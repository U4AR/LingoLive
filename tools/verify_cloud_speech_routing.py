"""Read-only deployment, asset, authentication and unchanged cost-guard verification."""
import argparse,datetime,hashlib,json,shutil,subprocess
from pathlib import Path
import requests
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stage',action='store_true');p.add_argument('--source-commit',default='HEAD');a=p.parse_args();root=Path(__file__).resolve().parents[1];sdk=shutil.which('gcloud') or '/workspace/.cloud-tools/gcloud'
token=subprocess.check_output([sdk,'auth','print-access-token'],text=True).strip()
r=requests.get('https://run.googleapis.com/v2/projects/locateassist/locations/us-central1/services/lingolive',headers={'Authorization':'Bearer '+token},timeout=30);r.raise_for_status();s=r.json();token=''
old=json.loads((root/'validation/cloud-current-deployment.json').read_text());revision=s['latestReadyRevision'].split('/')[-1];t=s['template'];c=t['containers'][0];env={e['name']:e.get('value','') for e in c['env']};guards={k:env[k] for k in old['cost_guards']};assert guards==old['cost_guards'];assert t['scaling'].get('maxInstanceCount')==1 and t['scaling'].get('minInstanceCount',0)==0;assert c['resources']['limits']=={'cpu':'1','memory':'512Mi'} and c['resources'].get('cpuIdle') is True;assert t['maxInstanceRequestConcurrency']==12 and t['timeout']=='600s';assert t['serviceAccount']=='lingolive@locateassist.iam.gserviceaccount.com';assert not env.get('GEMINI_API_KEY')
traffic=s['trafficStatuses'];percent=sum(v.get('percent',0) for v in traffic if v.get('revision','').split('/')[-1]==revision);assert percent==(0 if a.stage else 100),traffic
url=next(v['uri'] for v in traffic if v.get('tag')=='verify') if a.stage else old['url'];health=requests.get(url+'/health',timeout=30);health.raise_for_status();assert health.json()['version']=='1.10'
assets={}
for name in ['index.html','app.js','microphone.js','speech-routing.mjs','sw.js']:
 path='/' if name=='index.html' else '/sw.js' if name=='sw.js' else '/assets/'+name;r=requests.get(url+path,timeout=30);r.raise_for_status();assert r.content==(root/'web'/name).read_bytes(),name;assets[name]=hashlib.sha256(r.content).hexdigest()
assert requests.post(url+'/v1/teach',json={'text':'hello'},headers={'Origin':url},timeout=30).status_code==401
commit=subprocess.check_output(['git','rev-parse',a.source_commit],cwd=root,text=True).strip();paths=[root/'backend'/n for n in ['app.py','fast_lessons.py','requirements.txt']]+[root/'Dockerfile']+list((root/'web').glob('*'))+list((root/'shared').glob('*'));fingerprints={}
for f in paths:
 if f.is_file():
  name=str(f.relative_to(root));assert subprocess.check_output(['git','show',commit+':'+name],cwd=root)==f.read_bytes();fingerprints[name]=hashlib.sha256(f.read_bytes()).hexdigest()
record={**old,'url':url,'ready_revision':revision,'source_commit':commit,'app_version':'1.10','health':health.json(),'traffic_percent':percent,'cost_guards':guards,'app_source_sha256':fingerprints,'asset_sha256':assets,'persistent_sdk_login_verified':True,'guards_unchanged':True,'speech_routing_verified':'local real-browser fixtures and generated-audio checks; live asset hashes verified','public_verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(root/'validation'/('cloud-v1.10-staged-deployment.json' if a.stage else 'cloud-current-deployment.json')).write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'url':url,'revision':revision,'traffic_percent':percent,'assets_verified':len(assets),'unauthenticated_teach_rejected':True,'guards_unchanged':True,'app_version':'1.10'}))
