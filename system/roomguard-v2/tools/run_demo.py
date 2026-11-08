"""Explicit multi-node demo. Never controls production services/accounts."""
import os,time,threading,uuid,math
os.environ.setdefault('ADMIN_PASSWORD','DemoOnly-123456');os.environ.setdefault('DATA_DIR','./demo-data-v2');os.environ['DISABLE_MQTT']='1';os.environ['DEMO']='1';os.environ['BOOTSTRAP_LEGACY_NODES']='0'
from server.app import engine,registry
engine.time_trusted=True;engine.demo_inputs={};states={};started=time.monotonic()
for room,model in [('101','ESP32'),('102','ESP8266'),('103','ESP32')]:
 device='rg-'+model.lower()+'-demo'+room;ticket=registry.ticket('demo');registry.enroll({'id':device,'code':ticket['code'],'model':model,'firmware':'2.0','capabilities':['dht11','mq2','flame','buzzer','rgb']});registry.approve(device,{'room':room,'floor':'1F' if room!='103' else '2F'},'demo',lambda *a:None)
 engine.demo_inputs[device]={'smoke':False,'flame':False}
 states[device]={'boot':uuid.uuid4().hex[:10],'seq':0,'event_id':'','active':False,'muted':False,'reasons':[],'smoke':False,'flame':False,'dht_ok':True,'mq_ready':True,'temperature':24,'humidity':55,'mq_raw':120,'mq_voltage':.5,'config_version':0,'model':model,'firmware':'2.0','control_nonce':'demo-nonce'}
def publish(d,p):
 if d not in states:return False
 s=states[d]
 if p['kind']=='silence':s['muted']=True
 else:
  s['config_version']=p['version'];s['config_epoch']=p.get('epoch','')
  for key,default in [('clear_seconds',10),('report_seconds',5),('hardware_profile',0)]:s[key]=p.get(key,default)
 engine.ack(d,{'id':p['id'],'status':'applied'});return True
engine.publisher=publish;engine.broker_online=True
def loop():
 while True:
  for i,(d,s) in enumerate(list(states.items())):
   if d not in engine.devices:continue
   old=s['reasons'];p=engine.demo_inputs[d];reasons=[k for k in ['smoke','flame'] if p[k]]
   if reasons and not s['active']:s['event_id']=uuid.uuid4().hex;s['active']=True;s['muted']=False
   if any(k not in old for k in reasons):s['muted']=False
   if s['active'] and not reasons:
    s.setdefault('_clear',time.monotonic())
    if time.monotonic()-s['_clear']>=engine.setting('config:'+d)['clear_seconds']:s['active']=False;s['muted']=False
   else:s.pop('_clear',None)
   phase=(time.monotonic()-started)/18+i;s.update(p);s['reasons']=reasons;s['seq']+=1;s['temperature']=round(24+i+math.sin(phase),1);s['humidity']=round(55+2*math.cos(phase),1);s['mq_raw']=int((1800 if p['smoke'] else 120)+15*math.sin(phase));engine.ingest(d,{k:v for k,v in s.items() if not k.startswith('_')})
  time.sleep(1)
threading.Thread(target=loop,daemon=True).start()
if __name__=='__main__':
 import uvicorn
 uvicorn.run('server.app:app',host='127.0.0.1',port=8080)
