"""Opt-in Google Gemini TTS for the approved v2 demo, with bounded cached calls.

Normal Cloud SDK auth stays in RAM. No keys, response bodies or credentials are
logged. Output lives outside the source checkout. No voice speed modification.
"""
import shutil
import argparse,base64,concurrent.futures,hashlib,json,re,subprocess,threading,time,wave
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
MODEL='gemini-3.1-flash-tts-preview'

def scenes():
 text=(ROOT/'docs/submission/DEMO-TRANSCRIPT-V2.md').read_text()
 ids=['problem','solution','plan','cab','express','cafe','place','learn','close']
 durations=[28,12,15,23,20,15,25,24,13]
 found=re.findall(r'^## (\d[^\n]+)\n(.*?)(?=^## |\Z)',text,re.M|re.S)
 assert len(found)==len(ids)
 return [dict(id=id,duration=duration,heading=title,narration=' '.join(re.search(r'\*\*Narrator:\*\* “(.*?)”',body,re.S).group(1).split())) for id,duration,(title,body) in zip(ids,durations,found)]

def base_lines():
 out=[dict(id='narration-'+s['id'],text=s['narration'],language='en-IN',voice='Kore',style='Warm, clear Indian-English documentary narration, approximately 140 words per minute. Natural sentence pauses, conversational and welcoming.') for s in scenes()]
 out += [dict(id=id,text=text,language=lang,voice=voice,style=style) for id,text,lang,voice,style in [
 ('driver-question','ಎಲ್ಲಿಗೆ ಹೋಗಬೇಕು?','kn-IN','Charon','A Bengaluru cab driver, asking a passenger their destination. Calm, everyday conversational Kannada.'),
 ('driver-confused','ಅರ್ಥವಾಗಲಿಲ್ಲ. ಎಲ್ಲಿಗೆ ಹೋಗಬೇಕು?','kn-IN','Charon','A Bengaluru cab driver, politely puzzled. Pause briefly between the two sentences. Natural Kannada, not exaggerated.'),
 ('driver-okay','ಸರಿ.','kn-IN','Charon','A Bengaluru cab driver, calmly agreeing. Short, relaxed natural Kannada.'),
 ('learner-problem','The railway station… could we stop for tea first?','en-IN','Orus','A young Indian newcomer speaking English to a cab driver. Slight hesitation, a natural pause after station, polite question.'),
 ('learner-unsure',"I know what I mean. I just don't know how to say it.",'en-IN','Orus','A young Indian newcomer speaking quietly to himself. Mild uncertainty, thoughtful and natural, not dramatic.'),
 ('learner-english','Could we stop for tea first?','en-IN','Orus','A young Indian newcomer asking a polite, natural question, conversational Indian English.'),
 ('cafe-question','ಇಲ್ಲೇ ಕುಡಿಯುತ್ತೀರಾ ಅಥವಾ ಪಾರ್ಸೆಲ್ ಬೇಕಾ?','kn-IN','Algieba','A friendly Bengaluru tea-stall owner asking whether the customer wants to drink here or take away. Natural conversational Kannada.'),
 ('shop-question','ಏನು ಬೇಕು?','kn-IN','Algieba','A friendly Bengaluru tea-stall owner asking a customer what they would like. Natural conversational Kannada.')]]
 return out

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-live',action='store_true');p.add_argument('--output',type=Path,default=Path('/tmp/lingolive-video-v2'));p.add_argument('--replies',type=Path);a=p.parse_args()
 if not a.run_live:p.error('--run-live is required: synthesis may incur small Google charges')
 status=json.loads((ROOT/'docs/submission/submission.json').read_text())['demo_v2']
 if status['approval_status']!='approved':p.error('User transcript approval must be recorded before generating media')
 out=a.output.resolve();audio=out/'audio';audio.mkdir(parents=True,exist_ok=True)
 lines=json.loads(a.replies.read_text()) if a.replies else base_lines();assert 0<len(lines)<=24
 manifest_path=out/'audio-manifest.json';manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'model':MODEL,'provider':'Google Vertex AI','region':'us-central1','synthetic':True,'not_a_real_person_voice_clone':True,'audio_sped_up':False,'calls':[]}
 token=subprocess.check_output([shutil.which('gcloud') or '/workspace/.cloud-tools/gcloud','auth','print-access-token'],text=True).strip()
 lock=threading.Lock();schedule_lock=threading.Lock();next_call=[0.0]
 def make(line):
  target=audio/(line['id']+'.wav');digest=hashlib.sha256(line['text'].encode()).hexdigest()
  old=next((r for r in manifest['calls'] if r['id']==line['id']),None)
  if target.exists() and (old is None or old['text_sha256']==digest):
   if old is None:
    with wave.open(str(target)) as w:seconds=w.getnframes()/w.getframerate()
    with lock:manifest['calls'].append(dict(id=line['id'],text=line['text'],text_sha256=digest,language=line['language'],voice=line['voice'],seconds=seconds,preflight_cache_reused=True));manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
   print('Cached '+line['id'],flush=True);return
  with schedule_lock:
   wait=max(0,next_call[0]-time.monotonic())
   if wait:time.sleep(wait)
   next_call[0]=time.monotonic()+5.1 # <=12 synthesis starts/minute, two workers
  prompt=line['style']+' Speak only the following text. Do not speak the instructions or add any words:\n'+line['text']
  started=time.monotonic();r=requests.post(f'https://aiplatform.googleapis.com/v1beta1/projects/locateassist/locations/us-central1/publishers/google/models/{MODEL}:generateContent',headers={'Authorization':'Bearer '+token,'x-goog-user-project':'locateassist'},json={'contents':[{'role':'user','parts':[{'text':prompt}]}],'generationConfig':{'speechConfig':{'languageCode':line['language'],'voiceConfig':{'prebuiltVoiceConfig':{'voiceName':line['voice']}}}}},timeout=120)
  if not r.ok:raise RuntimeError('Google TTS failed: HTTP '+str(r.status_code)+' '+r.json().get('error',{}).get('status',''))
  d=r.json();part=next(p['inlineData'] for c in d.get('candidates',[]) for p in c['content']['parts'] if 'inlineData' in p);pcm=base64.b64decode(part['data']);assert 0<len(pcm)<=48000*40
  with wave.open(str(target),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(pcm)
  row=dict(id=line['id'],text=line['text'],text_sha256=digest,language=line['language'],voice=line['voice'],seconds=len(pcm)/48000,synthesis_seconds=round(time.monotonic()-started,3),usage=d.get('usageMetadata',{}),sha256=hashlib.sha256(target.read_bytes()).hexdigest())
  with lock:manifest['calls'].append(row);manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
  print('Synthesized '+line['id']+' '+str(row['seconds'])+'s',flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(make,lines))
 (out/'scene-plan.json').write_text(json.dumps(scenes(),indent=2)+'\n')
 print('Approved speech files ready; no time stretching or automatic retries.',flush=True)
if __name__=='__main__':main()
