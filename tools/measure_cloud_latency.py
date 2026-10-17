"""Opt-in live latency checks: at most ten lessons (twenty parallel model calls) and one short PCM stream.

Credentials come from the normal Cloud SDK and Secret Manager, remain in RAM,
and are never written to the report. Run using backend/.venv/bin/python.
"""
from __future__ import annotations
import argparse,asyncio,base64,concurrent.futures,datetime,hashlib,json,os,re,shutil,ssl,statistics,subprocess,sys,threading,time,wave
from pathlib import Path
import requests
from websockets.asyncio.client import connect
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app import validate_lesson
BASE='https://lingolive-358650584819.us-central1.run.app'
CASES=[
 ('Japanese',{'text':'コーヒーはいかがですか？','known_code':'en-US','known_name':'English','learning_code':'ja-JP','learning_name':'Japanese'}),
 ('Hindi',{'text':'आप कहाँ जाना चाहते हैं?','known_code':'en-US','known_name':'English','learning_code':'hi-IN','learning_name':'Hindi'}),
 ('Spanish',{'text':'¿Quieres tomar un café?','known_code':'en-US','known_name':'English','learning_code':'es-ES','learning_name':'Spanish'}),
]

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--resume',action='store_true',help='Continue unmeasured cases in the same report without repeating completed calls')
 parser.add_argument('--run-live',action='store_true',help='Authorize up to ten lessons (twenty model calls) and one short speech stream')
 parser.add_argument('--output',type=Path,default=ROOT/'validation/cloud-parallel-latency-results.json')
 parser.add_argument('--wav',type=Path,default=ROOT/'tools/fixtures/reference.wav',help='Synthesized John chapter 3 verse 16, mono PCM16/16kHz, at most four seconds')
 parser.add_argument('--url',default=BASE,help='Verified public or tagged service URL')
 parser.add_argument('--expected-traffic',type=int,choices=(0,100),default=100)
 args=parser.parse_args()
 base=args.url.rstrip('/')
 if base not in (BASE,'https://lingolive-l5utioe5cq-uc.a.run.app','https://verify---lingolive-l5utioe5cq-uc.a.run.app'):
  parser.error('Only the existing LingoLive HTTPS service or its verification tag is allowed.')
 if not args.run_live:parser.error('Pass --run-live to run real Google calls; no benchmark runs by default.')
 sdk=shutil.which('gcloud') or '/workspace/.cloud-tools/gcloud'
 credential=subprocess.check_output([sdk,'auth','print-access-token'],text=True).strip()
 admin={'Authorization':'Bearer '+credential}
 response=requests.get('https://run.googleapis.com/v2/projects/locateassist/locations/us-central1/services/lingolive',headers=admin,timeout=30);response.raise_for_status();service=response.json()
 revision=service['latestReadyRevision'].split('/')[-1]
 traffic=service.get('trafficStatuses',service.get('traffic',[]))
 assert sum(t.get('percent',0) for t in traffic if t.get('revision','').split('/')[-1]==revision)==args.expected_traffic,'Latest revision traffic differs'
 container=service['template']['containers'][0];env={e['name']:e.get('value') for e in container.get('env',[])}
 assert env['LINGOLIVE_FLASH_MODEL']=='gemini-3.1-flash-lite'
 assert env['LINGOLIVE_LESSON_STRATEGY']=='parallel'
 assert service['template']['scaling']['maxInstanceCount']==1
 record=json.loads((ROOT/'validation/cloud-current-deployment.json').read_text())
 assert record['ready_revision']==revision,'Verified record belongs to another revision'
 assert all(env.get(k)==v for k,v in record['cost_guards'].items()),'Runtime cost/model configuration changed'
 assert service['template'].get('scaling',{}).get('minInstanceCount',0)==0
 assert container['resources']['limits']=={'cpu':'1','memory':'512Mi'}
 assert service['template']['maxInstanceRequestConcurrency']==12
 assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in record['app_source_sha256'].items()),'Local runtime differs from the verified build'
 for name,digest in record['asset_sha256'].items():
  route='/' if name=='index.html' else '/sw.js' if name=='sw.js' else '/assets/'+name
  fetched=requests.get(base+route,timeout=30);fetched.raise_for_status();assert hashlib.sha256(fetched.content).hexdigest()==digest,'Hosted asset changed'
 health=requests.get(base+'/health',timeout=30);health.raise_for_status();assert health.json()['version']=='1.5'
 secret=requests.get('https://secretmanager.googleapis.com/v1/projects/locateassist/secrets/lingolive-private-access/versions/latest:access',headers=admin,timeout=30);secret.raise_for_status()
 code=base64.b64decode(secret.json()['payload']['data']).decode().strip()
 clients=[requests.Session(),requests.Session()]
 for client in clients:
  login=client.post(base+'/v1/session',json={'token':code},headers={'Origin':base},timeout=30);assert login.status_code==200,'Private-code sign-in failed'
 del credential,admin,secret,code
 report={'tested_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'url':base,'ready_revision':revision,'health':health.json(),'runtime_source_commit':record['source_commit'],'model':env['LINGOLIVE_FLASH_MODEL'],'reasoning':'minimal','lesson_strategy':'parallel','provider_calls_per_lesson':2,'max_instances':1,'limits_unchanged':True,'latest_deployed_assets_match_source':True,'measurement':'Client HTTP request start to fully received, validated JSON: translation, all word meanings/readings, three replies. Measured from this cloud workspace; no physical phone or browser paint timing.','warm_state':'Unknown before health/asset verification; calls after that are warm-path samples. No cold-start claim.','max_lesson_attempts':10,'lesson_attempts':0,'results':[],'limitations':['Two sequential samples per language; too few for reliable percentiles.','Examples use prepared speech/text and host access code, not a valid personal API key.','Network, language, context and provider load affect latency. No automatic retries.']}
 if args.resume:
  previous=json.loads(args.output.read_text());assert previous['ready_revision']==revision,'Cannot resume across revisions'
  report=previous;report['resumed_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 lock=threading.Lock();run_start=time.perf_counter()-(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(report['tested_at_utc'])).total_seconds()
 def save():args.output.parent.mkdir(exist_ok=True,parents=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 def lesson(client,label,kind,value,round_number=None):
  with lock:
   assert report['lesson_attempts']<10,'Hard test-call ceiling reached'
   report['lesson_attempts']+=1
  start=time.perf_counter();row={'language':label,'kind':kind,'round':round_number,'source':value['text'],'request_start_offset_seconds':round(start-run_start,4)}
  try:
   with client.post(base+'/v1/teach',json=value,headers={'Origin':base},timeout=105,stream=True) as r:
    row['response_headers_seconds']=round(time.perf_counter()-start,3);data=r.json();received=time.perf_counter();row.update(http_status=r.status_code,seconds=round(received-start,3),completed_offset_seconds=round(received-run_start,4))
    if r.status_code!=200:
     row.update(success=False,error=data.get('detail','Service request failed'))
    else:
     parsed=validate_lesson(data,value['text']);assert parsed['contains_learning_language'] and len(parsed['replies'])==3
     assert all(w['reading'] and w['meaning'] for words in [parsed['words']]+[reply['words'] for reply in parsed['replies']] for w in words if w['is_word'])
     row.update(success=True,source_preserved=True,replies=3,all_readings_and_meanings=True,response_bytes=len(json.dumps(data,ensure_ascii=False).encode()))
  except Exception as error:
   row.update(success=False,seconds=round(time.perf_counter()-start,3),error_type=type(error).__name__)
  with lock:
   report['results'].append(row);save();print(json.dumps(row,ensure_ascii=False),flush=True)
  return row
 save();print(json.dumps({'revision_verified':revision,'model':report['model'],'call_ceiling':10}),flush=True)
 for number in (1,2):
  for name,value in CASES:
   if not any(r['kind']=='sequential' and r['language']==name and r['round']==number for r in report['results']):lesson(clients[0],name,'sequential',value,number)
 # Two independent browser-style sessions start one lesson at the same time.
 pending_pair=[index for index,(name,_) in enumerate(CASES[:2]) if not any(r['kind']=='two_users' and r['language']==name for r in report['results'])]
 gate=threading.Barrier(max(1,len(pending_pair)))
 def run_pair(index):
  gate.wait();name,value=CASES[index];return lesson(clients[index],name,'two_users',value)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(run_pair,pending_pair))
 if report['lesson_attempts']<=8 and not report.get('speech'):
  try:
   with wave.open(str(args.wav),'rb') as wav:
    assert (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())==(1,2,16000)
    pcm=wav.readframes(wav.getnframes());duration=wav.getnframes()/16000;assert 0<duration<=4
   async def speech():
    stamps={};parts=[];start=time.perf_counter();stamps['socket_start']=start
    cookie='; '.join(k+'='+v for k,v in clients[0].cookies.get_dict().items())
    async with asyncio.timeout(40):
     async with connect(base.replace('https://','wss://')+'/v1/listen',origin=base,additional_headers={'Cookie':cookie},ssl=ssl.create_default_context(),open_timeout=20,max_size=500000) as ws:
      await ws.send(json.dumps({'setup':{}}))
      while True:
       value=json.loads(await ws.recv());assert not value.get('error'),'Speech setup failed'
       if 'setupComplete' in value or 'setup_complete' in value:break
      stamps['setup_complete']=time.perf_counter()
      async def send():
       stamps['audio_start']=time.perf_counter()
       for position in range(0,len(pcm),3200):
        frame=pcm[position:position+3200]
        await ws.send(json.dumps({'realtimeInput':{'audio':{'data':base64.b64encode(frame).decode(),'mimeType':'audio/pcm;rate=16000'}}}))
        await asyncio.sleep(len(frame)/32000)
       stamps['audio_end']=time.perf_counter();await ws.send(json.dumps({'realtimeInput':{'audioStreamEnd':True}}))
      sender=asyncio.create_task(send())
      try:
       async for raw in ws:
        value=json.loads(raw);assert not value.get('error'),'Speech failed'
        content=value.get('serverContent',value.get('server_content',{}));final=content.get('inputTranscription',content.get('input_transcription',{}))
        if final.get('text'):
         parts.append(final['text']);stamps['final_received']=time.perf_counter()
         normalized=re.sub('[^a-z0-9]','',(' '.join(parts)).lower().replace('sixteen','16').replace('three','3'))
         if 'johnchapter3verse16' in normalized:break
       await sender
      finally:
       sender.cancel();await asyncio.gather(sender,return_exceptions=True)
    text=' '.join(parts).strip();assert text and 'john' in text.lower() and len(text.split())>=4,'Expected complete fixture speech was not recognized'
    return text,stamps
   transcript,stamps=asyncio.run(speech())
   audio_result={'input':'Existing synthesized reference.wav; not physical microphone','audio_seconds':round(duration,3),'transcript':transcript,'socket_and_google_setup_seconds':round(stamps['setup_complete']-stamps['socket_start'],3),'final_relative_to_audio_end_seconds':round(stamps['final_received']-stamps['audio_end'],3)}
   value={'text':transcript,'known_code':'ja-JP','known_name':'Japanese','learning_code':'en-US','learning_name':'English','memory_notes':'Use short, simple replies.','recent_turns':[{'speaker':'user','text':'I am trying to find this passage to read aloud.'}],'previous_reply_source':'Which passage would you like to read?','previous_replies':[{'text':'John chapter 3 verse 16','translation':'ヨハネによる福音書3章16節'}]}
   plain=lesson(clients[0],'English → Japanese explanations','speech_then_lesson',value)
   completed=plain.get('completed_offset_seconds',time.perf_counter()-run_start)+run_start
   audio_result.update(client_handoff_seconds=round((plain['request_start_offset_seconds']+run_start)-stamps['final_received'],3),audio_end_to_complete_lesson_seconds=round(completed-stamps['audio_end'],3),socket_start_to_complete_lesson_seconds=round(completed-stamps['socket_start'],3))
   report['speech']=audio_result;save();print(json.dumps({'speech':audio_result},ensure_ascii=False),flush=True)
   with_audio={**value,'audio_context':{'mime_type':'audio/wav','data':base64.b64encode(args.wav.read_bytes()).decode()}}
   lesson(clients[0],'English → Japanese explanations','same_context_with_optional_audio',with_audio)
  except Exception as error:
   report['speech_error']={'type':type(error).__name__,'message':'Speech pipeline did not complete; see measured text results.'};save();print(json.dumps(report['speech_error']),flush=True)
 summary={}
 for name,_ in CASES:
  rows=[r for r in report['results'] if r['language']==name and r['kind']=='sequential'];values=[r['seconds'] for r in rows if r['success']]
  summary[name]={'attempted':len(rows),'succeeded':len(values),'median_seconds':round(statistics.median(values),3) if values else None,'min_seconds':min(values) if values else None,'max_seconds':max(values) if values else None}
 report['sequential_summary']=summary;report['succeeded']=sum(r['success'] for r in report['results']);report['failed']=sum(not r['success'] for r in report['results']);report['total_run_seconds']=round(time.perf_counter()-run_start,3);save()
 for client in clients:
  try:client.delete(base+'/v1/session',headers={'Origin':base},timeout=10)
  except requests.RequestException:pass
 print(json.dumps({'summary':summary,'attempts':report['lesson_attempts'],'failures':report['failed'],'total_run_seconds':report['total_run_seconds']},ensure_ascii=False),flush=True)
 return 1 if report['failed'] or report.get('speech_error') else 0
if __name__=='__main__':raise SystemExit(main())
