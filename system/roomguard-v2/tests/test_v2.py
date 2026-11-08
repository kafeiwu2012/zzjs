import os,importlib,json
import pytest
from fastapi.testclient import TestClient
from server.core import Engine
from server.registry import Registry
from test_engine import state
@pytest.fixture
def client(tmp_path,monkeypatch):
 monkeypatch.setenv('DATA_DIR',str(tmp_path));monkeypatch.setenv('ADMIN_PASSWORD','TeacherPassword123!');monkeypatch.setenv('DISABLE_MQTT','1');monkeypatch.setenv('TEST_HELPER','1');monkeypatch.setenv('BOOTSTRAP_LEGACY_NODES','0')
 import server.app as mod
 mod=importlib.reload(mod)
 with TestClient(mod.app) as c:yield c,mod

def login(c,user='admin',password='TeacherPassword123!'):
 r=c.post('/api/login',json={'username':user,'password':password});assert r.status_code==200,r.text;return {'Authorization':'Bearer '+r.json()['token']}
def join(c,h,device,room):
 code=c.post('/api/manage/tickets',json={},headers=h).json()['code'];r=c.post('/api/enroll',json={'id':device,'code':code,'model':'ESP32','firmware':'2.0'});assert r.json()['status']=='pending'
 r=c.post('/api/manage/approve',json={'id':device,'room':room,'floor':'1F'},headers=h);assert r.status_code==200,r.text
 r=c.post('/api/enroll',json={'id':device,'code':code});assert r.json()['status']=='approved';assert len(r.json()['mqtt_password'])>=24
 return code

def test_zero_fixed_nodes_and_dynamic_three(client):
 c,m=client;h=login(c);assert c.get('/api/status').json()['nodes']==[]
 for i in range(3):
  d='rg-esp32-test'+str(i);join(c,h,d,str(101+i));m.engine.ingest(d,state(model='ESP32'))
 assert len(c.get('/api/status').json()['nodes'])==3
 assert len(c.get('/api/manage/devices',headers=h).json()['devices'])==3

def test_join_security_and_disable(client):
 c,m=client;h=login(c);d='rg-esp32-owner';code=join(c,h,d,'101')
 assert c.post('/api/enroll',json={'id':'rg-esp32-attacker','code':code}).status_code==403
 assert c.post('/api/enroll',json={'id':'server','code':code}).status_code==403
 assert c.post('/api/manage/disable',json={'id':d},headers=h).status_code==200
 assert c.post('/api/enroll',json={'id':d,'code':code}).status_code==403
 with pytest.raises(ValueError):m.engine.ingest(d,state())

def test_student_scope_and_teacher_operations(client):
 c,m=client;h=login(c);a='rg-esp32-a';b='rg-esp32-b';join(c,h,a,'101');join(c,h,b,'102')
 m.engine.ingest(a,state(active=True,event_id='event1',reasons=['flame'],flame=True));m.engine.ingest(b,state())
 r=c.post('/api/manage/users',json={'name':'student','password':'StudentPassword123!','role':'operator','scopes':[a]},headers=h);assert r.status_code==200
 sh=login(c,'student','StudentPassword123!')
 assert c.get('/api/manage/services',headers=sh).status_code==403
 assert c.post('/api/nodes/'+a+'/confirm',json={'event_id':'event1'},headers=sh).status_code==200
 assert c.post('/api/nodes/'+b+'/confirm',json={'event_id':'event1'},headers=sh).status_code==403
 assert c.post('/api/nodes/'+a+'/config',json={'clear_seconds':12},headers=sh).status_code==403
 assert c.get('/api/history?device='+b,headers=sh).status_code==403
 assert len(c.get('/api/status',headers=sh).json()['nodes'])==1

def test_display_profiles_and_terminal_discovery(client):
 c,m=client;h=login(c);t='web-test-terminal';assert c.post('/api/terminals/hello',json={'id':t,'name':'测试大屏','kind':'screen'}).status_code==200
 r=c.post('/api/manage/profiles',json={'id':'campus','config':{'title':'校园监测','theme':'dark','page_size':2,'rotation_seconds':5,'font_scale':1.2}},headers=h);assert r.status_code==200,r.text
 assert c.post('/api/manage/terminals',json={'id':t,'profile':'campus','enabled':True},headers=h).status_code==200
 p=c.get('/api/display?terminal_id='+t).json();assert p['config']['page_size']==2 and p['config']['theme']=='dark'
 assert c.post('/api/manage/profiles',json={'id':'bad','config':{'page_size':0}},headers=h).status_code==409

def test_backup_and_service_allowlist(client):
 c,m=client;h=login(c);r=c.post('/api/manage/backup',json={},headers=h);assert r.status_code==200
 name=r.json()['file'];assert name in [b['file'] for b in c.get('/api/manage/backups',headers=h).json()['backups']]
 assert c.post('/api/manage/restore',json={'file':'../../etc/passwd','confirm':'RESTORE'},headers=h).status_code==409
 assert c.post('/api/manage/service',json={'service':'ssh','action':'stop','confirm':'ssh'},headers=h).status_code==409
 r=c.post('/api/manage/service',json={'service':'mosquitto','action':'restart','confirm':'mosquitto'},headers=h);assert r.status_code==200 and r.json()['simulation']

def test_rename_keeps_sample_location(client):
 c,m=client;h=login(c);d='rg-esp32-move';join(c,h,d,'101');m.engine.ingest(d,state())
 assert c.post('/api/manage/approve',json={'id':d,'room':'201'},headers=h).status_code==200
 csv=c.get('/api/export?kind=samples&device='+d,headers=h).text;assert ',101,' in csv

def test_heartbeat_uses_applied_interval(client):
 c,m=client;h=login(c);d='rg-esp32-slow';join(c,h,d,'101')
 m.engine.ingest(d,state(report_seconds=60))
 m.engine.live[d]=m.engine.clock()-30
 assert c.get('/api/status').json()['nodes'][0]['online']
 m.engine.live[d]=m.engine.clock()-241
 assert not c.get('/api/status').json()['nodes'][0]['online']

def test_deployment_epoch_prevents_false_config_success(client):
 c,m=client;h=login(c);d='rg-esp32-epoch';join(c,h,d,'101');cfg=m.engine.setting('config:'+d)
 assert cfg['epoch']
 m.engine.ingest(d,state(firmware='2.0',clear_seconds=10,report_seconds=5,hardware_profile=0,config_epoch='other-server'))
 assert not c.get('/api/status').json()['nodes'][0]['config_synced']
 m.engine.ingest(d,state(2,firmware='2.0',clear_seconds=10,report_seconds=5,hardware_profile=0,config_epoch=cfg['epoch']))
 assert c.get('/api/status').json()['nodes'][0]['config_synced']

def test_join_ticket_expires(client):
 c,m=client;h=login(c);code=c.post('/api/manage/tickets',json={},headers=h).json()['code']
 with m.engine.lock:m.engine.db.execute('UPDATE joins SET expires=0');m.engine.db.commit()
 assert c.post('/api/enroll',json={'id':'rg-esp32-expired','code':code}).status_code==403
