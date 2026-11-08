import os,tempfile
os.environ['DATA_DIR']=tempfile.mkdtemp(prefix='rg-api-')
os.environ['ADMIN_PASSWORD']='ApiTestPassword123!'
os.environ['DISABLE_MQTT']='1'
os.environ['BOOTSTRAP_LEGACY_NODES']='1'
from fastapi.testclient import TestClient
from server.app import app,engine
from test_engine import state,D

def test_auth_api_and_csv():
 with TestClient(app) as c:
  assert c.get('/api/status').status_code==200
  assert c.get('/api/history').status_code==401
  assert c.post('/api/nodes/'+D+'/silence',json={}).status_code==401
  assert c.post('/api/login',json={'username':'admin','password':'wrong'}).status_code==401
  p=c.post('/api/login',json={'username':'admin','password':'ApiTestPassword123!'});assert p.status_code==200
  h={'Authorization':'Bearer '+p.json()['token']}
  engine.ingest(D,state(active=True,event_id='a',reasons=['smoke'],smoke=True))
  assert c.post('/api/nodes/'+D+'/confirm',json={'event_id':'a'},headers=h).status_code==200
  assert c.post('/api/nodes/'+D+'/silence',json={'event_id':'a'},headers=h).status_code==409
  assert c.post('/api/nodes/'+D+'/config',json={'clear_seconds':0},headers=h).status_code==409
  assert c.post('/api/nodes/'+D+'/config',json={'clear_seconds':15},headers=h).status_code==200
  assert 'temperature_C' in c.get('/api/export?kind=samples',headers=h).text
  assert c.post('/api/time',json={'epoch':1800000000},headers=h).status_code==409
  assert c.post('/api/settings',json={'samples':30,'events':180},headers=h).status_code==200
  assert c.post('/api/password',json={'old':'ApiTestPassword123!','new':'ChangedPassword123!'},headers=h).status_code==200
  assert c.get('/api/history',headers=h).status_code==401
