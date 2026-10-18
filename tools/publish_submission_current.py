"""Publish audited submission files to the existing public demo bucket, no IAM change.

Explicit --publish required. Operator credentials stay in memory. Public upload
uses a fixed allowlist; SDK profiles, private judge codes and recordings are excluded.
"""
import argparse,base64,hashlib,json,mimetypes,subprocess
from pathlib import Path
from urllib.parse import quote
import requests
BUCKET='lingolive-demo-358650584819';PREFIX='ai-builder-cup-2026/submission-2026-10-18'
FILES=['index.html','LingoLive-Pitch-Deck.pdf','LingoLive-Pitch-Deck.pptx','LingoLive-Writeup.pdf','LingoLive-Demo.mp4','LingoLive-Demo-download.mp4','LingoLive-Demo.srt','LingoLive-Demo.vtt','LingoLive-Submission.zip','LingoLive-web-source.zip','ENTRY.md','BRIEF-DESCRIPTION.txt','README-SUBMISSION.md','video-verification.json','audio-verification.json','readback-verification.json','source-secret-audit.json','source-archive-secret-audit.json','SHA256SUMS.txt','poster.jpg']
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--publish',action='store_true');p.add_argument('--directory',type=Path,required=True);a=p.parse_args()
if not a.publish:p.error('--publish is required')
root=a.directory.resolve();v=json.loads((root/'video-verification.json').read_text());assert 180<=v['seconds']<=240 and v['decode_verified'] and v['all_expected_voices_audible'] and v['longest_silence_seconds']<5.5
assert hashlib.sha256((root/'LingoLive-Demo.mp4').read_bytes()).hexdigest()==v['sha256'];assert all((root/f).is_file() for f in FILES)
for n in ['source-secret-audit.json','source-archive-secret-audit.json']:
 audit=json.loads((root/n).read_text());assert not audit['unresolved_findings'] and not audit['incomplete_scan_items']
token=subprocess.check_output(['/workspace/.cloud-tools/gcloud','auth','print-access-token'],text=True).strip();s=requests.Session();s.headers['Authorization']='Bearer '+token;token=''
r=s.get('https://storage.googleapis.com/storage/v1/b/'+BUCKET,timeout=30);r.raise_for_status();assert r.json().get('labels',{}).get('purpose')=='hackathon-public-demo'
rows=[]
for file in [f for f in FILES if f!='index.html']+['index.html']:
 p=root/file;data=p.read_bytes();assert 0<len(data)<60*1024*1024;sha=hashlib.sha256(data).hexdigest();mime={'.srt':'text/plain; charset=utf-8','.vtt':'text/vtt; charset=utf-8','.md':'text/plain; charset=utf-8','.txt':'text/plain; charset=utf-8'}.get(p.suffix,mimetypes.guess_type(file)[0] or 'application/octet-stream');name=PREFIX+'/'+file
 r=s.post('https://storage.googleapis.com/upload/storage/v1/b/'+BUCKET+'/o',params={'uploadType':'media','name':name},headers={'Content-Type':mime},data=data,timeout=120);r.raise_for_status();d=r.json();assert d['md5Hash']==base64.b64encode(hashlib.md5(data).digest()).decode()
 attachment=p.suffix in ('.zip','.pptx','.srt','.vtt') or file.endswith('-download.mp4');disposition=('attachment' if attachment else 'inline')+'; filename="'+file.replace('-download','')+'"'
 r=s.patch('https://storage.googleapis.com/storage/v1/b/'+BUCKET+'/o/'+quote(name,safe=''),json={'cacheControl':'no-cache,max-age=0,must-revalidate','contentDisposition':disposition,'metadata':{'sha256':sha,'app-version':'1.12','demo-version':'3.1'}},timeout=30);r.raise_for_status()
 url='https://storage.googleapis.com/'+BUCKET+'/'+name;anon=requests.get(url,params={'generation':d['generation']},timeout=120);anon.raise_for_status();assert hashlib.sha256(anon.content).hexdigest()==sha
 rows.append(dict(file=file,bytes=len(data),sha256=sha,url=url,generation=d['generation'],anonymous_download_verified=True));print('Published and anonymously verified '+file,flush=True)
(root/'publication.json').write_text(json.dumps(dict(bucket=BUCKET,prefix=PREFIX,app_version='1.12',demo_version='3.1',artifacts=rows,source_publication_authorized=True,iam_changed=False,app_deployed_by_this_script=False,portal_submitted=False),indent=2)+'\n')
