"""Thread-safe state engine. Deadlines are monotonic; SQLite stores UTC timestamps."""
import os, csv, hashlib, hmac, io, json, math, secrets, sqlite3, threading, time
from pathlib import Path
DEVICES = {'room101-esp32': '101', 'room102-esp8266': '102'}

def password_hash(value, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt + ':' + hashlib.pbkdf2_hmac('sha256', value.encode(), bytes.fromhex(salt), 260000).hex()

def password_ok(value, encoded):
    try: return hmac.compare_digest(password_hash(value, encoded.split(':')[0]), encoded)
    except (ValueError, IndexError): return False

class Engine:
    def __init__(self, db_path, admin_password=None, clock=time.monotonic, wall=time.time):
        self.clock, self.wall = clock, wall
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(db_path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS nodes(id TEXT PRIMARY KEY,room TEXT NOT NULL,state TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS samples(id INTEGER PRIMARY KEY,device TEXT,ts REAL,boot TEXT,seq INTEGER,payload TEXT,UNIQUE(device,boot,seq));
CREATE INDEX IF NOT EXISTS sample_time ON samples(device,ts);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,ts REAL,device TEXT,kind TEXT,event_id TEXT,actor TEXT,detail TEXT);
CREATE INDEX IF NOT EXISTS event_time ON events(ts);
CREATE TABLE IF NOT EXISTS commands(id TEXT PRIMARY KEY,device TEXT,kind TEXT,event_id TEXT,created REAL,status TEXT,payload TEXT,result TEXT);
''')
        if not self.setting('admin_hash'):
            if not admin_password or len(admin_password) < 12: raise ValueError('首次启动需设置至少12位 ADMIN_PASSWORD')
            self.set_setting('admin_hash', password_hash(admin_password))
        if not self.setting('deployment_id'):self.set_setting('deployment_id',secrets.token_hex(12))
        if not self.setting('retention'): self.set_setting('retention', {'samples':30,'events':180})
        for d, room in (DEVICES.items() if os.environ.get('BOOTSTRAP_LEGACY_NODES')=='1' else []):
            self.db.execute('INSERT OR IGNORE INTO nodes VALUES(?,?,?)',(d,room,'{}'))
            if not self.setting('config:'+d): self.set_setting('config:'+d, {'version':1,'clear_seconds':10})
        self.db.execute("UPDATE commands SET status='unconfirmed',result='server restarted before confirmation' WHERE status='sent'")
        self.db.commit()
        self.devices={r['id']:r['room'] for r in self.db.execute('SELECT id,room FROM nodes')}
        self.intervals = {}
        self.live = {}  # no node presumed online after server restart
        self.boots = {} # bounded prior boots and sequence, used against delayed messages
        self.deadlines = {}
        self.publisher = None
        self.broker_online = False
    def setting(self,key):
        with self.lock:
            row=self.db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
            return json.loads(row[0]) if row else None
    def set_setting(self,key,value):
        with self.lock:
            self.db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(key,json.dumps(value)))
            self.db.commit()
    def event(self,device,kind,event_id='',actor='system',detail=None):
        detail=dict(detail or {})
        if device in getattr(self,'devices',{}):detail.setdefault('room_at_event',self.devices[device])
        self.db.execute('INSERT INTO events(ts,device,kind,event_id,actor,detail) VALUES(?,?,?,?,?,?)',
                        (self.wall(),device,kind,event_id,actor,json.dumps(detail or {},ensure_ascii=False)))
    @staticmethod
    def validate(p):
        if not isinstance(p,dict): raise ValueError('object required')
        for k in ('boot','event_id'):
            if not isinstance(p.get(k),str) or len(p[k])>80: raise ValueError(k)
        if not p['boot'] or type(p.get('seq')) is not int or not 0<=p['seq']<=4294967295: raise ValueError('sequence')
        for k in ('active','muted','smoke','flame','dht_ok','mq_ready'):
            if type(p.get(k)) is not bool: raise ValueError(k)
        reasons=p.get('reasons')
        if not isinstance(reasons,list) or any(x not in ['smoke','flame'] for x in reasons) or len(set(reasons))!=len(reasons): raise ValueError('reasons')
        if not p['active'] and (reasons or p['muted']): raise ValueError('inactive state')
        if p['active'] and not p['event_id']: raise ValueError('event_id')
        for k in ('temperature','humidity','mq_raw','mq_voltage'):
            v=p.get(k)
            if v is not None and (type(v) not in (int,float) or not math.isfinite(v)): raise ValueError(k)
        if p['dht_ok'] and (p.get('temperature') is None or p.get('humidity') is None or not -10<=p['temperature']<=70 or not 0<=p['humidity']<=100): raise ValueError('DHT range')
        if type(p.get('config_version')) is not int or not 0<=p['config_version']<=2147483647: raise ValueError('config_version')
        if not p['dht_ok']: p['temperature']=p['humidity']=None
        if 'report_seconds' in p and (type(p['report_seconds']) is not int or not 5<=p['report_seconds']<=60):raise ValueError('report_seconds')
        return p
    @staticmethod
    def config_applied(p,cfg):
        if p.get('config_version')!=cfg['version']:return False
        if cfg.get('epoch') and p.get('config_epoch')!=cfg['epoch']:return False
        if p.get('firmware')=='2.0':
            for k,default in [('clear_seconds',10),('report_seconds',5),('hardware_profile',0)]:
                if p.get(k)!=cfg.get(k,default):return False
        return True
    def ingest(self,device,p):
        if device not in self.devices: raise ValueError('unknown device')
        p=self.validate(dict(p))
        with self.lock:
            boot,seq=p['boot'],p['seq']
            prev=self.db.execute('SELECT state FROM nodes WHERE id=?',(device,)).fetchone()
            old=json.loads(prev[0]); now=self.clock()
            history=self.boots.setdefault(device,{})
            # Reject old boot packets once a newer boot has been observed.
            if boot in history and (history.get('_current')!=boot or seq<=history[boot]): return False
            if boot==old.get('boot') and seq<=old.get('seq',-1): return False
            history[boot]=seq; history['_current']=boot
            if len(history)>16:
                for key in list(history):
                    if key not in (boot,'_current'): del history[key]; break
            if device not in self.live:
                self.event(device,'online',detail={'boot':boot})
            if p['active'] and (not old.get('active') or p['event_id']!=old.get('event_id')):
                self.event(device,'alarm',p['event_id'],detail={'reasons':p['reasons']})
            elif p['active'] and p['reasons']!=old.get('reasons'):
                self.event(device,'reasons',p['event_id'],detail={'reasons':p['reasons']})
            elif not p['active'] and old.get('active'):
                self.event(device,'recovered',old.get('event_id',''))
            if old.get('active') and p['active'] and p['event_id']!=old.get('event_id'):
                self.event(device,'interrupted',old.get('event_id',''),detail={'reason':'new event or device restart; prior recovery not observed'})
            if old and (old.get('dht_ok')!=p['dht_ok'] or old.get('mq_ready')!=p['mq_ready']):
                self.event(device,'health',detail={'dht_ok':p['dht_ok'],'mq_ready':p['mq_ready']})
            p['last_seen']=self.wall();p['room_at_sample']=self.devices[device]
            raw=json.dumps(p,ensure_ascii=False)
            self.db.execute('UPDATE nodes SET state=? WHERE id=?',(raw,device))
            self.db.execute('INSERT OR IGNORE INTO samples(device,ts,boot,seq,payload) VALUES(?,?,?,?,?)',(device,self.wall(),boot,seq,raw))
            self.intervals[device]=p.get('report_seconds',5)
            self.live[device]=now
            # An authoritative state is also evidence that a configuration was applied.
            cfg=self.setting('config:'+device)
            if cfg.get('epoch') and p.get('config_epoch')==cfg['epoch'] and p['config_version']>cfg['version']:
                cfg['version']=p['config_version']+1;self.set_setting('config:'+device,cfg);self.event(device,'config_version_reconciled',detail={'version':cfg['version']})
            if self.config_applied(p,cfg):
                self.db.execute("UPDATE commands SET status='applied',result='state confirmed' WHERE device=? AND kind='config' AND status IN ('pending','sent')",(device,))
            self.db.commit()
            if not self.config_applied(p,cfg) and self.publisher:
                # Config synchronization is idempotent; never replay silence commands.
                self.publisher(device,{'id':'sync-'+cfg.get('epoch','legacy')[-8:]+'-'+str(cfg['version']),'kind':'config',**cfg,'ttl_ms':10000,'nonce':p.get('control_nonce','')})
            return True
    def tick(self):
        with self.lock:
            for d,t in list(self.live.items()):
                if self.clock()-t>=max(20,self.intervals.get(d,5)*4):
                    del self.live[d]; self.event(d,'offline')
            for cid,end in list(self.deadlines.items()):
                if self.clock()>=end:
                    self.db.execute("UPDATE commands SET status='unconfirmed' WHERE id=? AND status IN ('sent','pending')",(cid,))
                    del self.deadlines[cid]
            self.db.commit()
    def snapshot(self):
        self.tick()
        with self.lock:
            nodes=[]
            for row in self.db.execute('SELECT * FROM nodes ORDER BY room'):
                if row['id'] not in self.devices:continue
                s=json.loads(row['state']);cfg=self.setting('config:'+row['id'])
                eid=s.get('event_id','')
                ack=self.db.execute("SELECT id FROM events WHERE device=? AND event_id=? AND kind='confirmed' LIMIT 1",(row['id'],eid)).fetchone()
                nodes.append({'id':row['id'],'room':row['room'],'online':row['id'] in self.live,'state':s,'desired_config':cfg,'config_synced':self.config_applied(s,cfg),'confirmed':bool(ack)})
            return {'nodes':nodes,'server_time':self.wall(),'time_trusted':getattr(self,'time_trusted',False),'broker_online':self.broker_online}
    def confirm(self,device,event_id,actor):
        with self.lock:
            self._current(device,event_id)
            exists=self.db.execute("SELECT id FROM events WHERE device=? AND event_id=? AND kind='confirmed'",(device,event_id)).fetchone()
            if not exists:self.event(device,'confirmed',event_id,actor)
            self.db.commit()
    def _current(self,device,event_id):
        if device not in self.devices: raise ValueError('设备不存在')
        s=json.loads(self.db.execute('SELECT state FROM nodes WHERE id=?',(device,)).fetchone()[0])
        if not s.get('active') or not event_id or s.get('event_id')!=event_id: raise ValueError('告警事件已变化，请刷新')
        return s
    def command(self,device,kind,actor,event_id='',clear_seconds=None,report_seconds=None,hardware_profile=None):
        self.tick()
        if device not in self.devices: raise ValueError('设备不存在')
        with self.lock:
            cid=secrets.token_hex(12)
            state=json.loads(self.db.execute('SELECT state FROM nodes WHERE id=?',(device,)).fetchone()[0])
            p={'id':cid,'kind':kind,'ttl_ms':10000,'nonce':state.get('control_nonce','')}
            if kind=='silence':
                self._current(device,event_id)
                if device not in self.live or not self.broker_online: raise ValueError('节点或消息代理离线，拒绝消音')
                p['event_id']=event_id
            elif kind=='config':
                if type(clear_seconds) is not int or not 1<=clear_seconds<=300: raise ValueError('解除时间须为1—300秒整数')
                cfg=self.setting('config:'+device)
                report=report_seconds if report_seconds is not None else cfg.get('report_seconds',5)
                profile=hardware_profile if hardware_profile is not None else cfg.get('hardware_profile',0)
                if type(report) is not int or not 5<=report<=60 or type(profile) is not int or profile not in (0,1):raise ValueError('上报5—60秒，硬件模板只能0或1')
                cfg={'version':max(cfg['version'],state.get('config_version',0))+1,'clear_seconds':clear_seconds,'report_seconds':report,'hardware_profile':profile,'epoch':cfg.get('epoch','')}
                self.set_setting('config:'+device,cfg);p.update(cfg)
                self.db.execute("UPDATE commands SET status='superseded' WHERE device=? AND kind='config' AND status IN ('pending','sent','unconfirmed')",(device,))
            else: raise ValueError('未知指令')
            connected=device in self.live and self.broker_online
            status='sent' if connected else 'pending'
            self.db.execute('INSERT INTO commands VALUES(?,?,?,?,?,?,?,?)',(cid,device,kind,event_id,self.wall(),status,json.dumps(p),''))
            self.event(device,'command',event_id,actor,{'id':cid,**p});self.db.commit()
            if connected:
                self.deadlines[cid]=self.clock()+10
                if not self.publisher or not self.publisher(device,p):
                    self.db.execute("UPDATE commands SET status='unconfirmed',result='publish failed' WHERE id=?",(cid,));self.db.commit()
            return {'id':cid,'status':self.db.execute('SELECT status FROM commands WHERE id=?',(cid,)).fetchone()[0]}
    def ack(self,device,p):
        if device not in self.devices or not isinstance(p,dict):return
        with self.lock:
            row=self.db.execute('SELECT * FROM commands WHERE id=? AND device=?',(str(p.get('id','')),device)).fetchone()
            if not row or row['status'] not in ('sent','pending','unconfirmed'):return
            if p.get('status') not in ('applied','rejected'):return
            self.db.execute('UPDATE commands SET status=?,result=? WHERE id=?',(p['status'],str(p.get('reason',''))[:200],row['id']))
            self.deadlines.pop(row['id'],None)
            self.event(device,'command_result',row['event_id'],detail={'id':row['id'],'status':p['status']})
            self.db.commit()
    def history(self,kind,device=None,start=0,end=None,limit=1000):
        if kind not in ('samples','events','commands'):raise ValueError('类型错误')
        end=end or self.wall()+1
        if not math.isfinite(start) or not math.isfinite(end) or end<start:raise ValueError('时间范围错误')
        limit=max(1,min(int(limit),10000))
        col='created' if kind=='commands' else 'ts'
        query=f'SELECT * FROM {kind} WHERE {col} BETWEEN ? AND ?'; args=[float(start),float(end)]
        if device:
            if device not in self.devices: raise ValueError('设备不存在')
            query+=' AND device=?';args.append(device)
        query+=f' ORDER BY {col} DESC LIMIT ?';args.append(limit)
        with self.lock:return [dict(x) for x in self.db.execute(query,args)]
    def trend(self,device,start,end,points=240):
        if device not in self.devices:raise ValueError('设备不存在')
        if not math.isfinite(start) or not math.isfinite(end) or end<=start or end-start>366*86400:raise ValueError('时间范围须在366天内')
        bucket=max(5,(end-start)/min(max(points,20),1000))
        query="""SELECT CAST((ts-?)/? AS INTEGER) AS bucket,AVG(ts) AS ts,
 AVG(CASE WHEN json_extract(payload,'$.dht_ok') THEN json_extract(payload,'$.temperature') END) AS temperature,
 AVG(CASE WHEN json_extract(payload,'$.dht_ok') THEN json_extract(payload,'$.humidity') END) AS humidity,
 AVG(CASE WHEN json_extract(payload,'$.mq_ready') THEN json_extract(payload,'$.mq_raw') END) AS mq_raw,
 MIN(CAST(json_extract(payload,'$.dht_ok') AS INTEGER)) AS all_dht_valid,
 MIN(ts) AS first_ts,MAX(ts) AS last_ts,COUNT(*) AS count
 FROM samples WHERE device=? AND ts BETWEEN ? AND ? GROUP BY bucket ORDER BY bucket"""
        with self.lock:return {'bucket_seconds':bucket,'rows':[dict(r) for r in self.db.execute(query,(start,bucket,device,start,end))]}
    def export(self,kind,device,start,end):
        rows=self.history(kind,device,start,end,10000)
        buf=io.StringIO();w=csv.writer(buf)
        if kind=='samples':
            headers=['time_utc','device','room','temperature_C','humidity_pct','dht_ok','mq_ready','mq_raw','mq_voltage_V','active','reasons']
            w.writerow(headers)
            for r in reversed(rows):
                p=json.loads(r['payload']); w.writerow([time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(r['ts'])),r['device'],(lambda v: "'"+v if str(v).startswith(('=','+','-','@','\t','\r')) else v)(p.get('room_at_sample',self.devices.get(r['device'],''))),p.get('temperature'),p.get('humidity'),p['dht_ok'],p['mq_ready'],p.get('mq_raw'),p.get('mq_voltage'),p['active'],','.join(p['reasons'])])
        elif rows:
            w.writerow(rows[0].keys())
            for r in rows:
                w.writerow([("'"+str(v)) if str(v).startswith(('=','+','-','@','\t','\r')) else v for v in r.values()])
        else:w.writerow(['no records'])
        return '\ufeff'+buf.getvalue()
    def cleanup(self):
        with self.lock:
            keep=self.setting('retention')
            for table,days,col in [('samples',keep['samples'],'ts'),('events',keep['events'],'ts'),('commands',keep['events'],'created')]:
                self.db.execute(f'DELETE FROM {table} WHERE {col}<?',(self.wall()-days*86400,))
            self.db.commit()
