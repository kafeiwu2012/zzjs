# RoomGuard V2.0 · 自适应节点与教师管理中心

这是新的主交付版本，保留V1.1硬件参考，但网络配置与节点管理以V2文档为准。

## 阅读顺序

1. docs/需求与协议基线_V2.md：范围、协议、接入与权限。
2. docs/树莓派新手部署与维护_V2.md：写卡、SSH、安装、升级、诊断与恢复。
3. docs/ESP手机配网与Arduino烧录_V2.md：同型号通用固件，手机连接加密热点配网。
4. docs/教师后台操作手册_V2.md：批准设备、分配学生权限、节点参数、服务与终端显示。
5. docs/测试与交付说明_V2.md：软件验证与实物待验收项。
6. docs/开发与重建指南_V2.md：源码入口、电脑演示、软件回归和各平台重建。
7. docs/双人演讲与教师排练_V2.md：双人展示、逐页讲稿与答辩。

首次安装：sudo bash deploy/install.sh；已有V1.1升级：先备份，再sudo bash deploy/update.sh。不把生产环境设置为DEMO或TEST_HELPER。

监控工作台：http://树莓派IP:8080/；教师后台：http://树莓派IP:8080/teacher。首次账号admin，密码安装时设置。新安装节点清单为空；生成接入码、手机配网、教师批准后自动出现。

Arduino工程：arduino/RoomGuard_ESP32与arduino/RoomGuard_ESP8266。固定版本库在arduino/libraries。无编译内置的SSID、房间或共享MQTT密码，两种芯片分别编译；第一次仍用USB烧录，不提供OTA。node_options.h是硬件参数，先核对实际接线。

只看模拟演示：安装server/requirements.txt后，在根目录python -m tools.run_demo，打开http://127.0.0.1:8080。模拟账号admin／DemoOnly-123456，三模拟节点；DEMO不修改真实服务或账号，不用于证明实物通过。

EXE需要Windows10 x64和Edge；APK minSdk22，开发测试签名，旧版可能需卸载再安装。后台告警仍需手机网络与系统许可及指定OPPO真机验收。

hardware是V1.1基板审阅草案，不是制造版；机械尺寸待核验，PCB未布线。旧版资料仅作历史参考，不把旧secrets.h配置流程用于V2新工程。
