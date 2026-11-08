#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "$(id -u)" -ne 0 ]; then echo '请在树莓派上运行 sudo bash deploy/install.sh';exit 1;fi
if [ ! -f /etc/os-release ];then exit 1;fi
if [ -e /etc/roomguard/server.env ];then echo '检测到已有部署。为保护账号与数据，不覆盖。更新代码请参阅开发手册。';exit 1;fi
read -r -s -p '首次管理员密码（至少12位，不会显示）：' admin_password;echo
if [ "${#admin_password}" -lt 12 ];then echo '密码太短';exit 1;fi
# Restrict environment-file characters so installation does not corrupt quoting.
if [[ ! "$admin_password" =~ ^[A-Za-z0-9_@.%+:,=/!-]+$ ]];then echo '请使用字母、数字及 _@.%+:,=/!- 符号';exit 1;fi
apt-get update
apt-get install -y python3-venv python3-pip mosquitto mosquitto-clients sudo curl unzip sqlite3 avahi-daemon
id roomguard >/dev/null 2>&1 || useradd --system --home /var/lib/roomguard --shell /usr/sbin/nologin roomguard
install -d -m 755 /opt/roomguard
install -d -m 750 -o root -g roomguard /etc/roomguard
install -d -m 700 -o roomguard -g roomguard /var/lib/roomguard
cp -r server /opt/roomguard/
# Source ZIP permissions must not prevent the unprivileged service reading code.
chown -R root:roomguard /opt/roomguard/server
find /opt/roomguard/server -type d -exec chmod 750 {} +
find /opt/roomguard/server -type f -exec chmod 640 {} +
install -d -m 755 /opt/roomguard/tools
install -m 644 tools/backup.py tools/doctor.py tools/reset_admin.py tools/__init__.py /opt/roomguard/tools/
python3 -m venv /opt/roomguard/venv
/opt/roomguard/venv/bin/pip install -r server/requirements.txt
server_password=$(python3 -c 'import secrets;print(secrets.token_hex(24))')
umask 077
cat > /etc/roomguard/server.env <<EOF
ADMIN_PASSWORD=$admin_password
DATA_DIR=/var/lib/roomguard
MQTT_HOST=127.0.0.1
MQTT_PORT=1883
MQTT_USER=server
MQTT_PASSWORD=$server_password
ENABLE_CLOCK_SET=1
ENABLE_SYSTEM_MANAGEMENT=1
EOF
chown root:roomguard /etc/roomguard/server.env
chmod 640 /etc/roomguard/server.env
printf '%s\n%s\n' "$server_password" "$server_password" | mosquitto_passwd -c /etc/mosquitto/roomguard.passwd server
chown root:mosquitto /etc/mosquitto/roomguard.passwd
chmod 640 /etc/mosquitto/roomguard.passwd
install -m 644 deploy/mosquitto.acl /etc/mosquitto/roomguard.acl
install -m 644 deploy/mosquitto-roomguard.conf /etc/mosquitto/conf.d/roomguard.conf
install -d -m 755 -o root -g root /run/roomguard-control
install -d -m 700 -o root -g root /var/lib/roomguard-control
install -d -m 750 -o root -g roomguard /var/log/roomguard-control
printf '%s\n' 'd /run/roomguard-control 0755 root root -' > /etc/tmpfiles.d/roomguard-control.conf
install -m 755 deploy/system_control.py /usr/local/sbin/roomguard-control
printf '%s\n' 'roomguard ALL=(root) NOPASSWD: /usr/local/sbin/roomguard-control ""' > /etc/sudoers.d/roomguard-control
chmod 440 /etc/sudoers.d/roomguard-control
visudo -cf /etc/sudoers.d/roomguard-control
install -m 755 deploy/set-time.py /usr/local/sbin/roomguard-set-time
printf '%s\n' 'roomguard ALL=(root) NOPASSWD: /usr/local/sbin/roomguard-set-time *' > /etc/sudoers.d/roomguard-time
chmod 440 /etc/sudoers.d/roomguard-time
visudo -cf /etc/sudoers.d/roomguard-time
install -m 644 deploy/roomguard.service /etc/systemd/system/roomguard.service
systemctl daemon-reload
systemctl enable --now mosquitto
systemctl restart mosquitto
systemctl enable --now roomguard
# Verify HTTP readiness before reporting success or removing the setup password.
ready=0
for attempt in $(seq 1 45);do
 if curl --fail --silent http://127.0.0.1:8080/api/status >/dev/null;then ready=1;break;fi
 sleep 1
done
if [ "$ready" -ne 1 ];then
 echo '服务未就绪，不宣称安装成功。请执行 sudo journalctl -u roomguard -n 80 --no-pager';exit 1
fi
sed -i '/^ADMIN_PASSWORD=/d' /etc/roomguard/server.env
echo '安装完成。访问 http://树莓派IP:8080 ，账号 admin。在 /teacher 教师后台生成接入码并批准新节点。'
echo '如有防火墙，仅向比赛局域网开放TCP 8080和1883，不要配置公网端口映射。'
