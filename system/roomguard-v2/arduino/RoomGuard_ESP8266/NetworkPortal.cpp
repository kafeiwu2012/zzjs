#include "NetworkPortal.h"
#include <ArduinoJson.h>
#include "PortalLite.h"
PortalLite portal;
#ifdef ESP32
Preferences networkPrefs;
#endif
NetworkSettings net,previous;bool deferredConnect=false,portalOn=false,candidate=false,storageReady=false,enrolling=false;String csrf,rx;uint32_t portalAt=0,candidateAt=0,enrollAt=0,requestAt=0,pressedAt=0;WiFiClient enrollment;
String randomText(){String s;for(int i=0;i<3;i++){
#ifdef ESP32
 s+=String(esp_random(),HEX);
#else
 s+=String(os_random(),HEX);
#endif
}return s;}
String escapeHtml(String s){s.replace("&","&amp;");s.replace("<","&lt;");s.replace(">","&gt;");s.replace("\"","&quot;");return s;}
bool loadNetwork(){
#ifdef ESP32
 networkPrefs.begin("rg-network",false);String bundle=networkPrefs.getString("bundle","");if(bundle.length()){StaticJsonDocument<1536> j;if(!deserializeJson(j,bundle)){net.ssid=j["ssid"]|"";net.password=j["wifi"]|"";net.server=j["server"]|"";net.code=j["code"]|"";net.mqttPassword=j["mqtt"]|"";net.apPassword=j["ap"]|"";}}storageReady=true;
#else
 LittleFSConfig fs;fs.setAutoFormat(false);LittleFS.setConfig(fs);storageReady=LittleFS.begin();if(storageReady){File f=LittleFS.open("/network.json","r");if(f){StaticJsonDocument<1536> j;if(!deserializeJson(j,f)){net.ssid=j["ssid"]|"";net.password=j["wifi"]|"";net.server=j["server"]|"";net.code=j["code"]|"";net.mqttPassword=j["mqtt"]|"";net.apPassword=j["ap"]|"";}f.close();}}
#endif
 return net.ssid.length()&&net.server.length();}
bool saveNetwork(bool initialize=false){
#ifdef ESP32
 StaticJsonDocument<1536> j;j["ssid"]=net.ssid;j["wifi"]=net.password;j["server"]=net.server;j["code"]=net.code;j["mqtt"]=net.mqttPassword;j["ap"]=net.apPassword;String bundle;serializeJson(j,bundle);return networkPrefs.putString("bundle",bundle)>0;
#else
 if(!storageReady){if(!initialize||!LittleFS.format())return false;storageReady=LittleFS.begin();if(!storageReady)return false;}
 StaticJsonDocument<1536> j;j["ssid"]=net.ssid;j["wifi"]=net.password;j["server"]=net.server;j["code"]=net.code;j["mqtt"]=net.mqttPassword;j["ap"]=net.apPassword;File f=LittleFS.open("/network.tmp","w");if(!f)return false;serializeJson(j,f);f.close();return LittleFS.rename("/network.tmp","/network.json");
#endif
}
void connectWifi(){WiFi.begin(net.ssid.c_str(),net.password.c_str());}
void page(){String html=F("<!doctype html><html lang='zh-CN'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>RoomGuard 节点配网</title><style>body{font:16px sans-serif;background:#f1f5fa;color:#17354e;margin:20px auto;max-width:500px;padding:15px}form{background:white;padding:22px;border-radius:12px}input,button{display:block;box-sizing:border-box;width:100%;padding:12px;margin:8px 0 18px}button{background:#167fa6;color:white;border:0}small{color:#697d92}</style><h1>RoomGuard 节点配置</h1><p>设备：");html+=escapeHtml(net.id);html+=F("</p><form action='/save' method='post'><input name='csrf' type='hidden' value='");html+=csrf;html+=F("'><label>路由器 Wi-Fi 名称</label><input name='ssid' maxlength='32' required value='");html+=escapeHtml(net.ssid);html+=F("'><label>Wi-Fi 密码（留空保留原密码）</label><input name='password' type='password' maxlength='63'><label>树莓派 IPv4（不带 http://）</label><input name='server' required value='");html+=escapeHtml(net.server);html+=F("'><label>教师接入码（新接入／换服务器时填写）</label><input name='code' autocomplete='off' maxlength='80'><small>保存后尝试连接。切回比赛Wi-Fi，请教师批准设备；失败60秒回退原网络。网页不要求互联网。</small>");if(!storageReady)html+=F("<p><label><input type='checkbox' name='initialize' value='yes' required>确认首次初始化Flash文件系统（会清空该文件系统）</label></p>");html+=F("<button>试连接并保存</button></form><p>热点10分钟后关闭；重新配置请在程序运行后长按BOOT/FLASH约5秒，勿在上电时按住。</p></html>");portal.sendHeader("Cache-Control","no-store");portal.send(200,"text/html; charset=utf-8",html);}
void openPortal(){if(portalOn)return;WiFi.mode(WIFI_AP_STA);String ssid="RG-CONFIG-"+net.id.substring(net.id.length()-6);WiFi.softAP(ssid.c_str(),net.apPassword.c_str());csrf=randomText();portalAt=millis();portalOn=true;portal.begin();Serial.printf("\nAP SSID: %s\nAP PASSWORD: %s\nOpen http://192.168.4.1\n",ssid.c_str(),net.apPassword.c_str());}
void networkSetup(){WiFi.persistent(false);WiFi.mode(WIFI_STA);String mac=WiFi.macAddress();mac.replace(":","");mac.toLowerCase();
#ifdef ESP32
 net.id="rg-esp32-"+mac;
#else
 net.id="rg-esp8266-"+mac;
#endif
 loadNetwork();if(net.apPassword.length()<12){net.apPassword=randomText().substring(0,16);if(storageReady)saveNetwork();}pinMode(0,INPUT_PULLUP);
 portal.on("/",HTTP_GET,page);portal.on("/save",HTTP_POST,[](){if(portal.arg("csrf")!=csrf){portal.send(403,"text/plain","Invalid form");return;}String ssid=portal.arg("ssid"),server=portal.arg("server"),pwd=portal.arg("password"),code=portal.arg("code");IPAddress ip;if(!ssid.length()||ssid.length()>32||!ip.fromString(server)||pwd.length()>63||code.length()>80){portal.send(400,"text/plain","Invalid fields");return;}bool initialize=portal.arg("initialize")=="yes";if(!storageReady&&!initialize){portal.send(409,"text/plain","Storage initialization required");return;}
 if(!storageReady){
#ifndef ESP32
 if(!LittleFS.format()||!LittleFS.begin()){portal.send(500,"text/plain","Storage failed");return;}storageReady=true;
#endif
 }
 previous=net;candidate=true;candidateAt=millis();net.ssid=ssid;if(pwd.length())net.password=pwd;if(server!=net.server||code.length())net.mqttPassword="";net.server=server;if(code.length())net.code=code;enrollment.stop();enrolling=false;deferredConnect=true;portal.send(200,"text/html; charset=utf-8",F("<meta charset='utf-8'><h2>正在试连接</h2><p>请切回比赛路由器Wi-Fi，在教师后台批准设备。收到有效接入响应后才持久保存；失败60秒回退原配置。首次接入请保持设备供电。</p>"));});
 if(net.ssid.length())connectWifi();else openPortal();Serial.printf("RoomGuard V2 device: %s\n",net.id.c_str());}
void completeEnrollment(){int start=rx.indexOf("\r\n\r\n");if(start<0)return;StaticJsonDocument<1024> j;if(deserializeJson(j,rx.substring(start+4)))return;String status=j["status"]|"";
 if(status=="pending"||status=="approved"){if(status=="approved"){net.mqttPassword=j["mqtt_password"]|"";net.code="";}if(saveNetwork()){candidate=false;Serial.println(status=="approved"?"Enrollment approved":"Waiting for teacher approval");}}
}
void networkLoop(){uint32_t now=millis();if(deferredConnect&&uint32_t(now-candidateAt)>500){deferredConnect=false;connectWifi();}if(digitalRead(0)==LOW){if(!pressedAt)pressedAt=now;if(uint32_t(now-pressedAt)>5000)openPortal();}else pressedAt=0;
 if(portalOn){portal.handleClient();if(uint32_t(now-portalAt)>600000){portal.stop();WiFi.softAPdisconnect(true);portalOn=false;}}
 if(candidate&&uint32_t(now-candidateAt)>60000){net=previous;candidate=false;enrollment.stop();enrolling=false;connectWifi();Serial.println("Candidate failed, reverted");}
 if(enrolling){size_t budget=256;while(budget--&&enrollment.available())rx+=(char)enrollment.read();if(rx.length()>4096||uint32_t(now-requestAt)>5000){enrollment.stop();enrolling=false;}else if(!enrollment.connected()&&!enrollment.available()){completeEnrollment();enrollment.stop();enrolling=false;}}
 if(WiFi.status()!=WL_CONNECTED||enrolling||net.mqttPassword.length()||!net.code.length()||uint32_t(now-enrollAt)<5000)return;
 enrollAt=now;IPAddress ip;if(!ip.fromString(net.server))return;enrollment.setTimeout(150);
#ifdef ESP32
 if(!enrollment.connect(ip,8080,150))return;
#else
 if(!enrollment.connect(ip,8080))return;
#endif
 StaticJsonDocument<512> j;j["id"]=net.id;j["code"]=net.code;
#ifdef ESP32
 j["model"]="ESP32";
#else
 j["model"]="ESP8266";
#endif
 j["firmware"]="2.0";JsonArray a=j.createNestedArray("capabilities");for(const char* k:{"dht11","mq2","flame","buzzer","rgb"})a.add(k);String body;serializeJson(j,body);enrollment.print(String("POST /api/enroll HTTP/1.1\r\nHost: ")+net.server+":8080\r\nContent-Type: application/json\r\nConnection: close\r\nContent-Length: "+body.length()+"\r\n\r\n"+body);rx="";requestAt=now;enrolling=true;
}

void networkMQTTReady(){if(candidate){if(!saveNetwork())return;candidate=false;}if(portalOn){portal.stop();WiFi.softAPdisconnect(true);portalOn=false;}}
