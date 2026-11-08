import os,json,secrets,shutil,subprocess,time,re
from pathlib import Path
from .registry import Registry
class Management:
 def __init__(self,engine,data):self.e=engine;self.registry=Registry(engine);self.data=Path(data)
 def helper(self,p):
  if os.environ.get('DEMO')=='1' or os.environ.get('TEST_HELPER')=='1':return {'ok':True,'simulation':True}
  if os.environ.get('ENABLE_SYSTEM_MANAGEMENT')!='1':raise ValueError('系统维护工具未启用，请按V2部署手册安装')
  try:
   r=subprocess.run(['sudo','-n','/usr/local/sbin/roomguard-control'],input=json.dumps(p),text=True,capture_output=True,timeout=15,check=True)
   return json.loads(r.stdout)
  except (OSError,subprocess.SubprocessError,ValueError):raise ValueError('受限系统工具执行失败，查看服务日志并按维护手册检查')
 def provision(self,device,password):return self.helper({'kind':'account','device':device,'password':password})
 def revoke(self,device):return self.helper({'kind':'revoke','device':device})
 def backup(self,actor):
  folder=self.data/'backups';folder.mkdir(exist_ok=True,mode=0o700);name='monitor-'+str(time.time_ns())+'.db';target=folder/name
  import sqlite3
  with self.e.lock,sqlite3.connect(target) as dest:self.e.db.backup(dest)
  target.chmod(0o600)
  with self.e.lock:self.registry.audit('backup_created',actor,detail={'file':name})
  return {'file':name,'bytes':target.stat().st_size}
 def backup_list(self):
  folder=self.data/'backups';folder.mkdir(exist_ok=True,mode=0o700)
  return [{'file':p.name,'bytes':p.stat().st_size,'time':p.stat().st_mtime} for p in sorted(folder.glob('monitor-*.db'),reverse=True) if not p.is_symlink()][:100]
 def services(self):
  result={'services':[],'disk':dict(zip(['total','used','free'],shutil.disk_usage(self.data))),'broker_online':self.e.broker_online}
  for unit in ['roomguard','mosquitto']:
   try:state=subprocess.run(['systemctl','is-active',unit],capture_output=True,text=True,timeout=3).stdout.strip()
   except (OSError,subprocess.SubprocessError):state='unavailable'
   try:enabled=subprocess.run(['systemctl','is-enabled',unit],capture_output=True,text=True,timeout=3).stdout.strip()
   except (OSError,subprocess.SubprocessError):enabled='unavailable'
   result['services'].append({'name':unit,'state':state,'autostart':enabled})
  result['simulation']=os.environ.get('DEMO')=='1';return result
