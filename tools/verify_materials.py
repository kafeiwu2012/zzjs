"""Verify the published file manifest and recursively audit archive contents."""
from pathlib import Path,PurePosixPath
import hashlib,io,json,re,zipfile,sys
R=Path(__file__).resolve().parents[1]
blocked={'.jks','.keystore','.p12','.pfx','.key','.db','.sqlite','.sqlite3'}
seen=set();issues=[];archives=0
def inspect(name,data):
 global archives
 p=PurePosixPath(name)
 if p.suffix.lower() in blocked or p.name.lower() in {'server.env','.env','id_rsa','id_ed25519'}:issues.append(name+': private-key/runtime filename')
 if p.suffix.lower()=='.zip':
  digest=hashlib.sha256(data).digest()
  if digest in seen:return
  seen.add(digest);archives+=1
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   assert z.testzip() is None,name
   for n in z.namelist():
    if not n.endswith('/'):inspect(name+'!/'+n,z.read(n))
 elif p.suffix.lower() in {'.py','.js','.java','.h','.c','.cpp','.md','.txt','.json','.sh','.ini','.conf'}:
  text=data.decode('utf-8',errors='replace')
  if re.search(r'-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----',text):issues.append(name+': private-key block')
  if re.search(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}\b',text):issues.append(name+': token pattern')
  if p.name=='secrets.h':
   vals=re.findall(r'#define\s+(WIFI_SSID|WIFI_PASSWORD|MQTT_PASSWORD)\s+"([^"]*)"',text)
   if not vals or any(v not in {'CHANGE_ME','YOUR_WIFI_SSID','YOUR_WIFI_PASSWORD','YOUR_MQTT_PASSWORD',''} for k,v in vals):issues.append(name+': non-placeholder credentials header')
count=0;manifest=R/'CHECKSUMS.sha256'
for line in manifest.read_text().splitlines():
 digest,name=line.split('  ',1);p=R/name
 assert p.is_file(),name
 data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==digest,name
 inspect(name,data);count+=1
mapping=json.loads((R/'docs/materials-index.json').read_text());assert len(mapping)==93
for rec in mapping:
 p=R/rec['repository_path'];assert p.is_file();assert hashlib.sha256(p.read_bytes()).hexdigest()==rec['uploaded_sha256'],rec['repository_path']
if issues:
 print('\n'.join(issues));sys.exit(1)
print(f'PASS: {count} file hashes, {len(mapping)} original deliverables, {archives} unique ZIPs; no excluded keys/runtime data detected.')
