"""Persistent device identity, enrollment and display configuration."""
import hashlib,json,re,secrets,time
from .core import password_hash
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$')
DEFAULT_DISPLAY={'title':'RoomGuard 校园环境监测','theme':'light','font_scale':1.0,'page_size':6,'rotation_seconds':12,'refresh_seconds':2,'alarm_first':True,'sound_enabled':True,'history_hours':24,'fields':['temperature','humidity','mq','flame'],'rooms':[],'floor':''}
class Registry:
 def __init__(self,engine):
  self.e=engine;self.db=engine.db;self.lock=engine.lock
  with self.lock:
   self.db.executescript('''CREATE TABLE IF NOT EXISTS devices(id TEXT PRIMARY KEY,status TEXT,room TEXT,floor TEXT,model TEXT,firmware TEXT,capabilities TEXT,created REAL);
CREATE TABLE IF NOT EXISTS joins(code_hash TEXT PRIMARY KEY,expires REAL,device TEXT,secret TEXT);
CREATE TABLE IF NOT EXISTS users(name TEXT PRIMARY KEY,hash TEXT,role TEXT,scopes TEXT);
CREATE TABLE IF NOT EXISTS terminals(id TEXT PRIMARY KEY,name TEXT,kind TEXT,last_seen REAL,profile TEXT,enabled INTEGER);
CREATE TABLE IF NOT EXISTS profiles(id TEXT PRIMARY KEY,config TEXT);''')
   self.db.execute('INSERT OR IGNORE INTO users VALUES(?,?,?,?)',('admin',engine.setting('admin_hash'),'teacher','[]'))
   # Existing V1.1 nodes are migrated; new installations have zero fixed devices.
   for row in self.db.execute('SELECT id,room FROM nodes').fetchall():
    self.db.execute('INSERT OR IGNORE INTO devices VALUES(?,?,?,?,?,?,?,?)',(row['id'],'active',row['room'],'','legacy','1.1','[]',time.time()))
   self.db.execute('INSERT OR IGNORE INTO profiles VALUES(?,?)',('default',json.dumps(DEFAULT_DISPLAY)))
   self.db.commit();self.refresh()
 def refresh(self):
  self.e.devices={r['id']:r['room'] for r in self.db.execute("SELECT * FROM devices WHERE status='active'")}
 def audit(self,kind,actor,device='',detail=None):
  self.e.event(device,kind,actor=actor,detail=detail);self.db.commit()
 def list(self):
  with self.lock:
   result=[dict(r) for r in self.db.execute('SELECT * FROM devices ORDER BY created')]
   for r in result:
    r['pending_join']=bool(self.db.execute("SELECT 1 FROM joins WHERE device=? AND expires>? AND secret=''",(r['id'],time.time())).fetchone())
    r['desired_config']=self.e.setting('config:'+r['id']) or {'version':0,'clear_seconds':10,'report_seconds':5,'hardware_profile':0}
    state=self.db.execute('SELECT state FROM nodes WHERE id=?',(r['id'],)).fetchone();r['applied_config_version']=json.loads(state[0]).get('config_version',0) if state else 0
    r['config_synced']=self.e.config_applied(json.loads(state[0]) if state else {},r['desired_config'])
   return result
 def ticket(self,actor):
  code=secrets.token_urlsafe(18);expires=time.time()+600
  with self.lock:
   self.db.execute('DELETE FROM joins WHERE expires<?',(time.time(),))
   self.db.execute('INSERT INTO joins VALUES(?,?,?,?)',(hashlib.sha256(code.encode()).hexdigest(),expires,'',''));self.audit('join_ticket_created',actor)
  return {'code':code,'expires':expires}
 def enroll(self,p):
  device=str(p.get('id',''));code=str(p.get('code',''))
  if not ID.fullmatch(device) or not device.startswith(('rg-','room')) or len(code)>100:raise ValueError('设备编号或接入码无效')
  caps=p.get('capabilities',[])
  if not isinstance(caps,list) or len(caps)>16 or any(not isinstance(x,str) or len(x)>32 for x in caps):raise ValueError('能力清单无效')
  digest=hashlib.sha256(code.encode()).hexdigest()
  with self.lock:
   row=self.db.execute('SELECT * FROM joins WHERE code_hash=?',(digest,)).fetchone()
   if not row or row['expires']<time.time():raise ValueError('接入码无效或过期，请向教师获取新码')
   if row['device'] and row['device']!=device:raise ValueError('接入码已绑定其他设备')
   known=self.db.execute('SELECT * FROM devices WHERE id=?',(device,)).fetchone()
   if known and known['status']=='disabled':raise ValueError('设备已停用，请教师先重新开放接入')
   if not row['device']:
    self.db.execute('UPDATE joins SET device=? WHERE code_hash=?',(device,digest))
    if not known:
     self.db.execute('INSERT INTO devices VALUES(?,?,?,?,?,?,?,?)',(device,'pending','','',str(p.get('model',''))[:32],str(p.get('firmware',''))[:32],json.dumps(p.get('capabilities',[])[:16]),time.time()))
    self.audit('join_requested','device',device)
   if row['secret']:
    return {'status':'approved','id':device,'mqtt_password':row['secret'],'mqtt_port':1883}
   return {'status':'pending','id':device}
 def approve(self,device,p,actor,provision):
  room=str(p.get('room','')).strip();floor=str(p.get('floor','')).strip()
  if not room or len(room)>40 or len(floor)>40:raise ValueError('房间名称1—40字，楼层不超过40字')
  with self.lock:
   row=self.db.execute('SELECT * FROM devices WHERE id=?',(device,)).fetchone()
   if not row:raise ValueError('设备不存在')
   if self.db.execute("SELECT id FROM devices WHERE room=? AND status='active' AND id<>?",(room,device)).fetchone():raise ValueError('房间已绑定其他在线管理设备，请先停用旧设备')
   ticket=self.db.execute('SELECT * FROM joins WHERE device=? AND expires>? ORDER BY expires DESC LIMIT 1',(device,time.time())).fetchone()
   if row['status']!='active' and not ticket:raise ValueError('无有效接入申请，请重新配网提交接入码')
   password=secrets.token_urlsafe(24)
   if row['status']!='active' or (ticket and not ticket['secret']):
    provision(device,password) # must finish before claiming success
    self.db.execute('UPDATE joins SET secret=? WHERE device=? AND expires>?',(password,device,time.time()))
   self.db.execute("UPDATE devices SET status='active',room=?,floor=? WHERE id=?",(room,floor,device))
   self.db.execute('INSERT OR IGNORE INTO nodes VALUES(?,?,?)',(device,room,'{}'));self.db.execute('UPDATE nodes SET room=? WHERE id=?',(room,device))
   if not self.e.setting('config:'+device):self.e.set_setting('config:'+device,{'version':1,'clear_seconds':10,'report_seconds':5,'hardware_profile':0,'epoch':self.e.setting('deployment_id')})
   self.refresh();self.audit('device_bound',actor,device,{'old_room':row['room'],'room':room,'floor':floor})
   return {'ok':True}
 def disable(self,device,actor,revoke):
  with self.lock:
   if not self.db.execute('SELECT 1 FROM devices WHERE id=?',(device,)).fetchone():raise ValueError('设备不存在')
   revoke(device);self.db.execute("UPDATE devices SET status='disabled' WHERE id=?",(device,));self.db.execute('DELETE FROM joins WHERE device=?',(device,));self.e.live.pop(device,None);self.refresh();self.audit('device_disabled',actor,device)
 def reopen(self,device,actor):
  with self.lock:
   self.db.execute("UPDATE devices SET status='pending' WHERE id=? AND status='disabled'",(device,));self.audit('device_reopened',actor,device)
 def users(self):
  with self.lock:return [{'name':r['name'],'role':r['role'],'scopes':json.loads(r['scopes'])} for r in self.db.execute('SELECT * FROM users')]
 def user(self,name):
  with self.lock:
   r=self.db.execute('SELECT * FROM users WHERE name=?',(name,)).fetchone();return dict(r) if r else None
 def save_user(self,p,actor):
  name=p.get('name','');role=p.get('role');scopes=p.get('scopes',[]);password=p.get('password','')
  if not ID.fullmatch(name) or role not in ['teacher','operator','viewer'] or not isinstance(scopes,list) or any(d not in self.e.devices for d in scopes):raise ValueError('账号、角色或节点范围无效')
  if name=='admin' and role!='teacher':raise ValueError('内置教师管理员不能降级')
  old=self.user(name)
  if password and not 12<=len(password)<=128:raise ValueError('密码需12—128位')
  if not old and not password:raise ValueError('新账号需要密码')
  value=password_hash(password) if password else old['hash']
  with self.lock:
   self.db.execute('INSERT OR REPLACE INTO users VALUES(?,?,?,?)',(name,value,role,json.dumps(scopes)))
   if name=='admin':self.e.set_setting('admin_hash',value)
   self.audit('user_saved',actor,detail={'name':name,'role':role,'scopes':scopes})
 def save_profile(self,name,p,actor):
  if not ID.fullmatch(name):raise ValueError('方案编号至少3个字母/数字/下划线')
  cfg=dict(DEFAULT_DISPLAY);cfg.update({k:v for k,v in p.items() if k in cfg})
  if not isinstance(cfg['title'],str) or not 1<=len(cfg['title'])<=60 or cfg['theme'] not in ['light','dark']:raise ValueError('标题或主题无效')
  for key,lo,hi in [('page_size',1,24),('rotation_seconds',5,120),('refresh_seconds',2,10)]:
   if type(cfg[key]) is not int or not lo<=cfg[key]<=hi:raise ValueError(key+'参数无效')
  if type(cfg['font_scale']) not in [int,float] or not .85<=cfg['font_scale']<=1.4:raise ValueError('字号倍率无效')
  if type(cfg['sound_enabled']) is not bool or cfg['history_hours'] not in [1,24,168,720]:raise ValueError('声音或历史窗口无效')
  if type(cfg['alarm_first']) is not bool or not isinstance(cfg['fields'],list) or any(k not in ['temperature','humidity','mq','flame'] for k in cfg['fields']):raise ValueError('字段或告警排序无效')
  if not isinstance(cfg['rooms'],list) or any(not isinstance(x,str) or len(x)>40 for x in cfg['rooms']) or not isinstance(cfg['floor'],str) or len(cfg['floor'])>40:raise ValueError('展示范围无效')
  with self.lock:self.db.execute('INSERT OR REPLACE INTO profiles VALUES(?,?)',(name,json.dumps(cfg)));self.audit('profile_saved',actor,detail={'profile':name})
 def profiles(self):
  with self.lock:return {r['id']:json.loads(r['config']) for r in self.db.execute('SELECT * FROM profiles')}
 def terminal_hello(self,p):
  t=p.get('id','')
  if not ID.fullmatch(t):raise ValueError('终端编号无效')
  with self.lock:
   if not self.db.execute('SELECT 1 FROM terminals WHERE id=?',(t,)).fetchone() and self.db.execute('SELECT COUNT(*) FROM terminals').fetchone()[0]>=200:raise ValueError('终端登记已达200，请教师清理')
   self.db.execute('INSERT OR IGNORE INTO terminals VALUES(?,?,?,?,?,?)',(t,str(p.get('name','终端'))[:40],str(p.get('kind','web'))[:20],time.time(),'default',1));self.db.execute('UPDATE terminals SET last_seen=? WHERE id=?',(time.time(),t));self.db.commit()
 def display(self,t):
  with self.lock:
   row=self.db.execute('SELECT * FROM terminals WHERE id=?',(t,)).fetchone();profile=row['profile'] if row else 'default';cfg=self.profiles().get(profile,dict(DEFAULT_DISPLAY));return {'profile':profile,'config':cfg,'enabled':bool(row['enabled']) if row else True}
