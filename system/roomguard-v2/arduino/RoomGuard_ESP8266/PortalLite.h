#pragma once
#include <functional>
#define HTTP_GET 1
#define HTTP_POST 2
// Cooperative bounded HTTP parser: one client, max4KiB, no blocking reads.
class PortalLite {
 WiFiServer server{80};WiFiClient client;String input,output,body;uint32_t at=0;size_t sent=0;std::function<void()> getHandler,postHandler;
 String decode(String s){String out;for(size_t i=0;i<s.length();i++){char c=s[i];if(c=='+')out+=' ';else if(c=='%'&&i+2<s.length()){char b[3]={s[i+1],s[i+2],0};char v=strtol(b,nullptr,16);if(v)out+=v;i+=2;}else out+=c;}return out;}
public:
 void on(const char*,int method,std::function<void()> fn){if(method==HTTP_GET)getHandler=fn;else postHandler=fn;}
 void begin(){server.begin();}
 void stop(){client.stop();
#ifdef ESP32
 server.end();
#else
 server.stop();
#endif
 }
 void sendHeader(const char*,const char*){}
 String arg(const char* key){size_t start=0;while(start<body.length()){int end=body.indexOf('&',start);if(end<0)end=body.length();String pair=body.substring(start,end);int eq=pair.indexOf('=');if(eq>=0&&decode(pair.substring(0,eq))==key)return decode(pair.substring(eq+1));start=end+1;}return "";}
 void send(int code,const char* type,String payload){output=String("HTTP/1.1 ")+code+" Response\r\nConnection: close\r\nCache-Control: no-store\r\nContent-Type: "+type+"\r\nContent-Length: "+payload.length()+"\r\n\r\n"+payload;sent=0;}
 void handleClient(){if(!client||(!client.connected()&&!client.available())){client.stop();client=server.available();input="";output="";body="";sent=0;at=millis();}
 if(!client)return;
 // Configuration is accepted only from the ESP access point subnet.
 IPAddress ip=client.remoteIP();if(ip[0]!=192||ip[1]!=168||ip[2]!=4){client.stop();return;}
 if(uint32_t(millis()-at)>5000){client.stop();return;}
 if(output.length()){size_t available=client.availableForWrite();if(available){size_t count=output.length()-sent;if(count>128)count=128;if(count>available)count=available;sent+=client.write((const uint8_t*)output.c_str()+sent,count);if(sent==output.length())client.stop();}return;}
 size_t budget=256;while(budget--&&client.available())input+=(char)client.read();if(input.length()>4096){client.stop();return;}
 int end=input.indexOf("\r\n\r\n");if(end<0)return;String headers=input.substring(0,end);String lower=headers;lower.toLowerCase();int pos=lower.indexOf("content-length:");int len=0;if(pos>=0){int e=lower.indexOf("\r\n",pos);len=lower.substring(pos+15,e<0?lower.length():e).toInt();}if(len<0||len>2048){client.stop();return;}if(input.length()<size_t(end+4+len))return;body=input.substring(end+4,end+4+len);
 if(input.startsWith("GET / ")&&getHandler)getHandler();else if(input.startsWith("POST /save ")&&postHandler)postHandler();else send(404,"text/plain","Not found");
 }
};
