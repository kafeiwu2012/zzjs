#!/usr/bin/python3
"""Root-owned constrained helper. No shell, arbitrary paths, or arbitrary units."""
import os,sys,json,re,subprocess,tempfile,pathlib,fcntl,grp,uuid,time,sqlite3,shutil,stat,pwd
ROOT=pathlib.Path('/var/lib/roomguard');PW=pathlib.Path('/etc/mosquitto/roomguard.passwd');VALID=re.compile(r'^(?:rg-|room)[A-Za-z0-9_-]{1,60}$')
def run(args,**kwargs):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=12,**kwargs)
def record(p):
 f=pathlib.Path('/var/log/roomguard-control/maintenance.jsonl')
 fd=os.open(f,os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_NOFOLLOW,0o640)
 try:
  info=os.fstat(fd)
  if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or info.st_nlink!=1:raise ValueError('unsafe audit file')
  os.fchown(fd,0,pwd.getpwnam('roomguard').pw_gid)
  os.write(fd,(json.dumps({'time':time.time(),**p})+'\n').encode())
 finally:os.close(fd)
def deferred(kind,args):
 unit='roomguard-maint-'+uuid.uuid4().hex[:12]
 run(['/usr/bin/systemd-run','--quiet','--collect','--unit',unit,'--on-active=2s','/usr/local/sbin/roomguard-control','--execute',kind,*args])
 return {'queued':True,'job':unit,'message':'已排队，不等于执行成功；重连后查看维护记录'}
def execute(kind,args):
 if kind=='service' and len(args)==2 and args[0] in ['start','stop','restart','enable','disable'] and args[1] in ['roomguard','mosquitto']:
  run(['/usr/bin/systemctl',args[0],args[1]]);record({'kind':kind,'action':args[0],'service':args[1],'status':'completed'})
 elif kind=='restore' and len(args)==1 and re.fullmatch(r'monitor-[0-9]+\.db',args[0]):
  directory=os.open(ROOT/'backups',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
  source=os.open(args[0],os.O_RDONLY|os.O_NOFOLLOW,dir_fd=directory);os.close(directory)
  info=os.fstat(source)
  if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_uid not in [0,pwd.getpwnam('roomguard').pw_uid]:os.close(source);raise ValueError('unsafe backup')
  fd,tempname=tempfile.mkstemp(prefix='restore-',suffix='.db',dir='/var/lib/roomguard-control');path=pathlib.Path(tempname)
  try:
   with os.fdopen(source,'rb') as src,os.fdopen(fd,'wb') as dst:shutil.copyfileobj(src,dst)
   with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as c:
    if c.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('backup integrity failed')
    tables={x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {'users','devices','nodes','settings'}<=tables:raise ValueError('backup must be V2 schema')
   run(['/usr/bin/systemctl','stop','roomguard'])
   try:
    for suffix in ['-wal','-shm']:(ROOT/('monitor.db'+suffix)).unlink(missing_ok=True)
    user=pwd.getpwnam('roomguard');os.chown(path,user.pw_uid,user.pw_gid);path.chmod(0o600);os.replace(path,ROOT/'monitor.db')
   finally:run(['/usr/bin/systemctl','start','roomguard'])
  finally:path.unlink(missing_ok=True)
  record({'kind':'restore','file':args[0],'status':'completed','note':'MQTT密码文件未回滚，需核对节点连接'})
 else:raise ValueError('invalid deferred job')
if os.geteuid()!=0:raise SystemExit('requires root')
try:
 if len(sys.argv)>1:
  if sys.argv[1]!='--execute':raise ValueError()
  execute(sys.argv[2],sys.argv[3:]);sys.exit(0)
 raw=sys.stdin.read(4097)
 if len(raw)>4096:raise ValueError('too large')
 p=json.loads(raw);kind=p.get('kind')
 if kind in ['account','revoke']:
  device=p.get('device','')
  if not VALID.fullmatch(device):raise ValueError('invalid device')
  password=p.get('password','')
  if kind=='account' and (not re.fullmatch(r'[A-Za-z0-9_-]{24,80}',password)):raise ValueError('invalid secret')
  with open('/run/roomguard-control/mqtt.lock','a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX)
   fd,tmp=tempfile.mkstemp(prefix='roomguard-',dir=PW.parent);os.close(fd);tmp=pathlib.Path(tmp)
   try:
    shutil.copyfile(PW,tmp)
    if kind=='account':run(['/usr/bin/mosquitto_passwd',str(tmp),device],input=password+'\n'+password+'\n')
    else:run(['/usr/bin/mosquitto_passwd','-D',str(tmp),device])
    tmp.chmod(0o640);os.chown(tmp,0,grp.getgrnam('mosquitto').gr_gid)
    old=PW.read_bytes();os.replace(tmp,PW)
    try:run(['/usr/bin/systemctl','reload','mosquitto'])
    except Exception:PW.write_bytes(old);PW.chmod(0o640);raise
   finally:tmp.unlink(missing_ok=True)
  result={'ok':True}
 elif kind=='service':
  if p.get('service') not in ['roomguard','mosquitto'] or p.get('action') not in ['start','stop','restart','enable','disable']:raise ValueError('invalid service')
  result=deferred('service',[p['action'],p['service']])
 elif kind=='restore':
  name=p.get('file','')
  if not re.fullmatch(r'monitor-[0-9]+\.db',name):raise ValueError('invalid file')
  result=deferred('restore',[name])
 elif kind=='logs':
  service=p.get('service')
  if service not in ['roomguard','mosquitto']:raise ValueError('invalid unit')
  data=run(['/usr/bin/journalctl','-u',service,'--no-pager','-n','60','-o','short']).stdout
  data=re.sub(r'(?i)(password|token|secret|authorization|code)([=: ]+)[^\s,;]+',r'\1\2[REDACTED]',data)
  result={'logs':data[-18000:]}
 else:raise ValueError('invalid action')
 print(json.dumps(result))
except Exception as e:
 try:record({'status':'failed','error':type(e).__name__})
 except Exception:pass
 print(json.dumps({'error':'controlled operation failed'}));sys.exit(1)
