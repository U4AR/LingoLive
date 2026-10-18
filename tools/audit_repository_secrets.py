"""Audit all fetched Git history and optional archives without logging secret values.

Fetch branches/tags first. Requires Python, PyMuPDF and (with --ocr) tesseract.
Never verifies candidate credentials by making authenticated provider requests.
"""
import argparse,base64,collections,hashlib,html,io,json,math,re,subprocess,time,urllib.parse,zipfile
from pathlib import Path
import fitz
P=argparse.ArgumentParser();P.add_argument('--repo',default=str(Path(__file__).resolve().parents[1]));P.add_argument('--archive',action='append',default=[]);P.add_argument('--output',required=True);P.add_argument('--ocr',action='store_true');a=P.parse_args()
def git(*args):return subprocess.check_output(['git','-C',a.repo,*args])
RULES={
 'google_api_key':r'(?<![A-Za-z0-9])(?:AIza[A-Za-z0-9_-]{30,}|AQ\.[A-Za-z0-9_-]{30,})',
 'google_oauth_access_token':r'ya29\.[A-Za-z0-9_.-]{25,}',
 'google_oauth_client_secret':r'GOCSPX-[A-Za-z0-9_-]{15,}',
 'google_oauth_authorization_code':r'4/0A[A-Za-z0-9_-]{25,}',
 'github_token':r'(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,})',
 'private_key':r'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED |DSA )?PRIVATE KEY-----',
 'aws_access_key':r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
 'slack_token':r'\bxox[baprs]-[A-Za-z0-9-]{20,}',
 'stripe_secret':r'\b(?:sk_live_|rk_live_)[A-Za-z0-9]{16,}',
 'generic_secret_key':r'\bsk-(?:proj-)?[A-Za-z0-9_-]{30,}',
 'bearer_jwt':r'\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{15,}',
 'url_embedded_password':r'https?://[^\s/@:]{2,}:[^\s/@]{8,}@',
}
RULES={k:re.compile(v) for k,v in RULES.items()}
ASSIGN=re.compile(r'''(?i)["']?(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|access[_-]?code|password|private[_-]?key)["']?\s*[:=]\s*["']([^"'\r\n]{8,})["']''')
findings=[];notices=[];stats=collections.Counter();seen_findings=set();seen_embedded=set();image_cache={}
PLACEHOLDERS=re.compile(r'(?i)(?:example|placeholder|test|fixture|dummy|invalid|replace|your[-_ ]|not[-_ ]real|demo|SECRET[_-]REF|process\.|os\.environ|assert|access[_ -]code|api[_ -]key|token[_ -]file|\bsecret\b)')
def add(rule,label,value):
 key=(rule,hashlib.sha256(value.encode()).hexdigest())
 if key in seen_findings:return
 seen_findings.add(key);findings.append({'rule':rule,'location':label,'value_sha256':key[1]})
def textscan(s,label):
 stats['text_views']+=1
 views={s,html.unescape(s),urllib.parse.unquote(s)}
 if '\\u' in s:
  views.add(re.sub(r'\\u([a-fA-F0-9]{4})',lambda m:chr(int(m[1],16)),s))
 if '\\n' in s:views.add(s.replace('\\n','\n'))
 for view in views:
  for k,p in RULES.items():
   for m in p.finditer(view):add(k,label,m[0])
  for m in ASSIGN.finditer(view):
   val=m[1]
   if PLACEHOLDERS.search(val) or not re.fullmatch(r'[A-Za-z0-9_./+!@#$%^&*=-]{16,}',val):continue
   freq=collections.Counter(val);ent=-sum(n/len(val)*math.log2(n/len(val)) for n in freq.values())
   if ent>=3.5 and re.search('[A-Za-z]',val) and re.search('[0-9]',val):add('suspicious_literal_secret_assignment',label,val)
 # Decode standalone base64 literals only, never execute their contents.
 for m in re.finditer(r'''["']([A-Za-z0-9+/]{40,}={0,2})["']''',s):
  try:
   raw=base64.b64decode(m[1],validate=True)
   dec=raw.decode('utf-8')
  except (ValueError,UnicodeError):continue
  if any(p.search(dec) for p in RULES.values()):
   for k,p in RULES.items():
    for match in p.finditer(dec):add('base64_'+k,label,match[0])
def scan(raw,label,depth=0):
 stats['payloads']+=1
 textscan(raw.decode('utf-8','replace'),label)
 if raw[:2] in (b'\xff\xfe',b'\xfe\xff'):textscan(raw.decode('utf-16','replace'),label+'#utf16')
 if depth>4:
  notices.append({'location':label,'reason':'archive nesting limit'});return
 if zipfile.is_zipfile(io.BytesIO(raw)):
  try:
   with zipfile.ZipFile(io.BytesIO(raw)) as z:
    for info in z.infolist():
     if info.is_dir():continue
     stats['archive_members']+=1
     if info.file_size>50*1024*1024:raise ValueError('member >50MiB')
     scan(z.read(info),label+'!'+info.filename,depth+1)
  except Exception as e:notices.append({'location':label,'reason':'archive scan '+type(e).__name__})
 elif raw.startswith(b'%PDF-'):
  try:
   with fitz.open(stream=raw,filetype='pdf') as doc:
    stats['pdf_documents']+=1
    for i,page in enumerate(doc):
     textscan(page.get_text(),label+f'#page{i+1}')
     if a.ocr and len(page.get_text().strip())<30:
      img=page.get_pixmap(matrix=fitz.Matrix(1.5,1.5));ocr(img.tobytes('png'),label+f'#page{i+1}')
  except Exception as e:notices.append({'location':label,'reason':'PDF scan '+type(e).__name__})
 elif raw.startswith((b'\x89PNG',b'\xff\xd8\xff',b'GIF87',b'GIF89',b'RIFF')):
  if a.ocr and not raw.startswith(b'RIFF'):ocr(raw,label)
  else:stats['images_not_ocr']+=1

def ocr(raw,label):
 sha=hashlib.sha256(raw).hexdigest()
 if sha not in image_cache:
  try:
   r=subprocess.run(['tesseract','stdin','stdout','-l','eng','--psm','11'],input=raw,capture_output=True,timeout=40,check=True)
   image_cache[sha]=r.stdout.decode('utf-8','replace');stats['images_ocr_unique']+=1
  except Exception as e:notices.append({'location':label,'reason':'OCR '+type(e).__name__});return
 textscan(image_cache[sha],label+'#ocr')

reachable={s.split(' ',1)[0]:s.partition(' ')[2] for s in git('rev-list','--objects','--all').decode().splitlines()}
objects=git('cat-file','--batch-all-objects','--batch-check=%(objectname) %(objecttype) %(objectsize)').decode().splitlines()
for i,row in enumerate(objects):
 oid,kind,size=row.split()
 if kind not in ('blob','commit','tag'):continue
 raw=git('cat-file',kind,oid);stats[kind+'_objects']+=1
 label=reachable.get(oid) or kind+':'+oid
 scan(raw,label)
 if i%100==0:print(json.dumps({'progress_object':i,'total':len(objects),'findings':len(findings)}),flush=True)
# Include uncommitted but intended source, and user-requested final downloadable archives.
status=git('status','--porcelain=v1','-z').decode().split('\0')
for row in status:
 if not row:continue
 p=Path(a.repo)/row[3:]
 if p.is_file():scan(p.read_bytes(),'working-tree:'+row[3:]);stats['changed_files']+=1
for file in a.archive:
 p=Path(file);scan(p.read_bytes(),'archive:'+p.name);stats['external_archives']+=1
report={
 'audit_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'repository':'https://github.com/U4AR/LingoLive',
 'head_commit':git('rev-parse','HEAD').decode().strip(),
 'reachable_commits':int(git('rev-list','--all','--count')),
 'refs':git('for-each-ref','--format=%(refname)').decode().splitlines(),
 'scope':'All local Git objects, including commit/tag messages and unreachable objects, after fetching every remote branch and tag. Current changed source and supplied archives also scanned. Archive members decompressed, PDF text extracted, image text OCR where enabled. URL/HTML/Unicode escape and selected base64 decoding included.',
 'audited_archives':[{'file':Path(f).name,'bytes':Path(f).stat().st_size,'sha256':hashlib.sha256(Path(f).read_bytes()).hexdigest()} for f in a.archive],
 'counts':dict(stats),'unresolved_findings':findings,'incomplete_scan_items':notices,
 'limits':'Pattern and suspicious-literal scan plus English OCR; not a guarantee against every unknown secret format, obfuscation, OCR error, remote inaccessible/deleted Git object, or external fork/cache. Credential values never logged.',
}
Path(a.output).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
raise SystemExit(bool(findings or notices))
