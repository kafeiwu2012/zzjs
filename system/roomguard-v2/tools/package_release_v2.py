"""RoomGuard V2 release builder. Excludes runtime data, private keys and obsolete flows."""
from pathlib import Path
import hashlib,json,shutil,zipfile,stat
R=Path(__file__).resolve().parents[1];O=R.parent/'deliverables';O.mkdir(exist_ok=True)
blocked_dirs={'.venv','.pio','.platformio','__pycache__','.pytest_cache','.git','.github','.gradle','build','data','demo-data','demo-data-v2','node_modules','archive_v1.0','archive_v1.1'}
blocked_suffix={'.jks','.keystore','.p12','.pfx','.pem','.key','.pyc','.pdb','.idsig','.elf','.map','.db','.sqlite','.sqlite3','.kicad_prl'}
selected_tools={'__init__.py','backup.py','doctor.py','reset_admin.py','run_demo.py','mqtt_v2.py','browser_v2.py','build_baseboard.py','build_baseboard_pcb.py','draw_baseboard_overview.py','draw_circuits.py','export_docs_v2.py','validate_presentation_v2.py','package_release_v2.py'}
root_files={'README.md','THIRD_PARTY.md','pytest.ini','requirements-dev.txt'}
def allowed(p):
 rel=p.relative_to(R);parts=rel.parts;low=p.name.lower()
 if p.is_symlink() or any(x in blocked_dirs for x in parts) or p.suffix.lower() in blocked_suffix:return False
 if low in {'secrets.h','secrets.example.h','server.env','.env','.ds_store'} or low.startswith('.env') or p.name.startswith('SHA256SUMS_'):return False
 top=parts[0]
 if len(parts)==1:return p.name in root_files
 if top in {'server','deploy','clients','tests','hardware'}:return True
 if top=='firmware':return rel.as_posix()=='firmware/include/alarm.h'
 if top=='arduino':return parts[1] in {'RoomGuard_ESP32','RoomGuard_ESP8266','libraries'}
 if top=='tools':return len(parts)==2 and p.name in selected_tools
 if top=='docs':return len(parts)==2 and ('_V2.' in p.name or p.name.startswith('通用基板设计说明_V1.1') or p.name=='电平转换参考.svg')
 if top=='presentation':return len(parts)==2 and p.suffix in {'.py','.json','.png','.pdf','.pptx','.txt'}
 if top=='artifacts':return len(parts)==2 or (len(parts)==3 and parts[1] in {'esp32','esp8266'} and p.suffix=='.bin')
 return False
files=sorted(p for p in R.rglob('*') if p.is_file() and allowed(p))
checks=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(R).as_posix()+'\n' for p in files)
manifest=R/'artifacts/SHA256SUMS_V2.txt';manifest.write_text(checks)
def add(z,p,name):
 info=zipfile.ZipInfo(name);t=__import__('time').localtime(p.stat().st_mtime);info.date_time=t[:6];info.compress_type=zipfile.ZIP_DEFLATED
 mode=0o755 if p.suffix in {'.sh','.exe'} else 0o644;info.external_attr=(stat.S_IFREG|mode)<<16;z.writestr(info,p.read_bytes(),compresslevel=8)
def archive(path,items):
 with zipfile.ZipFile(path,'w') as z:
  for p,name in items:add(z,p,name)
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None
  for n in z.namelist():
   q=Path(n);assert q.suffix.lower() not in blocked_suffix and q.name.lower() not in {'server.env','secrets.h','.env'}
   assert not any(x in blocked_dirs for x in q.parts)
 print(path.name,path.stat().st_size)
full=O/'RoomGuard_V2_FullProject.zip'
archive(full,[(p,'roomguard-v2/'+p.relative_to(R).as_posix()) for p in files+[manifest]])
arduino=O/'RoomGuard_V2_ArduinoIDE.zip'
archive(arduino,[(p,'RoomGuard_V2_ArduinoIDE/'+p.relative_to(R).as_posix()) for p in files if p.relative_to(R).parts[0]=='arduino' or p.name.startswith('ESP手机配网与Arduino烧录_V2') or p.name=='THIRD_PARTY.md'])
base=O/'RoomGuard_V2_基板参考草案_不可直接打板.zip'
archive(base,[(p,p.relative_to(R).as_posix()) for p in files if p.relative_to(R).parts[0]=='hardware' or p.name.startswith('通用基板设计说明_V1.1') or p.name in {'build_baseboard.py','build_baseboard_pcb.py','draw_baseboard_overview.py'}])
exported=[]
for p in (R/'docs').glob('*_V2.*'):
 if p.suffix in {'.pdf','.docx','.png','.mmd'}:shutil.copyfile(p,O/p.name);exported.append(O/p.name)
for p in (R/'presentation').glob('RoomGuard_V2_*.p*'):
 shutil.copyfile(p,O/p.name);exported.append(O/p.name)
for name in ['总览1.png','总览2.png']:
 dest=O/('V2_PPT_'+name);shutil.copyfile(R/'presentation'/name,dest);exported.append(dest)
for name in ['RoomGuard-Windows10-x64.exe','RoomGuard-Android5.1.apk']:
 src=R/'artifacts'/name;dest=O/(src.stem+'_V2'+src.suffix);shutil.copyfile(src,dest);exported.append(dest)
index=O/'RoomGuard_V2_下载与使用说明.txt'
index.write_text('''RoomGuard V2.0 完整交付导航

1. RoomGuard_V2_FullProject.zip是完整项目，内层目录roomguard-v2；树莓派按《树莓派新手部署与维护_V2》从写卡、SSH、安装、校时开始。
2. Arduino IDE工程在arduino/RoomGuard_ESP32与RoomGuard_ESP8266，分别编译，不能互刷BIN；烧录后手机连ESP加密热点配置Wi-Fi／Pi地址／接入码，教师后台核对并批准。
3. 新装节点为空是正常状态；101绑定ESP32、102绑定ESP8266。新增同类节点重复配网批准，网页／EXE／APK自动显示。
4. 教师后台地址：http://实际树莓派IP:8080/teacher；监控：http://实际树莓派IP:8080/；只读大屏加?screen=1。安装时自行设置admin密码。
5. Windows EXE需要Windows10 x64与Edge；APK minSdk22、版本2.0。只装APK不代表OPPO后台保活已通过。
6. PPT为20页主讲＋4页隐藏答辩备页，淡入切页、逐页备注；先改学校和姓名，再根据实物测试更新展示证据。附双人排练手册。
7. 基板仍是V1.1电气／布局参考，已知每侧15针和2.54mm；排距与模块脚序待核验，PCB未布线，无制造Gerber。
8. 已通过：两平台Arduino编译、21项自动测试、C++告警状态机、真实MQTT代理集成、Chromium自适应与标签转义、APK／EXE构建、PPT渲染检查。
9. 待现场验收：Pi ARM64安装与受限root助手、ESP物理烧录与配网、电平与传感器响应、Windows启动、OPPO Android5.1后台／锁屏、整机连续运行。用《实机验收记录模板_V2》留真实记录。
10. 自动审批拒绝了复制旧Android签名私钥，已改用本次新开发测试签名。所有私钥不进包；旧版APK可能需卸载后安装，并重新设置地址和后台许可。
11. 可信局域网部署；不含TLS／公网部署方案。DEMO和TEST_HELPER仅测试，不用于生产。断网恢复上报当前状态，未实现完整历史补传。
12. 源文件、库、构建日志、测试证据、文档和演示均在完整项目中。外层重复放常用手册与可执行文件，便于直接查阅；无需重复安装两套。

完整项目内artifacts/SHA256SUMS_V2.txt为文件校验清单。外层RoomGuard_V2_SHA256.txt校验本批下载文件；验收边界以《测试与交付说明_V2》为准。
''')
exported.append(index)
products=[full,arduino,base]+sorted(exported)
sums=O/'RoomGuard_V2_SHA256.txt';sums.write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in products))
bundle=O/'RoomGuard_V2_完整交付包.zip'
archive(bundle,[(p,'RoomGuard_V2_交付/'+p.name) for p in products+[sums]])
(O/(bundle.name+'.sha256.txt')).write_text(hashlib.sha256(bundle.read_bytes()).hexdigest()+'  '+bundle.name+'\n')
with zipfile.ZipFile(full) as z:
 names=set(z.namelist())
 for chip in ['ESP32','ESP8266']:
  for name in ['RoomGuard_'+chip+'.ino','NodeRuntime.cpp','NetworkPortal.cpp','NetworkPortal.h','PortalLite.h','node_options.h','alarm.h']:
   assert 'roomguard-v2/arduino/RoomGuard_'+chip+'/'+name in names
 assert 'roomguard-v2/tools/package_release_v2.py' in names
 for line in checks.splitlines():
  digest,name=line.split('  ',1);assert hashlib.sha256(z.read('roomguard-v2/'+name)).hexdigest()==digest
print('PASS: ZIP integrity, source hashes, project completeness, key/data exclusion and readable archive permissions.')
