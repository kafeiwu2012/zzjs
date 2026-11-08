import os
os.environ["BOOTSTRAP_LEGACY_NODES"]="1"
import json
import pytest
from server.core import Engine
D='room101-esp32'
class Clock:
 def __init__(self):self.t=0;self.w=1800000000
 def mono(self):return self.t
 def wall(self):return self.w
 def advance(self,s):self.t+=s;self.w+=s
@pytest.fixture
def setup(tmp_path):
 c=Clock();e=Engine(tmp_path/'db', 'TestPassword123!',c.mono,c.wall);return e,c

def state(seq=1,**kw):
 p=dict(boot='b1',seq=seq,event_id='',active=False,muted=False,reasons=[],smoke=False,flame=False,dht_ok=True,mq_ready=True,temperature=25,humidity=60,mq_raw=120,mq_voltage=.5,config_version=1,control_nonce='nonce')
 p.update(kw);return p

def test_online_duplicate_offline_monotonic(setup):
 e,c=setup;assert e.ingest(D,state());c.advance(19);assert not e.ingest(D,state());assert e.snapshot()['nodes'][0]['online'];c.w-=36000;c.t+=1;assert not e.snapshot()['nodes'][0]['online'];assert e.ingest(D,state(2));assert e.snapshot()['nodes'][0]['online']

def test_dht_null_and_bad_message_not_heartbeat(setup):
 e,c=setup;e.ingest(D,state(dht_ok=False,temperature=0,humidity=0));assert e.snapshot()['nodes'][0]['state']['temperature'] is None
 with pytest.raises(ValueError):e.ingest(D,state(2,active='yes'))
 c.advance(20);assert not e.snapshot()['nodes'][0]['online']

def test_independent_reasons_confirm_and_recovery(setup):
 e,c=setup;e.ingest(D,state(active=True,event_id='alarm1',reasons=['smoke'],smoke=True));e.confirm(D,'alarm1','admin');e.confirm(D,'alarm1','admin');e.ingest(D,state(2,active=True,event_id='alarm1',reasons=['smoke','flame'],smoke=True,flame=True));e.ingest(D,state(3,event_id='alarm1'))
 kinds=[r['kind'] for r in e.history('events')];assert kinds.count('confirmed')==1;assert 'reasons' in kinds and 'recovered' in kinds

def test_silence_needs_online_and_ack_no_replay(setup):
 e,c=setup;e.ingest(D,state(active=True,event_id='a',reasons=['flame'],flame=True))
 with pytest.raises(ValueError):e.command(D,'silence','admin','a')
 e.broker_online=True;sent=[];e.publisher=lambda d,p:sent.append(p) or True
 r=e.command(D,'silence','admin','a');assert r['status']=='sent';assert sent[-1]['nonce']=='nonce';e.ack(D,{'id':r['id'],'status':'applied'});assert e.history('commands')[0]['status']=='applied'
 c.advance(20);e.tick()
 with pytest.raises(ValueError):e.command(D,'silence','admin','a')
 n=len(sent);e.ingest(D,state(2,active=True,event_id='a',reasons=['flame'],flame=True));assert len(sent)==n

def test_pending_config_state_confirms(setup):
 e,c=setup;r=e.command(D,'config','admin',clear_seconds=22);assert r['status']=='pending';assert e.setting('config:'+D)['version']==2
 e.ingest(D,state(config_version=2));assert e.history('commands')[0]['status']=='applied'
 with pytest.raises(ValueError):e.command(D,'config','admin',clear_seconds=0)

def test_restart_offline_and_old_boot_rejected(setup,tmp_path):
 e,c=setup;e.ingest(D,state());e.ingest(D,state(1,boot='b2'));assert not e.ingest(D,state(2,boot='b1'));assert not e.ingest(D,state(1,boot='b2'))
 e2=Engine(tmp_path/'db','ignored',c.mono,c.wall);assert not e2.snapshot()['nodes'][0]['online']

def test_retention_and_csv(setup):
 e,c=setup;e.ingest(D,state(dht_ok=False));data=e.export('samples',D,0,c.w+1);assert 'temperature_C' in data and '\ufeff' in data
 c.advance(31*86400);e.cleanup();assert not e.history('samples');assert e.history('events')

def test_command_timeout_survives_wall_jump(setup):
 e,c=setup;e.ingest(D,state(active=True,event_id='a',reasons=['smoke'],smoke=True));e.broker_online=True;e.publisher=lambda *a:True;r=e.command(D,'silence','admin','a');c.w-=100000;c.t+=11;e.tick();assert e.history('commands',end=1900000000)[0]['status']=='unconfirmed'

def test_trend_full_window_and_config_after_restore(setup):
 e,c=setup
 for i in range(4):e.ingest(D,state(i+1,temperature=20+i));c.advance(3600)
 rows=e.trend(D,c.w-5*3600,c.w)['rows'];assert len(rows)==4
 e.ingest(D,state(5,config_version=100));e.command(D,'config','admin',clear_seconds=12);assert e.setting('config:'+D)['version']==101
