"""GitHub Actions uploader for already signed and checksum-verified artifacts."""
from pathlib import Path
import hashlib,json,subprocess
from urllib.parse import quote
ROOT=Path(__file__).resolve().parent
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(4194304),b''):h.update(block)
 return {'bytes':path.stat().st_size,'sha256':h.hexdigest()}
def api(endpoint,*args):return json.loads(subprocess.run(['gh','api',endpoint,*args],check=True,text=True,capture_output=True).stdout)
def main():
 manifest=json.loads((ROOT/'manifest.json').read_text());endpoint=f'repos/{manifest["repository"]}/releases/{manifest["release_id"]}'
 release=api(endpoint)
 if not release['draft']:raise RuntimeError('Refusing to overwrite a published release')
 for name,expected in manifest['assets'].items():
  path=ROOT/name
  if digest(path)!=expected:raise RuntimeError('Local payload checksum mismatch')
  asset=api(release['upload_url'].split('{',1)[0]+'?name='+quote(name),'--method','POST','--input',str(path),'--header','Content-Type: application/octet-stream')
  if asset['size']!=expected['bytes'] or asset.get('digest')!='sha256:'+expected['sha256'] or asset['state']!='uploaded':raise RuntimeError('Upload verification failed')
  print('Verified on GitHub: '+name,flush=True)
 release=api(endpoint,'--method','PATCH','-F','draft=false','-F','body=@'+str(ROOT/'release-notes.md'))
 if release['draft']:raise RuntimeError('Release was not published')
 print(release['html_url'],flush=True)
if __name__=='__main__':main()
