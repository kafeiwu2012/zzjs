#!/usr/bin/env python3
"""Read-only diagnostics; never prints EnvironmentFile contents or passwords."""
import argparse,json,shutil,subprocess,urllib.request,sqlite3,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8080');p.add_argument('--db',help='可选只读检查数据库');a=p.parse_args();issues=[]
def command(args):
 try:return subprocess.run(args,capture_output=True,text=True,timeout=6).stdout.strip()
 except (OSError,subprocess.SubprocessError):return 'unavailable'
for unit in ['roomguard','mosquitto']:
 state=command(['systemctl','is-active',unit]);print(unit+':',state)
 if state!='active':issues.append(unit+'服务未运行')
disk=shutil.disk_usage('/var/lib/roomguard' if Path('/var/lib/roomguard').exists() else '.')
print('磁盘可用MB:',disk.free//1048576)
if disk.free<200*1048576:issues.append('磁盘剩余不足200MB')
print('NTP同步:',command(['timedatectl','show','-p','NTPSynchronized','--value']))
try:
 with urllib.request.urlopen(a.url.rstrip('/')+'/api/status',timeout=5) as r:s=json.load(r)
 print('Web/API: OK; MQTT:',s['broker_online'],'时间已校准:',s['time_trusted'])
 if not s['broker_online']:issues.append('消息代理未连接')
 if not s['time_trusted']:issues.append('本次运行时间尚未确认校准')
 for n in s['nodes']:
  st=n['state'];print(n['room'],'online=',n['online'],'alarm=',st.get('active'),'DHT=',st.get('dht_ok'),'MQready=',st.get('mq_ready'),'config_synced=',n['config_synced'])
  if not n['online']:issues.append(n['room']+'节点离线')
  elif not st.get('dht_ok'):issues.append(n['room']+'温湿度采集故障')
  if n['online'] and not st.get('mq_ready'):issues.append(n['room']+'MQ预热未完成')
  if st.get('active'):issues.append(n['room']+'存在或最后已知环境告警')
  if not n['config_synced']:issues.append(n['room']+'参数待同步')
 if s.get('demo'):issues.append('当前运行的是模拟演示模式')
except Exception as e:issues.append('Web/API无法访问: '+type(e).__name__)
if a.db:
 try:
  path=Path(a.db).resolve();c=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True);result=c.execute('PRAGMA quick_check').fetchone()[0];c.close();print('数据库quick_check:',result)
  if result!='ok':issues.append('数据库一致性检查异常')
 except Exception as e:issues.append('数据库不可读: '+type(e).__name__)
print('检查结论:', '；'.join(issues) if issues else '未发现上述检查范围内的问题')
print('此工具不验证实际电压、传感器物理响应或手机锁屏保活。')
sys.exit(1 if issues else 0)
