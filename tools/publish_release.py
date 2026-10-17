"""Deliver verified APK/source artifacts through an isolated GitHub delivery branch."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,time,zipfile
import xml.etree.ElementTree as ET
import requests
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'.cache/delivery-v1.0'
REPO='U4AR/SyntheticDataGeneration';TAG='lingolive-v1.0';BRANCH='lingolive-apk-delivery'
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(4194304),b''):h.update(b)
 return {'bytes':path.stat().st_size,'sha256':h.hexdigest()}
def github(method,path,**kw):
 token=os.getenv('GH_TOKEN') or os.getenv('GITHUB_TOKEN')
 if not token:raise RuntimeError('Existing GitHub API binding unavailable')
 r=requests.request(method,'https://api.github.com/'+path,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json'},timeout=60,**kw)
 if not r.ok:raise RuntimeError(f'GitHub {method} {path}: HTTP {r.status_code}')
 return r.json() if r.content else None
def prepare():
 DEST.mkdir(parents=True,exist_ok=True)
 if (DEST/'delivery-status.json').exists():raise RuntimeError('Delivery already started; inspect its state before retrying')
 tests=list((ROOT/'android/app/build/test-results/testDebugUnitTest').glob('TEST-*.xml'))
 if sum(int(ET.parse(p).getroot().get('tests','0')) for p in tests)!=10:raise RuntimeError('Expected ten current JVM checks')
 for p in tests:
  if any(int(ET.parse(p).getroot().get(k,'0')) for k in ['failures','errors','skipped']):raise RuntimeError('JVM tests are not all passing')
 if 'OK (7 tests)' not in (ROOT/'validation/android-tests.txt').read_text():raise RuntimeError('Seven Android checks must pass')
 backend=(ROOT/'validation/backend-tests.txt').read_text()
 if 'Ran 11 tests' not in backend or not backend.rstrip().endswith('OK'):raise RuntimeError('Eleven backend checks must pass')
 apk=ROOT/'android/app/build/outputs/apk/release/app-release.apk'
 main_sources=list((ROOT/'android/app/src/main').rglob('*.kt'))
 if apk.stat().st_mtime<max(p.stat().st_mtime for p in main_sources):raise RuntimeError('APK predates source')
 if (ROOT/'validation/android-tests.txt').stat().st_mtime<max(p.stat().st_mtime for p in (ROOT/'android/app/src/androidTest').rglob('*.kt')):raise RuntimeError('Android results predate tests')
 sdk=Path('/workspace/.android-tools/sdk/build-tools/36.0.0')
 signature=subprocess.run([str(sdk/'apksigner'),'verify','--verbose','--print-certs',str(apk)],check=True,text=True,capture_output=True).stdout
 subprocess.run([str(sdk/'zipalign'),'-c','-P','16','4',str(apk)],check=True,capture_output=True)
 badging=subprocess.run([str(sdk/'aapt2'),'dump','badging',str(apk)],check=True,text=True,capture_output=True).stdout
 if 'application-debuggable' in badging or "name='com.u4ar.lingolive'" not in badging:raise RuntimeError('Unexpected APK identity/debug status')
 with zipfile.ZipFile(apk) as z:
  for name in ['lesson_schema.json','teach_prompt.txt']:
   if z.read('assets/'+name)!=(ROOT/'shared'/name).read_bytes():raise RuntimeError('Schema/prompt mismatch')
  if b'test-only-device-key' in b''.join(z.read(n) for n in z.namelist() if n.endswith('.dex')):raise RuntimeError('Test credentials were packed')
  if not {'arm64-v8a','x86_64'}.issubset({n.split('/')[1] for n in z.namelist() if n.startswith('lib/')}):raise RuntimeError('Expected universal native libraries')
 shutil.copyfile(apk,DEST/'LingoLive.apk')
 report={'jvm_checks':10,'android_checks':7,'backend_checks':11,'apk':digest(apk),'signature':signature,'physical_microphone_tested':False,'live_google_calls_tested':False,'cloud_run_deployed':False}
 (ROOT/'validation/build-verification.json').write_text(json.dumps(report,indent=2))
 with zipfile.ZipFile(DEST/'LingoLive.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:z.write(apk,'LingoLive.apk')
 with zipfile.ZipFile(DEST/'LingoLive-source.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(ROOT.rglob('*')):
   rel=p.relative_to(ROOT)
   if not p.is_file() or any(part in {'.cache','.signing','.gradle','build','.git','.venv','.private','__pycache__'} for part in rel.parts) or p.name=='local.properties' or (p.name.startswith('.env') and p.name!='.env.example') or p.suffix in {'.keystore','.jks','.apk','.zip','.pyc'}:continue
   z.write(p,'LingoLive/'+str(rel))
 names=['LingoLive.apk','LingoLive.zip','LingoLive-source.zip']
 checks=DEST/'LingoLive-SHA256SUMS.txt';checks.write_text(''.join(digest(DEST/n)['sha256']+'  '+n+'\n' for n in names));names.append(checks.name)
 manifest={'repository':REPO,'tag':TAG,'assets':{n:digest(DEST/n) for n in names}}
 (DEST/'manifest.json').write_text(json.dumps(manifest,indent=2));shutil.copyfile(ROOT/'tools/upload_release.py',DEST/'upload.py')
 notes='''LingoLive 1.0 — listen, understand, join in

Independent Android 8+ app, about 8.5 MB. A minimal interface with a fixed listening button, selectable known/learning languages, live multilingual transcription, word-by-word explanations, original/pronunciation display, three suggested replies, tappable contextual meanings, Android pronunciation playback, and searchable private local memory. All finalized speech is retained; only learning-language detections automatically request lessons. Typed/pasted phrases can be taught explicitly.

Uses the documented Gemini 3.5 Transcribe Live WebSocket API with literal multilingual recognition and Gemini 3.6 Flash for structured language teaching. Google's bundled ML Kit identifies finalized text locally. Queued Flash calls are paced to 24 starts/minute, and failed lessons keep their transcripts for retry. Capture stops when the app backgrounds or opens Saved/Settings. Live sessions renew before Google's ten-minute limit, with bounded reconnect buffering.

No Google API key, backend token or server address is packed. Configure your own Google AI Studio key on the device, or enter your private Google Cloud Run backend address/token. Device secrets are encrypted with Android Keystore. New transcription/lessons require internet and account model access/quota; saved lessons work offline. A clearly labeled Japanese example is available before setup and is never saved as fake speech.

The Apache-2.0 source includes Android, a Cloud Run WebSocket/Flash relay, Dockerfile, Secret Manager deployment script and instructions. The server stores no learning history and is protected by a separately configured private access token. No Cloud Run service has been deployed; add credentials after installation or deployment. This private prototype uses a shared backend token; public multi-user hosting needs per-user auth/quotas.

Validation: ten JVM checks, eleven Python backend checks and seven Android UI/data/network-flow checks passed. The Google language identifier actually ran locally. Transcribe/Flash were mocked for network-flow tests with a test PCM source. Live Google inference, actual phone microphone speech, accents, and physical-device latency have not been tested because keys are intentionally left for later setup. The sideload APK is non-debuggable and development-signed; store distribution needs your release signing.

APK, APK ZIP, complete independent source and SHA-256 checksums are attached. Existing Bible applications and repository main are preserved. Sign in to GitHub to download from this private repository.
'''
 (DEST/'release-notes.md').write_text(notes)
 workflow='''name: Deliver verified LingoLive APK
"on":
  push:
    branches: [lingolive-apk-delivery]
    paths: [lingolive-delivery/upload.py]
permissions:
  contents: write
jobs:
  deliver:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262
        with:
          persist-credentials: false
          sparse-checkout: /lingolive-delivery/
          sparse-checkout-cone-mode: false
      - name: Upload verified signed APK and independent source
        env:
          GH_TOKEN: ${{ github.token }}
        run: python3 lingolive-delivery/upload.py
'''
 (DEST/'workflow.yml').write_text(workflow);return manifest,notes
def publish(manifest,notes):
 if any(r['tag_name']==TAG for r in github('GET',f'repos/{REPO}/releases?per_page=100')):raise RuntimeError('Release already exists; refusing overwrite')
 parent=github('GET',f'repos/{REPO}/git/ref/heads/main')['object']['sha']
 release=github('POST',f'repos/{REPO}/releases',json={'tag_name':TAG,'target_commitish':parent,'name':'LingoLive 1.0 — learn from live multilingual speech','draft':True,'prerelease':True,'body':notes})
 manifest['release_id']=release['id'];(DEST/'manifest.json').write_text(json.dumps(manifest,indent=2))
 gitdir=Path('/workspace/BibleAudioAndroid/.cache/apk-delivery.git');env=dict(os.environ,GIT_INDEX_FILE=str(DEST/'delivery.index'));env.pop('GEMINI_API_KEY',None)
 def git(*args):return subprocess.run(['git','--git-dir',str(gitdir),*args],check=True,text=True,capture_output=True,env=env).stdout.strip()
 if git('cat-file','-t',parent)!='commit':raise RuntimeError('Retained main commit unavailable')
 git('read-tree',parent);files={'.github/workflows/lingolive-delivery.yml':DEST/'workflow.yml'}
 files.update({'lingolive-delivery/'+n:DEST/n for n in list(manifest['assets'])+['upload.py','manifest.json','release-notes.md']})
 for name,p in files.items():git('update-index','--add','--cacheinfo','100644,'+git('hash-object','-w',str(p))+','+name)
 tree=git('write-tree');commit=git('-c','user.name=Codex','-c','user.email=codex@openai.com','commit-tree',tree,'-p',parent,'-m','Deliver independent LingoLive Android app and Cloud Run source')
 git('push','origin',commit+':refs/heads/'+BRANCH)
 status={'release_id':release['id'],'tag':TAG,'delivery_commit':commit,'main_sha':parent,'published':False};state=DEST/'delivery-status.json';state.write_text(json.dumps(status,indent=2));print('Pushed verified delivery; waiting for GitHub uploads',flush=True)
 cutoff=time.monotonic()+600
 while time.monotonic()<cutoff:
  r=github('GET',f'repos/{REPO}/releases/{release["id"]}')
  if not r['draft']:
   if len(r['assets'])!=4:raise RuntimeError('Expected four uploaded assets')
   for name,expected in manifest['assets'].items():
    a=next(a for a in r['assets'] if a['name']==name)
    if a['size']!=expected['bytes'] or a.get('digest')!='sha256:'+expected['sha256']:raise RuntimeError('Uploaded artifact mismatch')
   if github('GET',f'repos/{REPO}/git/ref/heads/main')['object']['sha']!=parent:raise RuntimeError('Main changed unexpectedly')
   status.update(published=True,url=r['html_url'],assets=[{k:a[k] for k in ['name','size','digest','browser_download_url']} for a in r['assets']]);state.write_text(json.dumps(status,indent=2));shutil.copyfile(state,ROOT/'validation/release-verification.json')
   if github('GET',f'repos/{REPO}/git/ref/heads/{BRANCH}')['object']['sha']==commit:github('DELETE',f'repos/{REPO}/git/refs/heads/{BRANCH}')
   print('Published: '+r['html_url'],flush=True);return
  runs=github('GET',f'repos/{REPO}/actions/runs?head_sha={commit}&per_page=20')['workflow_runs']
  jobs=[x for x in runs if x['name']=='Deliver verified LingoLive APK']
  if jobs and jobs[0]['status']=='completed' and jobs[0]['conclusion']!='success':raise RuntimeError('Delivery failed: '+jobs[0]['html_url'])
  time.sleep(20)
 raise RuntimeError('Publication pending; inspect delivery status')
if __name__=='__main__':publish(*prepare())
