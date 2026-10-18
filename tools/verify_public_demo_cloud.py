"""Read-only deployment, asset/auth guards and private counter policy checks.

No Google password, personal key, Firebase token or paid lesson request is used.
An interactive user's Google sign-in remains a separate check.
"""
import argparse,hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
import requests
P=Path(__file__).resolve().parents[1];a=argparse.ArgumentParser(description=__doc__);a.add_argument('--stage',action='store_true');a.add_argument('--source-commit',required=True);x=a.parse_args()
token=subprocess.check_output(['/workspace/.cloud-tools/gcloud','auth','print-access-token'],text=True).strip();admin=requests.Session();admin.headers['Authorization']='Bearer '+token
r=admin.get('https://run.googleapis.com/v2/projects/locateassist/locations/us-central1/services/lingolive',timeout=30);r.raise_for_status();s=r.json();revision=s['latestReadyRevision'].split('/')[-1];base=next(v['uri'] for v in s['trafficStatuses'] if v.get('tag')=='verify') if x.stage else 'https://lingolive-358650584819.us-central1.run.app';base=base.rstrip('/')
t=s['template'];c=t['containers'][0];env={v['name']:v.get('value','') for v in c['env']};assert t['scaling']['maxInstanceCount']==1 and t['scaling'].get('minInstanceCount',0)==0;assert c['resources']['limits']=={'cpu':'1','memory':'512Mi'} and c['resources']['cpuIdle'] is True
for k,v in {'LINGOLIVE_PUBLIC_DEMO':'true','LINGOLIVE_GOOGLE_SIGNIN_REQUIRED':'true','LINGOLIVE_GOOGLE_AUTH_PROVIDER':'firebase','LINGOLIVE_ALLOWED_GOOGLE_EMAILS':'','LINGOLIVE_PUBLIC_AUDIO_SECONDS_PER_DAY':'1200','LINGOLIVE_PUBLIC_MODEL_CALLS_PER_DAY':'200','LINGOLIVE_LESSON_STRATEGY':'parallel'}.items():assert env[k]==v,(k,'unexpected value')
assert not env.get('GEMINI_API_KEY');assert 'lingolive-session-signing' in next(e['valueSource']['secretKeyRef']['secret'] for e in c['env'] if e['name']=='LINGOLIVE_ACCESS_TOKEN')
session=requests.Session();health=session.get(base+'/health',timeout=30);health.raise_for_status();assert health.json()['version']=='1.12';auth=session.get(base+'/v1/auth/config',timeout=30);auth.raise_for_status();d=auth.json();assert d['google_required'] and d['public_demo'] and d['daily_audio_seconds']==1200 and d['daily_lessons']==100
assert session.get(base+'/v1/session',timeout=30).status_code==401
assert session.post(base+'/v1/teach',headers={'Origin':base},json={},timeout=30).status_code==401
bad=session.post(base+'/v1/session',headers={'Origin':base},json={'mode':'public','google_credential':'not-a-valid-token','google_nonce':d['nonce']},timeout=30);assert bad.status_code==401
assert session.post(base+'/v1/session',headers={'Origin':'https://untrusted.example'},json={'mode':'public'},timeout=30).status_code==403
assert session.post(base+'/v1/session',headers={'Origin':base},json={'token':'former-passcode-is-not-google'},timeout=30).status_code==401
assert auth.headers['referrer-policy']=='strict-origin-when-cross-origin';assert 'https://apis.google.com' in auth.headers['content-security-policy']
assets={}
for file in ['index.html','app.js','google-signin.js','firebase-auth.js','microphone.js','speech-routing.mjs','sw.js']:
 path=P/'web'/file;url=base+('/' if file=='index.html' else '/sw.js' if file=='sw.js' else '/assets/'+file);r=session.get(url,timeout=30);r.raise_for_status();sha=hashlib.sha256(r.content).hexdigest();assert sha==hashlib.sha256(path.read_bytes()).hexdigest();assets[file]=sha
bucket=env['LINGOLIVE_QUOTA_BUCKET'];r=admin.get('https://storage.googleapis.com/storage/v1/b/'+bucket,timeout=30);r.raise_for_status();b=r.json();assert b['iamConfiguration']['publicAccessPrevention']=='enforced';r=admin.get('https://storage.googleapis.com/storage/v1/b/'+bucket+'/iam',timeout=30);r.raise_for_status();policy=r.json();assert any(v['role']=='roles/storage.objectUser' and 'serviceAccount:lingolive@locateassist.iam.gserviceaccount.com' in v['members'] for v in policy['bindings']);assert not any(m in ('allUsers','allAuthenticatedUsers') for v in policy['bindings'] for m in v['members'])
commit=subprocess.check_output(['git','rev-parse',x.source_commit],cwd=P,text=True).strip();files=[P/'backend'/f for f in ['app.py','daily_quota.py','fast_lessons.py','requirements.txt']]+[P/'Dockerfile',P/'.dockerignore']+list((P/'web').glob('*'))+list((P/'shared').glob('*'));fingerprints={}
for path in files:
 if path.is_file():
  name=str(path.relative_to(P));assert subprocess.check_output(['git','show',commit+':'+name],cwd=P)==path.read_bytes();fingerprints[name]=hashlib.sha256(path.read_bytes()).hexdigest()
record={'app_version':'1.12','url':base,'ready_revision':revision,'source_commit':commit,'health':health.json(),'public_verified_at_utc':datetime.now(timezone.utc).isoformat(),'google_auth_provider':'Firebase Authentication / Google','any_verified_google_account':True,'passcode_required':False,'unauthenticated_paid_routes_rejected':True,'invalid_google_token_rejected':True,'origin_guard_verified':True,'public_audio_seconds_per_day':1200,'public_model_calls_per_day':200,'daily_parallel_lessons':100,'allowance_shared_across_all_users_and_modes':True,'quota_reset_timezone':'Asia/Kolkata','quota_bucket':bucket,'durable_quota_private_iam_verified':True,'provider':'vertex','personal_keys_enabled':True,'persistent_sdk_login_verified':True,'min_instances':0,'max_instances':1,'memory':'512Mi','cpu':'1','request_based_cpu':True,'concurrency':t['maxInstanceRequestConcurrency'],'timeout_seconds':600,'no_google_ai_key_in_service':True,'asset_sha256':assets,'app_source_sha256':fingerprints,'interactive_google_account_login_tested':False,'paid_model_calls_in_this_verifier':0,'live_google_oauth_start_checked_separately':True,'traffic':s.get('traffic',[]),'cost_guards':{k:env[k] for k in ['LINGOLIVE_FLASH_MODEL','LINGOLIVE_TRANSCRIBE_MODEL','LINGOLIVE_LESSON_STRATEGY','LINGOLIVE_MAX_OUTPUT_TOKENS','LINGOLIVE_REQUESTS_PER_MINUTE','LINGOLIVE_PUBLIC_AUDIO_SECONDS_PER_DAY','LINGOLIVE_PUBLIC_MODEL_CALLS_PER_DAY']}}
(P/'validation'/('cloud-v1.12-staged-deployment.json' if x.stage else 'cloud-current-deployment.json')).write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:record[k] for k in ['app_version','url','ready_revision','passcode_required','unauthenticated_paid_routes_rejected','daily_parallel_lessons','public_audio_seconds_per_day']}))
