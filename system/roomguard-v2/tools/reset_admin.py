#!/usr/bin/env python3
import getpass,json,sqlite3,subprocess,time
from pathlib import Path
from server.core import password_hash
r=subprocess.run(['systemctl','is-active','roomguard'],capture_output=True,text=True)
if r.stdout.strip()=='active':raise SystemExit('请先 sudo systemctl stop roomguard，再运行此工具。')
p=Path('/var/lib/roomguard/monitor.db')
if not p.exists():raise SystemExit('数据库不存在，未进行修改。')
pw=getpass.getpass('新管理员密码（至少12位）: ')
if len(pw)<12 or len(pw)>128:raise SystemExit('长度需12—128位')
if pw!=getpass.getpass('再输入一次: '):raise SystemExit('两次不一致，未修改')
backup=p.with_name('monitor-before-password-reset-'+str(int(time.time()))+'.db')
with sqlite3.connect(p) as src,sqlite3.connect(backup) as dst:src.backup(dst)
backup.chmod(0o600)
with sqlite3.connect(p) as c:
 encoded=password_hash(pw)
 c.execute('UPDATE settings SET value=? WHERE key=?',(json.dumps(encoded),'admin_hash'))
 if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'").fetchone():c.execute("UPDATE users SET hash=? WHERE name='admin'",(encoded,))
 c.execute('INSERT INTO events(ts,device,kind,event_id,actor,detail) VALUES(?,?,?,?,?,?)',(time.time(),'','password_reset','','local-maintainer','{}'))
print('密码已重置；一致性备份已保留。请 sudo systemctl start roomguard。')
