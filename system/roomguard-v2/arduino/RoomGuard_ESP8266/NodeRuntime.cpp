#include <Arduino.h>
#ifdef ESP32
#include <WiFi.h>
#include <Preferences.h>
Preferences prefs;
const int DHT_PIN=27, MQ_PIN=34, MQ_DO=26, FLAME=25, BUZZ=23, RED=18,GREEN=19,BLUE=21;
#else
#include <ESP8266WiFi.h>
#include <LittleFS.h>

// D4/GPIO2 DHT data must have a pull-up to3.3V for reliable boot.
const int DHT_PIN=2, MQ_PIN=A0, MQ_DO=14, FLAME=12, BUZZ=13, RED=4,GREEN=5,BLUE=16;
#endif
#include <AsyncMqttClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include "node_options.h"
#include "NetworkPortal.h"
#define DEVICE_ID net.id.c_str()
#include "alarm.h"
char brokerId[80],brokerPassword[96];AsyncMqttClient mqtt;DHT dht(DHT_PIN,DHT11);Alarm alarmState;
String configEpoch,bootId,eventId;uint32_t seq=0,configVersion=0,eventCounter=0,lastReport=0,lastDht=0,lastMQ=0,lastRetry=0;
uint32_t reportMs=5000;int hardwareProfile=HARDWARE_PROFILE;
uint32_t normalSince=0,smokeSince=0,flameSince=0;bool smoke=false,flame=false,dhtOk=false,mqReady=false,reportNow=true;
float temp=NAN,hum=NAN,mqVoltage=0;int mqRaw=0;String recentIds[8];int recentIndex=0;
String topic(const char* suffix){return String("building/")+DEVICE_ID+"/"+suffix;}
void saveConfig(){
#ifdef ESP32
 prefs.putUInt("report",reportMs/1000);prefs.putUInt("hardware",hardwareProfile);prefs.putUInt("version",configVersion);prefs.putUInt("clear",alarmState.clearMs/1000);prefs.putString("epoch",configEpoch);
#else
 File f=LittleFS.open("/config.json","w");if(f){StaticJsonDocument<384> j;j["version"]=configVersion;j["clear"]=alarmState.clearMs/1000;j["report"]=reportMs/1000;j["hardware"]=hardwareProfile;j["epoch"]=configEpoch;serializeJson(j,f);f.close();}
#endif
}
void loadConfig(){
#ifdef ESP32
 prefs.begin("roomguard",false);configEpoch=prefs.getString("epoch","");reportMs=prefs.getUInt("report",5)*1000;hardwareProfile=prefs.getUInt("hardware",HARDWARE_PROFILE);configVersion=prefs.getUInt("version",0);alarmState.clearMs=prefs.getUInt("clear",10)*1000;
#else
 if(LittleFS.begin()){File f=LittleFS.open("/config.json","r");if(f){StaticJsonDocument<384> j;if(!deserializeJson(j,f)){configEpoch=j["epoch"]|"";reportMs=(j["report"]|5)*1000;hardwareProfile=j["hardware"]|HARDWARE_PROFILE;configVersion=j["version"]|0;alarmState.clearMs=(j["clear"]|10)*1000UL;}f.close();}}
#endif
 if(reportMs<5000||reportMs>60000)reportMs=5000;if(hardwareProfile!=0&&hardwareProfile!=1)hardwareProfile=HARDWARE_PROFILE;
 if(alarmState.clearMs<1000||alarmState.clearMs>300000)alarmState.clearMs=10000;
}
void leds(bool r,bool g,bool b){
 digitalWrite(RED,r);digitalWrite(GREEN,g);digitalWrite(BLUE,b);
}
String nonces[3]; uint32_t nonceAt[3]={0,0,0};uint8_t nonceIndex=0;
void report(){
 nonceIndex=(nonceIndex+1)%3;nonces[nonceIndex]=bootId+"-"+String(seq+1);nonceAt[nonceIndex]=millis();
 StaticJsonDocument<1400> j;j["control_nonce"]=nonces[nonceIndex];j["boot"]=bootId;j["seq"]=++seq;j["uptime_ms"]=millis();j["event_id"]=eventId;j["active"]=alarmState.active;j["muted"]=alarmState.muted;j["clearing"]=alarmState.clearing;
 JsonArray r=j.createNestedArray("reasons");if(alarmState.reasons&1)r.add("smoke");if(alarmState.reasons&2)r.add("flame");
 j["smoke"]=smoke;j["flame"]=flame;j["dht_ok"]=dhtOk;j["mq_ready"]=mqReady;
 if(dhtOk){j["temperature"]=temp;j["humidity"]=hum;}else{j["temperature"]=nullptr;j["humidity"]=nullptr;}
 j["mq_raw"]=mqRaw;j["mq_voltage"]=mqVoltage;j["config_version"]=configVersion;j["rssi"]=WiFi.RSSI();j["model"]=
#ifdef ESP32
 "ESP32";
#else
 "ESP8266";
#endif
 j["firmware"]="2.0";j["config_epoch"]=configEpoch;j["clear_seconds"]=alarmState.clearMs/1000;j["hardware_profile"]=hardwareProfile;j["report_seconds"]=reportMs/1000;
 char data[1400];serializeJson(j,data,sizeof(data));if(mqtt.publish(topic("state").c_str(),1,false,data)){lastReport=millis();reportNow=false;}
}
void ack(String id,const char* status,const char* reason=""){
 StaticJsonDocument<256> j;j["id"]=id;j["status"]=status;j["reason"]=reason;char b[256];serializeJson(j,b,sizeof(b));mqtt.publish(topic("ack").c_str(),1,false,b);
}
void callback(char*,byte* payload,unsigned int length){
 StaticJsonDocument<512> j;if(deserializeJson(j,payload,length))return;
 String id=j["id"]|"",kind=j["kind"]|"";if(id.length()==0||id.length()>80)return;
 String nonce=j["nonce"]|"";bool fresh=false;for(int i=0;i<3;i++)if(nonce.length()&&nonce==nonces[i]&&uint32_t(millis()-nonceAt[i])<=10000)fresh=true;
 if(!fresh){ack(id,"rejected","stale command nonce");return;}
 for(int i=0;i<8;i++)if(recentIds[i]==id){ack(id,"applied","duplicate");return;}
 // Non-retained commands plus MQTT clean session avoid replay. Event matching limits silence scope.
 bool ok=false;
 if(kind=="silence"){
  String event=j["event_id"]|"";
  if(alarmState.active&&event==eventId){alarmState.muted=true;ok=true;}
 }else if(kind=="config"){
  String epoch=j["epoch"]|"";uint32_t v=j["version"]|0;int sec=j["clear_seconds"]|0;int rpt=j["report_seconds"]|5;int hp=j["hardware_profile"]|hardwareProfile;
  if((epoch!=configEpoch||v>=configVersion)&&sec>=1&&sec<=300&&rpt>=5&&rpt<=60&&(hp==0||hp==1)){if(epoch!=configEpoch||v!=configVersion||alarmState.clearMs!=uint32_t(sec)*1000||reportMs!=uint32_t(rpt)*1000||hardwareProfile!=hp){configEpoch=epoch;reportMs=uint32_t(rpt)*1000;hardwareProfile=hp;configVersion=v;alarmState.clearMs=uint32_t(sec)*1000;saveConfig();}ok=true;}
 }
 if(ok){recentIds[recentIndex++%8]=id;reportNow=true;ack(id,"applied");}
 else ack(id,"rejected","event mismatch or invalid config");
}
// Transport callbacks only enqueue. Sensor/alarm/config state is owned by loop().
volatile bool commandPending=false; char commandBuffer[512];unsigned int commandLength=0;
#ifdef ESP32
portMUX_TYPE commandMux=portMUX_INITIALIZER_UNLOCKED;
#define LOCK_COMMAND portENTER_CRITICAL(&commandMux)
#define UNLOCK_COMMAND portEXIT_CRITICAL(&commandMux)
#else
#define LOCK_COMMAND noInterrupts()
#define UNLOCK_COMMAND interrupts()
#endif
void incoming(char* topicIn,char* payload,AsyncMqttClientMessageProperties properties,size_t len,size_t index,size_t total){
 static char assembly[512];static bool receiving=false;
 if(index==0)receiving=!commandPending&&total>0&&total<sizeof(assembly);
 if(!receiving||index+len>=sizeof(assembly))return;
 memcpy(assembly+index,payload,len);
 if(index+len==total){LOCK_COMMAND;if(!commandPending){memcpy(commandBuffer,assembly,total);commandLength=total;commandPending=true;}UNLOCK_COMMAND;receiving=false;}
}
bool filtered(int pin,bool &current,uint32_t &since,uint32_t now){
 bool raw=digitalRead(pin)==LOW;
 if(raw==current){since=now;return current;}
 if(uint32_t(now-since)>=150){current=raw;since=now;}
 return current;
}
void setup(){
 digitalWrite(BUZZ,HIGH);pinMode(BUZZ,OUTPUT);pinMode(RED,OUTPUT);pinMode(GREEN,OUTPUT);pinMode(BLUE,OUTPUT);pinMode(MQ_DO,INPUT);pinMode(FLAME,INPUT);
#ifdef ESP32
 pinMode(RED,OUTPUT);pinMode(GREEN,OUTPUT);pinMode(BLUE,OUTPUT);analogReadResolution(12);analogSetPinAttenuation(MQ_PIN,ADC_11db);
 bootId=String((uint32_t)ESP.getEfuseMac(),HEX)+String(esp_random(),HEX);
#else
 bootId=String(ESP.getChipId(),HEX)+String(os_random(),HEX);
#endif
 Serial.begin(115200);leds(false,false,false);networkSetup();net.id.toCharArray(brokerId,sizeof(brokerId));loadConfig();dht.begin();
 mqtt.onMessage(incoming);mqtt.setCleanSession(true);mqtt.setKeepAlive(15);lastRetry=millis()-5000;lastDht=millis()-5000;

}
void loop(){
 networkLoop();if(mqtt.connected()&&!net.mqttPassword.length())mqtt.disconnect();uint32_t now=millis();mqReady=now>=MQ_WARMUP_MS; // wraps at49 days; warmup latched below
 static bool readyLatched=false;if(mqReady)readyLatched=true;mqReady=readyLatched;
 bool before=alarmState.active;
 filtered(FLAME,flame,flameSince,now);filtered(MQ_DO,smoke,smokeSince,now);
 if(alarmState.update((mqReady&&smoke?1:0)|(flame?2:0),mqReady,now))reportNow=true;
 if(!before&&alarmState.active)eventId=bootId+"-"+String(++eventCounter);
 bool flash=(now/250)%2;
 if(alarmState.active)leds(flash,false,false);else if(!mqReady||!dhtOk)leds(flash,flash,false);else if(WiFi.status()!=WL_CONNECTED||!mqtt.connected())leds(false,false,flash);else leds(false,true,false);
 digitalWrite(BUZZ,alarmState.active&&!alarmState.muted&&flash?LOW:HIGH);
 if(uint32_t(now-lastDht)>=reportMs){lastDht=now;hum=dht.readHumidity();temp=dht.readTemperature();dhtOk=isfinite(hum)&&isfinite(temp);}
 if(uint32_t(now-lastMQ)>=500){lastMQ=now;mqRaw=analogRead(MQ_PIN);
#ifdef ESP32
 mqVoltage=analogReadMilliVolts(MQ_PIN)/1000.0f*(hardwareProfile==1?3.0f:1.667f);
#else
 mqVoltage=mqRaw/1023.0f*ESP8266_A0_FULL_SCALE*ESP8266_MQ_DIVIDER_RATIO;
#endif
 }
 // Async transport keeps connection attempts and broker waits out of sensor scheduling.
 if(WiFi.status()==WL_CONNECTED&&net.mqttPassword.length()&&!mqtt.connected()&&uint32_t(now-lastRetry)>=5000){lastRetry=now;IPAddress brokerIp;brokerIp.fromString(net.server);mqtt.setServer(brokerIp,1883);mqtt.setClientId(brokerId);net.mqttPassword.toCharArray(brokerPassword,sizeof(brokerPassword));mqtt.setCredentials(brokerId,brokerPassword);mqtt.connect();}
 static bool wasConnected=false;
 if(mqtt.connected()){
  if(!wasConnected){networkMQTTReady();mqtt.subscribe(topic("command").c_str(),1);reportNow=true;}
  if(commandPending){char local[512];unsigned int length;LOCK_COMMAND;length=commandLength;memcpy(local,commandBuffer,length);commandPending=false;UNLOCK_COMMAND;callback(nullptr,(byte*)local,length);}
  if(reportNow||uint32_t(now-lastReport)>=reportMs)report();
 }
 wasConnected=mqtt.connected();
 delay(5);
}
