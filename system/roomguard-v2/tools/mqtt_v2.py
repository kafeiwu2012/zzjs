"""Real local broker; enroll/account helper is simulated and test driver installs credentials."""
import json,os,subprocess,sys,tempfile,time,pathlib,signal,threading
import httpx,paho.mqtt.client as mqtt
R=pathlib.Path(__file__).resolve().parents[1]
def wait(fn,seconds=10):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  try:
   r=fn()
   if r:return r
  except (httpx.HTTPError,KeyError,IndexError):pass
  time.sleep(.15)
 raise AssertionError('timeout')
with tempfile.TemporaryDirectory(prefix='rg-v2-mqtt-') as tmp:
 t=pathlib.Path(tmp);pw=t/'passwords';accounts={'server':'TemporaryServerTestOnly'}
 def credentials():pw.write_text(''.join(k+':'+v+'\n' for k,v in accounts.items()));pw.chmod(0o600)
 credentials();acl=t/'acl';acl.write_text((R/'deploy/mosquitto.acl').read_text());cfg=t/'mosquitto.conf';cfg.write_text(f'listener 18885 127.0.0.1\nallow_anonymous false\npassword_file {pw}\nacl_file {acl}\n')
 bl=open(t/'broker.log','w');sl=open(t/'server.log','w');broker=subprocess.Popen([os.environ.get('MOSQUITTO_BIN','mosquitto'),'-c',str(cfg)],stdout=bl,stderr=bl)
 env={**os.environ,'DATA_DIR':str(t/'data'),'ADMIN_PASSWORD':'TeacherMqttPassword123!','MQTT_HOST':'127.0.0.1','MQTT_PORT':'18885','MQTT_USER':'server','MQTT_PASSWORD':accounts['server'],'TEST_HELPER':'1','DISABLE_MQTT':'0','DEMO':'0','BOOTSTRAP_LEGACY_NODES':'0'}
 server=subprocess.Popen([sys.executable,'-m','uvicorn','server.app:app','--host','127.0.0.1','--port','8891'],cwd=R,env=env,stdout=sl,stderr=sl);clients={};states={};done=threading.Event()
 try:
  h=httpx.Client(base_url='http://127.0.0.1:8891',timeout=5);wait(lambda:h.get('/api/status').json()['broker_online']);token=h.post('/api/login',json={'username':'admin','password':'TeacherMqttPassword123!'}).json()['token'];h.headers['Authorization']='Bearer '+token
  assert h.get('/api/status').json()['nodes']==[]
  def add(i):
   device='rg-esp32-integration'+str(i);code=h.post('/api/manage/tickets',json={}).json()['code'];assert h.post('/api/enroll',json={'id':device,'code':code,'model':'ESP32','firmware':'2.0'}).json()['status']=='pending';assert h.post('/api/manage/approve',json={'id':device,'room':str(100+i)}).status_code==200
   accounts[device]=h.post('/api/enroll',json={'id':device,'code':code}).json()['mqtt_password'];credentials();broker.send_signal(signal.SIGHUP);time.sleep(.15)
   states[device]={'boot':'integrationboot','seq':0,'event_id':'alarm-'+device,'active':True,'muted':False,'reasons':['flame'],'smoke':False,'flame':True,'dht_ok':True,'mq_ready':True,'temperature':25,'humidity':55,'mq_raw':120,'mq_voltage':.5,'config_version':1,'control_nonce':'test-nonce','report_seconds':5}
   c=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id=device);c.username_pw_set(device,accounts[device])
   def on_connect(c,u,f,rc,props,d=device):c.subscribe('building/'+d+'/command',1)
   def message(c,u,msg,d=device):
    p=json.loads(msg.payload)
    if p['kind']=='silence':states[d]['muted']=True
    else:
     states[d]['config_version']=p['version'];states[d]['config_epoch']=p.get('epoch','')
     for key,default in [('clear_seconds',10),('report_seconds',5),('hardware_profile',0)]:states[d][key]=p.get(key,default)
    c.publish('building/'+d+'/ack',json.dumps({'id':p['id'],'status':'applied'}),1)
   c.on_connect=on_connect;c.on_message=message;c.connect('127.0.0.1',18885,15);c.loop_start();clients[device]=c;return device
  def heartbeat():
   while not done.is_set():
    for d,c in list(clients.items()):
     if c.is_connected():states[d]['seq']+=1;c.publish('building/'+d+'/state',json.dumps(states[d]),1)
    done.wait(1)
  a=add(1);b=add(2);thread=threading.Thread(target=heartbeat,daemon=True);thread.start();wait(lambda:len(h.get('/api/status').json()['nodes'])==2 and all(n['online'] for n in h.get('/api/status').json()['nodes']))
  third=add(3);wait(lambda:len(h.get('/api/status').json()['nodes'])==3 and all(n['online'] for n in h.get('/api/status').json()['nodes']))
  forged=dict(states[a],seq=99999,temperature=66);clients[third].publish('building/'+a+'/state',json.dumps(forged),1);time.sleep(.5);assert h.get('/api/status').json()['nodes'][0]['state']['temperature']==25
  assert h.post('/api/nodes/'+a+'/silence',json={'event_id':states[a]['event_id']}).status_code==200;wait(lambda:h.get('/api/status').json()['nodes'][0]['state']['muted']);assert not states[b]['muted'] and not states[third]['muted']
  offline=clients.pop(a);offline.disconnect();offline.loop_stop();wait(lambda:not h.get('/api/status').json()['nodes'][0]['online'],seconds=25)
  assert h.get('/api/status').json()['nodes'][0]['state']['active'];assert h.post('/api/nodes/'+a+'/silence',json={'event_id':states[a]['event_id']}).status_code==409
  report={'real_broker':'Mosquitto2.0.20 local test','start_zero_nodes':True,'HTTP_enroll_pending_approve':True,'third_node_join_without_server_restart':True,'MQTT_ACL_isolation':True,'independent_silence_ack':True,'offline20s_and_alarm_preserved':True,'broker_account_install':'test_driver_not_Pi_root_helper','physical_devices':False}
  (R/'artifacts/MQTT_V2集成测试.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
 finally:
  done.set()
  for c in clients.values():c.disconnect();c.loop_stop()
  server.terminate();broker.terminate();server.wait(timeout=5);broker.wait(timeout=5);sl.close();bl.close()
