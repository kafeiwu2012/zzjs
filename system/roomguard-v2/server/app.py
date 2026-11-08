import asyncio, json, logging, os, secrets, shutil, subprocess, time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from .core import Engine, DEVICES, password_ok, password_hash
from .management import Management

log=logging.getLogger('roomguard')
DATA=Path(os.environ.get('DATA_DIR','./data'));DATA.mkdir(parents=True,exist_ok=True)
engine=Engine(DATA/'monitor.db',os.environ.get('ADMIN_PASSWORD'))
management=Management(engine,DATA);registry=management.registry
sessions={}; failures=defaultdict(deque)
mqtt_client=None

def bridge_start():
    global mqtt_client
    import paho.mqtt.client as mqtt
    client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='roomguard-server',clean_session=True)
    client.username_pw_set(os.environ.get('MQTT_USER','server'),os.environ.get('MQTT_PASSWORD',''))
    def connect(c,u,f,rc,props):
        engine.broker_online=rc==0
        if rc==0:
            c.subscribe('building/+/state',1);c.subscribe('building/+/ack',1)
    def disconnect(c,u,flags,rc,props):engine.broker_online=False
    def message(c,u,msg):
        try:
            _,device,kind=msg.topic.split('/')
            if len(msg.payload)>8192:raise ValueError('payload too large')
            p=json.loads(msg.payload)
            if kind=='state':engine.ingest(device,p)
            elif kind=='ack':engine.ack(device,p)
        except Exception:log.exception('Rejected MQTT message on %s',msg.topic)
    client.on_connect=connect;client.on_disconnect=disconnect;client.on_message=message
    client.reconnect_delay_set(1,15)
    client.connect_async(os.environ.get('MQTT_HOST','127.0.0.1'),int(os.environ.get('MQTT_PORT','1883')),30)
    client.loop_start();mqtt_client=client
    def publish(device,p):
        info=client.publish('building/'+device+'/command',json.dumps(p),qos=1,retain=False)
        return info.rc==mqtt.MQTT_ERR_SUCCESS
    engine.publisher=publish

@asynccontextmanager
async def lifespan(app):
    if os.environ.get('DISABLE_MQTT')!='1':bridge_start()
    async def maintenance():
        n=0
        while True:
            engine.tick();n+=1
            if n%3600==0:engine.cleanup()
            if n%60==0:
                with engine.lock:engine.db.execute('DELETE FROM joins WHERE expires<?',(time.time(),));engine.db.commit()
            if n%60==1:
                def trusted():
                    try:return subprocess.run(['timedatectl','show','-p','NTPSynchronized','--value'],capture_output=True,text=True,timeout=2).stdout.strip()=='yes'
                    except (OSError,subprocess.SubprocessError):return False
                if await asyncio.to_thread(trusted):engine.time_trusted=True
            # expire sessions and rate-limit bookkeeping with monotonic time
            for key in list(sessions):
                if sessions[key]['expires']<time.monotonic():del sessions[key]
            await asyncio.sleep(1)
    task=asyncio.create_task(maintenance())
    yield
    task.cancel()
    if mqtt_client:mqtt_client.loop_stop();mqtt_client.disconnect()

app=FastAPI(title='RoomGuard 局域网监控',lifespan=lifespan,docs_url=None,redoc_url=None)

@app.middleware('http')
async def headers(request,call_next):
    if request.headers.get('content-length','0').isdigit() and int(request.headers.get('content-length','0'))>16384:
        return Response(status_code=413)
    r=await call_next(request)
    r.headers['X-Content-Type-Options']='nosniff';r.headers['X-Frame-Options']='SAMEORIGIN'
    r.headers['Referrer-Policy']='same-origin'
    r.headers['Cache-Control']='no-store' if request.url.path.startswith('/api') else 'no-cache'
    return r

async def object_body(request):
    raw=await request.body()
    if len(raw)>16384:raise HTTPException(413,'请求过大')
    try:p=json.loads(raw)
    except (ValueError,UnicodeError):raise HTTPException(400,'无效JSON')
    if not isinstance(p,dict):raise HTTPException(400,'JSON对象必需')
    return p

def identity(request):
    token=request.headers.get('authorization','').removeprefix('Bearer ')
    session=sessions.get(token)
    if not session or session['expires']<time.monotonic():raise HTTPException(401,'请登录或会话已过期')
    user=registry.user(session['name'])
    if not user:raise HTTPException(401,'账号不存在')
    return user

def admin(request):
    user=identity(request)
    if user['role']!='teacher':raise HTTPException(403,'仅教师管理员可操作')
    return user['name']

def authorize_node(request,device):
    user=identity(request)
    if user['role']=='viewer' or (user['role']=='operator' and device not in json.loads(user['scopes'])):raise HTTPException(403,'无该节点操作权限')
    return user['name']

def history_access(request,device):
    user=identity(request)
    if user['role']!='teacher' and (not device or device not in json.loads(user['scopes'])):raise HTTPException(403,'请选择被授权节点')

def require_device(d):
    if d not in engine.devices:raise HTTPException(404,'设备未启用或不存在')

@app.get('/api/status')
def status(request:Request):
    s=engine.snapshot();s['disk_free_mb']=shutil.disk_usage(DATA).free//1048576
    s['demo']=os.environ.get('DEMO')=='1'
    if request.headers.get('authorization'):
        user=identity(request)
        if user['role']!='teacher':s['nodes']=[n for n in s['nodes'] if n['id'] in json.loads(user['scopes'])]
    meta={r['id']:r for r in registry.list()}
    for node in s['nodes']:
        info=meta.get(node['id'],{});node.update({k:info.get(k,'') for k in ['floor','model','firmware']})
    return s

@app.post('/api/login')
async def login(request:Request):
    body=await object_body(request);ip=request.client.host if request.client else 'local';now=time.monotonic()
    q=failures[ip]
    while q and now-q[0]>300:q.popleft()
    if len(q)>=10:raise HTTPException(429,'尝试过多，5分钟后重试')
    user=registry.user(str(body.get('username','')))
    if not user or not password_ok(str(body.get('password','')),user['hash']):
        q.append(now);raise HTTPException(401,'账号或密码错误')
    q.clear();token=secrets.token_urlsafe(32);sessions[token]={'name':user['name'],'expires':now+8*3600}
    return {'token':token,'expires_in':28800,'role':user['role'],'name':user['name']}

@app.post('/api/logout')
def logout(request:Request):
    token=request.headers.get('authorization','').removeprefix('Bearer ');sessions.pop(token,None)
    return {'ok':True}

@app.post('/api/password')
async def change_password(request:Request):
    actor=admin(request);p=await object_body(request)
    if not password_ok(str(p.get('old','')),registry.user(actor)['hash']):raise HTTPException(400,'原密码错误')
    new=p.get('new','')
    if not isinstance(new,str) or not 12<=len(new)<=128:raise HTTPException(400,'新密码须为12—128位')
    encoded=password_hash(new)
    with engine.lock:engine.db.execute('UPDATE users SET hash=? WHERE name=?',(encoded,actor));engine.db.commit()
    if actor=='admin':engine.set_setting('admin_hash',encoded)
    sessions.clear()
    with engine.lock:engine.event('','password_changed',actor=actor);engine.db.commit()
    return {'ok':True}

@app.post('/api/nodes/{device}/{action}')
async def operate(device:str,action:str,request:Request):
    actor=authorize_node(request,device);require_device(device);p=await object_body(request)
    try:
        if action=='confirm':engine.confirm(device,p.get('event_id',''),actor);return {'ok':True}
        if action=='silence':return engine.command(device,'silence',actor,p.get('event_id',''))
        if action=='config':
            admin(request)
            meta=next((n for n in registry.list() if n['id']==device),{})
            if meta.get('firmware')!='2.0' and (p.get('report_seconds',5)!=5 or p.get('hardware_profile',0)!=0):raise ValueError('旧固件不支持这些参数，请先升级V2固件')
            return engine.command(device,'config',actor,clear_seconds=p.get('clear_seconds'),report_seconds=p.get('report_seconds'),hardware_profile=p.get('hardware_profile'))
        raise HTTPException(404,'操作不存在')
    except ValueError as e:raise HTTPException(409,str(e))

@app.get('/api/history')
def history(request:Request,kind:str='events',device:str|None=None,start:float=0,end:float|None=None,limit:int=1000):
    history_access(request,device)
    try:return {'rows':engine.history(kind,device,start,end,limit)}
    except ValueError as e:raise HTTPException(400,str(e))

@app.get('/api/trend')
def trend(request:Request,device:str,start:float,end:float,points:int=240):
    history_access(request,device)
    try:return engine.trend(device,start,end,points)
    except ValueError as e:raise HTTPException(400,str(e))

@app.get('/api/export')
def export(request:Request,kind:str='events',device:str|None=None,start:float=0,end:float|None=None):
    history_access(request,device)
    try:data=engine.export(kind,device,start,end)
    except ValueError as e:raise HTTPException(400,str(e))
    return Response(data,media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="roomguard-'+kind+'.csv"'})

@app.get('/api/settings')
def settings(request:Request):
    admin(request);return {'retention':engine.setting('retention')}

@app.post('/api/settings')
async def update_settings(request:Request):
    actor=admin(request);p=await object_body(request)
    if any(type(p.get(k)) is not int or not 1<=p[k]<=3650 for k in ['samples','events']):raise HTTPException(400,'保存天数须为1—3650整数')
    engine.set_setting('retention',{k:p[k] for k in ['samples','events']})
    with engine.lock:engine.event('','retention_changed',actor=actor,detail=p);engine.db.commit()
    return {'ok':True}

@app.post('/api/time')
async def set_time(request:Request):
    actor=admin(request);p=await object_body(request);epoch=p.get('epoch')
    if type(epoch) not in (int,float) or not 1735689600<=epoch<=4102444800:raise HTTPException(400,'时间应在2025—2100年')
    if os.environ.get('ENABLE_CLOCK_SET')!='1':raise HTTPException(409,'管理员尚未安装或启用受限校时工具，见部署手册')
    before=time.time()
    try:
        subprocess.run(['sudo','-n','/usr/local/sbin/roomguard-set-time',str(int(epoch))],check=True,timeout=8,capture_output=True)
    except (OSError,subprocess.SubprocessError):raise HTTPException(503,'系统校时失败，请检查服务日志及受限校时工具')
    with engine.lock:engine.event('','clock_set',actor=actor,detail={'before':before,'after':time.time()});engine.db.commit()
    engine.time_trusted=True
    return {'ok':True,'server_time':time.time()}

@app.post('/api/demo/{device}')
async def demo(device:str,request:Request):
    admin(request);require_device(device)
    if os.environ.get('DEMO')!='1':raise HTTPException(404)
    p=await object_body(request)
    if type(p.get('smoke')) is not bool or type(p.get('flame')) is not bool:raise HTTPException(400,'bool required')
    engine.demo_inputs[device]=p
    return {'ok':True}

@app.post('/api/enroll')
async def enroll(request:Request):
    ip=request.client.host if request.client else 'local';key='enroll:'+ip;now=time.monotonic();q=failures[key]
    while q and now-q[0]>60:q.popleft()
    if len(q)>60:raise HTTPException(429,'请求过于频繁')
    q.append(now)
    try:return registry.enroll(await object_body(request))
    except ValueError as e:raise HTTPException(403,str(e))

@app.get('/api/me')
def me(request:Request):
    u=identity(request);return {'name':u['name'],'role':u['role'],'scopes':json.loads(u['scopes'])}

@app.post('/api/terminals/hello')
async def hello(request:Request):
    try:registry.terminal_hello(await object_body(request));return {'ok':True}
    except ValueError as e:raise HTTPException(400,str(e))

@app.get('/api/display')
def display(terminal_id:str=''):return registry.display(terminal_id)

@app.get('/api/manage/{area}')
def manage_get(area:str,request:Request):
    admin(request)
    if area=='devices':return {'devices':registry.list()}
    if area=='users':return {'users':registry.users()}
    if area=='profiles':return registry.profiles()
    if area=='terminals':
        with engine.lock:return {'terminals':[dict(r) for r in engine.db.execute('SELECT * FROM terminals ORDER BY last_seen DESC')]}
    if area=='services':return management.services()
    if area=='backups':return {'backups':management.backup_list()}
    if area=='jobs':
        path=Path('/var/log/roomguard-control/maintenance.jsonl')
        if not path.exists():return {'jobs':[]}
        return {'jobs':[json.loads(x) for x in path.read_text().splitlines()[-30:]]}
    if area=='logs':
        try:return management.helper({'kind':'logs','service':request.query_params.get('service','roomguard')})
        except ValueError as e:raise HTTPException(409,str(e))
    raise HTTPException(404)

@app.post('/api/manage/{area}')
async def manage_post(area:str,request:Request):
    actor=admin(request);p=await object_body(request)
    try:
        if area=='tickets':return registry.ticket(actor)
        if area=='approve':return registry.approve(p.get('id',''),p,actor,management.provision)
        if area=='disable':registry.disable(p.get('id',''),actor,management.revoke);return {'ok':True}
        if area=='reopen':registry.reopen(p.get('id',''),actor);return {'ok':True}
        if area=='users':registry.save_user(p,actor);sessions.clear();return {'ok':True,'relogin':True}
        if area=='profiles':registry.save_profile(p.get('id',''),p.get('config',{}),actor);return {'ok':True}
        if area=='terminals':
            if p.get('profile') not in registry.profiles() or type(p.get('enabled')) is not bool:raise ValueError('方案或启用参数无效')
            with engine.lock:
                engine.db.execute('UPDATE terminals SET profile=?,enabled=?,name=COALESCE(?,name) WHERE id=?',(p['profile'],int(p['enabled']),str(p['name'])[:40] if p.get('name') else None,p.get('id','')));registry.audit('terminal_configured',actor,detail=p)
            return {'ok':True}
        if area=='terminal-delete':
            with engine.lock:engine.db.execute('DELETE FROM terminals WHERE id=?',(p.get('id',''),));registry.audit('terminal_removed',actor,detail={'id':p.get('id','')})
            return {'ok':True}
        if area=='backup':return management.backup(actor)
        if area=='service':
            if p.get('service') not in ['roomguard','mosquitto'] or p.get('action') not in ['start','stop','restart','enable','disable'] or p.get('confirm')!=p['service']:raise ValueError('服务、操作或确认名称无效')
            with engine.lock:registry.audit('service_requested',actor,detail=p)
            return management.helper({'kind':'service','service':p['service'],'action':p['action']})
        if area=='restore':
            if p.get('confirm')!='RESTORE' or p.get('file') not in [b['file'] for b in management.backup_list()]:raise ValueError('恢复文件或确认词无效')
            management.backup(actor)
            with engine.lock:registry.audit('restore_requested',actor,detail={'file':p['file']})
            return management.helper({'kind':'restore','file':p['file']})
        raise HTTPException(404)
    except ValueError as e:raise HTTPException(409,str(e))

@app.get('/teacher')
def teacher_page():return FileResponse(Path(__file__).parent/'static'/'teacher.html')

app.mount('/static',StaticFiles(directory=Path(__file__).parent/'static'),name='static')
@app.get('/')
def index():return FileResponse(Path(__file__).parent/'static'/'index.html')
