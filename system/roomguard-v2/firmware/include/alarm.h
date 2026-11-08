#pragma once
#include <stdint.h>
struct Alarm {
 bool active=false,muted=false,clearing=false;
 uint8_t reasons=0;
 uint32_t clearAt=0, clearMs=10000;
 bool update(uint8_t next, bool smokeValid, uint32_t now) {
  bool a=active,m=muted,c=clearing; uint8_t r=reasons;
  // A previously observed smoke condition may not clear on an invalid MQ reading.
  if(!smokeValid && (reasons&1)) next|=1;
  if(next){if(!active){active=true;muted=false;}if(next & ~reasons)muted=false;clearing=false;}
  else if(active){if(!clearing){clearing=true;clearAt=now;}if(uint32_t(now-clearAt)>=clearMs){active=false;muted=false;clearing=false;}}
  reasons=next;
  return a!=active||m!=muted||r!=reasons||c!=clearing;
 }
};
