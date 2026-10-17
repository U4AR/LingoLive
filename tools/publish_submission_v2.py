"""Publish only verified v2 media/docs to the existing dedicated demo bucket.

Opt-in; normal Google Cloud SDK authentication stays in RAM. No IAM changes,
app deployment, source-visibility changes, third-party messages or portal submission.
"""
import argparse,base64,hashlib,json,mimetypes,shutil,subprocess
from pathlib import Path
from urllib.parse import quote
import requests
BUCKET='lingolive-demo-358650584819';PREFIX='ai-builder-cup-2026/v2'
FILES=['LingoLive-Demo.mp4','LingoLive-Demo-download.mp4','LingoLive-Demo.srt','LingoLive-Demo.vtt','LingoLive-Proposal.pdf','LingoLive-Writeup.pdf','LingoLive-Submission.zip','LingoLive-Media-Assets.zip','DEMO-TRANSCRIPT-V2.md','video-verification.json','poster.jpg','index.html']

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--publish',action='store_true');p.add_argument('--only',nargs='+',choices=FILES);p.add_argument('--directory',type=Path,default=Path('/tmp/lingolive-video-v2'));a=p.parse_args()
 if not a.publish:p.error('--publish is required')
 root=a.directory.resolve();check=json.loads((root/'video-verification.json').read_text());assert check['decode_verified'] and check['seconds']<180
 assert hashlib.sha256((root/'LingoLive-Demo.mp4').read_bytes()).hexdigest()==check['sha256'];assert all((root/n).is_file() for n in FILES)
 sdk=shutil.which('gcloud') or '/workspace/.cloud-tools/gcloud';token=subprocess.check_output([sdk,'auth','print-access-token'],text=True).strip();s=requests.Session();s.headers['Authorization']='Bearer '+token
 r=s.get('https://storage.googleapis.com/storage/v1/b/'+BUCKET,timeout=30);r.raise_for_status();assert r.json().get('labels',{}).get('purpose')=='hackathon-public-demo'
 selected=a.only or FILES
 previous=json.loads((root/'publication.json').read_text()) if a.only and (root/'publication.json').exists() else {}
 rows=[row for row in previous.get('artifacts',[]) if row['file'] not in selected]
 def upload(file,name):
  assert 0<file.stat().st_size<60*1024*1024
  data=file.read_bytes();sha=hashlib.sha256(data).hexdigest();mime={'.srt':'text/plain; charset=utf-8','.vtt':'text/vtt; charset=utf-8','.html':'text/html; charset=utf-8','.md':'text/plain; charset=utf-8'}.get(file.suffix,mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
  response=s.post('https://storage.googleapis.com/upload/storage/v1/b/'+BUCKET+'/o',params={'uploadType':'media','name':name},headers={'Content-Type':mime},data=data,timeout=120);response.raise_for_status();d=response.json();assert d['md5Hash']==base64.b64encode(hashlib.md5(data).digest()).decode()
  attachment=file.suffix in ('.zip','.srt','.vtt') or file.name.endswith('-download.mp4');header=('attachment' if attachment else 'inline')+'; filename="'+file.name.replace('-download','')+'"'
  response=s.patch('https://storage.googleapis.com/storage/v1/b/'+BUCKET+'/o/'+quote(name,safe=''),json={'cacheControl':'public,max-age=300','contentDisposition':header,'metadata':{'sha256':sha,'app-version':'1.9','demo-version':'2'}},timeout=30);response.raise_for_status()
  url='https://storage.googleapis.com/'+BUCKET+'/'+name
  public=requests.get(url,params={'generation':d['generation']},timeout=120);public.raise_for_status();assert hashlib.sha256(public.content).hexdigest()==sha
  rows.append(dict(file=file.name,bytes=len(data),sha256=sha,url=url,generation=d['generation'],anonymous_download_verified=True,content_disposition=header));print('Published and anonymously verified '+file.name,flush=True)
 for name in selected:upload(root/name,PREFIX+'/'+name)
 # Existing root preview now introduces current v2 and links the archived v1.5.
 if not a.only or 'index.html' in selected:upload(root/'index.html','ai-builder-cup-2026/index.html')
 report=dict(bucket=BUCKET,project='locateassist',demo_version='2',app_version='1.9',public_preview_url='https://storage.googleapis.com/'+BUCKET+'/'+PREFIX+'/index.html',public_video_url='https://storage.googleapis.com/'+BUCKET+'/'+PREFIX+'/LingoLive-Demo.mp4',download_video_url='https://storage.googleapis.com/'+BUCKET+'/'+PREFIX+'/LingoLive-Demo-download.mp4',artifacts=rows,existing_v1_5_media_preserved=True,source_code_published_by_this_script=False,iam_changed=False,app_deployed_by_this_script=False,approved_hackathon_video_host_url=None,hack2skill_submitted=False,note='Cloud Storage watch/download links are public; they are not a YouTube, Vimeo or Google Drive submission URL.')
 (root/'publication.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
