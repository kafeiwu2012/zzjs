#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ "$(id -u)" -eq 0 ] || { echo '请运行 sudo bash deploy/update.sh';exit 1; }
[ -f /etc/roomguard/server.env ] || { echo '未检测到已安装实例，请使用install.sh。';exit 1; }
release_stamp=$(date +%Y%m%d-%H%M%S)
backup_dir="/var/lib/roomguard/backups/$release_stamp"
install -d -m 700 -o roomguard -g roomguard /var/lib/roomguard/backups
install -d -m 700 "$backup_dir"
python3 tools/backup.py /var/lib/roomguard/monitor.db "$backup_dir/monitor.db"
cp -r /opt/roomguard/server "$backup_dir/server"
systemctl stop roomguard
cp -r server /opt/roomguard/
# Source ZIP permissions must not prevent the unprivileged service reading code.
chown -R root:roomguard /opt/roomguard/server
find /opt/roomguard/server -type d -exec chmod 750 {} +
find /opt/roomguard/server -type f -exec chmod 640 {} +
install -d -m 755 /opt/roomguard/tools
install -m 644 tools/backup.py tools/doctor.py tools/reset_admin.py tools/__init__.py /opt/roomguard/tools/
if ! /opt/roomguard/venv/bin/pip install -r server/requirements.txt;then
 echo "依赖安装失败，保留备份于 $backup_dir；请按维护手册恢复。";exit 1
fi
install -d -m 755 -o root -g root /run/roomguard-control
install -d -m 700 -o root -g root /var/lib/roomguard-control
install -d -m 750 -o root -g roomguard /var/log/roomguard-control
printf '%s\n' 'd /run/roomguard-control 0755 root root -' > /etc/tmpfiles.d/roomguard-control.conf
install -m 755 deploy/system_control.py /usr/local/sbin/roomguard-control
printf '%s\n' 'roomguard ALL=(root) NOPASSWD: /usr/local/sbin/roomguard-control ""' > /etc/sudoers.d/roomguard-control
chmod 440 /etc/sudoers.d/roomguard-control
visudo -cf /etc/sudoers.d/roomguard-control
install -m 644 deploy/mosquitto.acl /etc/mosquitto/roomguard.acl
if ! grep -q '^ENABLE_SYSTEM_MANAGEMENT=' /etc/roomguard/server.env;then echo ENABLE_SYSTEM_MANAGEMENT=1 >> /etc/roomguard/server.env;fi
systemctl reload mosquitto
install -m 644 deploy/roomguard.service /etc/systemd/system/roomguard.service
systemctl daemon-reload
systemctl start roomguard
ready=0
for attempt in $(seq 1 30);do
 if curl --fail --silent http://127.0.0.1:8080/api/status >/dev/null;then ready=1;break;fi
 sleep 1
done
if [ "$ready" -ne 1 ];then echo "更新后服务未就绪，检查日志，备份目录：$backup_dir";exit 1;fi
echo "更新完成。数据库与旧代码备份：$backup_dir"
echo '客户端刷新网页；APK和EXE指向原服务器即可使用新界面。'
