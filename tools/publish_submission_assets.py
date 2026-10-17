"""Publish only the reviewed demo/documents to the dedicated public artifact bucket.

Opt-in. Uses the normal Cloud SDK login. Does not deploy or alter the app,
publish source code, accept credentials as arguments, or submit Hack2skill forms.
"""
import argparse,base64,hashlib,json,mimetypes,shutil,subprocess
from pathlib import Path
from urllib.parse import quote
import requests

BUCKET='lingolive-demo-358650584819'
PREFIX='ai-builder-cup-2026'
FILES=['LingoLive-Demo.mp4','LingoLive-Demo.srt','LingoLive-Demo.vtt','LingoLive-Proposal.pdf','LingoLive-Writeup.pdf','LingoLive-Submission.zip','poster.jpg','index.html']

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish',action='store_true')
    parser.add_argument('--directory',type=Path,default=Path('/tmp/lingolive-submission'))
    args=parser.parse_args()
    if not args.publish:parser.error('--publish is required')
    directory=args.directory.resolve();verification=json.loads((directory/'video-verification.json').read_text())
    assert verification['decode_verified'] and verification['seconds']<180
    assert hashlib.sha256((directory/'LingoLive-Demo.mp4').read_bytes()).hexdigest()==verification['sha256']
    assert all((directory/name).is_file() for name in FILES)
    sdk=shutil.which('gcloud') or '/workspace/.cloud-tools/gcloud'
    token=subprocess.check_output([sdk,'auth','print-access-token'],text=True).strip()
    client=requests.Session();client.headers.update({'Authorization':'Bearer '+token})
    bucket=client.get('https://storage.googleapis.com/storage/v1/b/'+BUCKET,timeout=30);bucket.raise_for_status()
    assert bucket.json().get('labels',{}).get('purpose')=='hackathon-public-demo'
    published=[]
    for name in FILES:
        file=directory/name;assert file.stat().st_size<60*1024*1024
        data=file.read_bytes();sha=hashlib.sha256(data).hexdigest();md5=base64.b64encode(hashlib.md5(data).digest()).decode()
        mime={'.vtt':'text/vtt; charset=utf-8','.srt':'text/plain; charset=utf-8','.html':'text/html; charset=utf-8'}.get(file.suffix,mimetypes.guess_type(name)[0] or 'application/octet-stream')
        object_name=PREFIX+'/'+name
        response=client.post('https://storage.googleapis.com/upload/storage/v1/b/'+BUCKET+'/o',params={'uploadType':'media','name':object_name},headers={'Content-Type':mime},data=data,timeout=120)
        response.raise_for_status();assert response.json()['md5Hash']==md5
        metadata=client.patch('https://storage.googleapis.com/storage/v1/b/'+BUCKET+'/o/'+quote(object_name,safe=''),json={'cacheControl':'public,max-age=3600','contentDisposition':('attachment' if file.suffix=='.zip' else 'inline')+'; filename="'+name+'"','metadata':{'sha256':sha}},timeout=30)
        metadata.raise_for_status()
        public_url='https://storage.googleapis.com/'+BUCKET+'/'+object_name
        fetched=requests.get(public_url,timeout=120);fetched.raise_for_status();assert hashlib.sha256(fetched.content).hexdigest()==sha
        published.append({'file':name,'bytes':len(data),'sha256':sha,'url':public_url,'anonymous_download_verified':True})
        print('Published and anonymously verified '+name,flush=True)
    report={'bucket':BUCKET,'project':'locateassist','public_preview_url':'https://storage.googleapis.com/'+BUCKET+'/'+PREFIX+'/index.html','artifacts':published,'source_code_published_by_this_script':False,'approved_hackathon_video_host_url':None,'hack2skill_submitted':False,'note':'Public Cloud Storage preview/download is not a YouTube/Vimeo/Google Drive submission link.'}
    (directory/'publication.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
