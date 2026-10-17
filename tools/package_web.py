"""Package only deployable web/backend source, docs and test evidence; no secrets/APKs."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
files=[ROOT/name for name in ['README.md','MEMORY.md','WEB-DEPLOY.md','VALIDATION.md','LICENSE','NOTICE','Dockerfile','Dockerfile.dev','.dockerignore','.gcloudignore','.gitignore']]
files+=list((ROOT/'web').glob('*'))+list((ROOT/'shared').glob('*'))
files+=list((ROOT/'docs').rglob('*'))
files += [ROOT/'backend'/name for name in ['app.py','fast_lessons.py','requirements.txt','.env.example']]
files+=list((ROOT/'backend/tests').glob('*.py'))
files += [ROOT/'tools'/name for name in ['deploy_cloud_run.sh','enable_google_signin.sh','web_fixture.py','test_web_core.mjs','test_web_browser.cjs','measure_cloud_latency.py','package_web.py','test_context.mjs','test_context_browser.cjs','test_memory_browser.cjs','test_simple_ui.cjs','test_tutorial_browser.cjs','test_byok_browser.cjs','render_project_pdf.cjs','google_auth_fixture.py','test_google_signin_browser.cjs','narrate_submission_demo.py','record_submission_demo.py','record_submission_demo.cjs','render_submission_frames.cjs','render_submission_video.py','render_submission_writeup.cjs','publish_submission_assets.py']]
files += [ROOT/'tools/fixtures/reference.wav',ROOT/'tools/fixtures/README.md']
files+=list((ROOT/'validation').glob('web-*'))
files += [ROOT/'validation'/name for name in ['cloud-deployment.json','cloud-public-check.json','cloud-api-results.json','cloud-guards-results.json','cloud-current-deployment.json','cloud-current-api-results.json','submission-demo.json','submission-demo-recording.json','submission-publication.json','submission-status.json','cloud-auth-status.json','cloud-latency-results.json','cloud-parallel-latency-results.json','parallel-architecture-comparison.json','parallel-lite-preflight.json','parallel-lite-tight-preflight.json','cloud-3.8-preflight.json','cloud-v1.3-deployment.json','cloud-v1.3-api-results.json'] if (ROOT/'validation'/name).is_file()]
files=sorted({p for p in files if p.is_file()})
assert all(not any(part in {'.venv','.cache','__pycache__','.signing'} for part in p.relative_to(ROOT).parts) for p in files)
assert all(p.suffix not in {'.apk','.jks','.keystore'} and (not p.name.startswith('.env') or p.name=='.env.example') for p in files)
results=json.loads((ROOT/'validation/web-browser-results.json').read_text())
assert results.get('passed')==13 and not results.get('error') and not results.get('errors')
google_results=json.loads((ROOT/'validation/web-google-signin-browser-results.json').read_text())
assert google_results.get('passed')==5 and google_results['real_google_login'] is False
assert 'Ran 93 tests' in (ROOT/'validation/web-backend-tests.txt').read_text()
assert (ROOT/'validation/web-backend-tests.txt').read_text().rstrip().endswith('OK')
for name,count in [('context-browser',8),('memory-browser',12),('simple-ui',4),('byok-browser',8),('tutorial',7)]:
 result=json.loads((ROOT/('validation/web-'+name+'-results.json')).read_text())
 assert result.get('passed')==count and not result.get('error') and not result.get('errors')
deployed_record=ROOT/'validation/cloud-current-deployment.json'
current=json.loads(deployed_record.read_text()) if deployed_record.is_file() else {}
fingerprints=current.get('app_source_sha256',{})
cloud_deployed=bool(fingerprints) and all((ROOT/name).is_file() and hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in fingerprints.items())
api_record=ROOT/'validation/cloud-current-api-results.json'
current_api=json.loads(api_record.read_text()) if api_record.is_file() else {}
destination=ROOT/'dist';destination.mkdir(exist_ok=True)
archive=destination/'LingoLive-web-source.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in files:z.write(p,'LingoLive-web/'+str(p.relative_to(ROOT)))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for name in ['web/index.html','backend/app.py','shared/lesson_schema.json','Dockerfile','tools/deploy_cloud_run.sh']:
  assert z.read('LingoLive-web/'+name)==(ROOT/name).read_bytes()
manifest={'file':archive.name,'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':len(files),'source_version':'1.5-parallel-flash-lite','connection_modes':['access_code','api_key'],'personal_key_storage':'server_memory_one_hour','cloud_deployed':cloud_deployed,'deployment_blocker':None if cloud_deployed else 'source_not_verified_against_deployment','existing_deployment_revision':current.get('ready_revision','lingolive-00004-jzp'),'deployed_app_source_commit':current.get('source_commit'),'hosted_context_inference_verified':cloud_deployed and current_api.get('live_google',False),'valid_personal_key_inference_tested':current_api.get('valid_personal_key_inference_tested',False),'google_signin_enabled':False,'google_signin_status':'optional_disabled_user_selected_private_access_code','existing_cloud_deployment':(ROOT/'validation/cloud-deployment.json').is_file(),'existing_deployment_google_inference_tested':(ROOT/'validation/cloud-api-results.json').is_file(),'existing_deployment_url':'https://lingolive-358650584819.us-central1.run.app'}
(destination/'web-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(destination/'LingoLive-web-SHA256SUMS.txt').write_text(manifest['sha256']+'  '+archive.name+'\n')
print(json.dumps(manifest,indent=2))
