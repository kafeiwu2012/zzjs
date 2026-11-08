from pathlib import Path
import json,re
H=Path(__file__).resolve().parents[1]/'hardware'
def sexp(text):
 tokens=re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+',text);it=iter(tokens)
 def read(t):
  if t=='(':
   a=[]
   for t in it:
    if t==')':return a
    a.append(read(t))
   raise ValueError('unclosed')
  return json.loads(t) if t.startswith('"') else t
 return read(next(it))
def child(seq,name):return next(x for x in seq if isinstance(x,list) and x and x[0]==name)
def test_exported_cad_net_connectivity():
 data=sexp((H/'RoomGuard_Baseboard_DRAFT.net').read_text());nets=child(data,'nets')[1:];mapping={}
 for n in nets:
  name=child(n,'name')[1].lstrip('/');mapping[name]={(child(node,'ref')[1],child(node,'pin')[1]) for node in n if isinstance(node,list) and node and node[0]=='node'}
 assert ('J7','4') in mapping['ADC32']
 assert ('J9','1') in mapping['ADC8266']
 assert ('U3','6') in mapping['SMOKE_MCU'] and ('J7','9') in mapping['SMOKE_MCU'] and ('J10','8') in mapping['SMOKE_MCU']
 # Physical SN74LVC2G17 pins:1A1,2GND,3A2,4Y2,5VCC,6Y1.
 assert ('U3','2') in mapping['GND'] and ('U3','3') in mapping['FLAME_IN']
 assert ('U3','5') in mapping['ESP_3V3']
 assert ('U1','5') in mapping['SENSOR_3V3'] and ('U1','5') not in mapping['ESP_3V3']
 assert ('Q3','2') in mapping['BUZZ_MCU'] and ('Q3','3') in mapping['BUZZ_INPUT']
 assert ('U2','1') in mapping['MQ_BUF'] and ('U2','2') in mapping['MQ_BUF']
def test_adc_limits_and_mechanical_not_approved():
 max32=5.25*10100/(19800+10100);max8266=5.25*10100/(55440+10100)
 assert max32<1.78 and max8266<.82
 m=json.loads((H/'mechanical.json').read_text());assert m['pitch_mm']==2.54 and m['pins_per_side']==15
 assert m['esp32_row_center_mm'] is None and m['esp8266_row_center_mm'] is None
 assert m['status']=='DRAFT_NOT_FOR_FABRICATION'
 assert not list(H.rglob('*.gbr'))
