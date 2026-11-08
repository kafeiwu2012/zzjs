"""Generate reviewable KiCad schematic/netlist source and unrouted placement draft.
Mechanical dimensions are NOT approved for manufacturing. Do not generate Gerbers.
"""
from pathlib import Path
import json,csv,uuid,math
R=Path(__file__).resolve().parents[1];H=R/'hardware';H.mkdir(exist_ok=True)
parts=[]
def add(ref,value,pins,fp='',group='logic',notes=''):
 parts.append(dict(ref=ref,value=value,pins={str(k):v for k,v in pins.items()},footprint=fp,group=group,notes=notes))
RFP='Resistor_SMD:R_0805_2012Metric';CFP='Capacitor_SMD:C_0805_2012Metric'
C2='Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical'
C3='Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical'
C4='Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical'
P15='Connector_PinSocket_2.54mm:PinSocket_1x15_P2.54mm_Vertical'
def resistor(ref,value,a,b,g='logic'):add(ref,value,{1:a,2:b},RFP,g)
def cap(ref,value,a,b,g='power'):add(ref,value,{1:a,2:b},CFP,g)
add('J1','5V INPUT 1=+5V 2=GND',{1:'RAW_5V',2:'GND'},'TerminalBlock:TerminalBlock_bornier-2_P5.08mm','power','Regulated5V only; no12V')
add('F1','PTC hold1.1A / trip2.2A',{1:'RAW_5V',2:'FUSED_IN'},'Fuse:Fuse_1206_3216Metric','power','Verify peak current and thermal derating')
add('Q1','AO3401A reverse-polarity',{1:'RP_GATE',2:'FUSED_OUT',3:'FUSED_IN'},'Package_TO_SOT_SMD:SOT-23','power','Pin1G 2S 3D; verify exact part')
resistor('R1','100k','RP_GATE','GND','power')
add('SW1','POWER SWITCH',{1:'FUSED_OUT',2:'P5V'},C2,'power','External switch header; do not bridge with metal while powered')
cap('C1','100uF/10V','P5V','GND');cap('C2','10uF','P5V','GND');cap('C3','100nF','P5V','GND')
add('U1','AP2112K-3.3',{1:'P5V',2:'GND',3:'P5V',4:'NC_U1_4',5:'SENSOR_3V3'},'Package_TO_SOT_SMD:SOT-23-5','power','600mA maximum datasheet rating; design sensor load<=100mA pending measurement')
cap('C4','1uF','P5V','GND');cap('C5','1uF','SENSOR_3V3','GND');cap('C6','10uF','SENSOR_3V3','GND')
add('JP1','SELECT ESP VREF (32:1-2 / 8266:2-3)',{1:'ESP32_3V3',2:'ESP_3V3',3:'ESP8266_3V3'},C3,'power','One shunt only. Never bridge external LDO to ESP3V3')
add('JP2','ESP32 VIN ENABLE',{1:'P5V',2:'ESP32_VIN'},C2,'power','Install only for selected board')
add('JP3','ESP8266 VIN ENABLE',{1:'P5V',2:'ESP8266_VIN'},C2,'power','Install only for selected board')
add('U2','MCP6002-I/P unity buffer',{1:'MQ_BUF',2:'MQ_BUF',3:'MQ_AO',4:'GND',5:'GND',6:'OPB_OUT',7:'OPB_OUT',8:'P5V'},'Package_DIP:DIP-8_W7.62mm','analog','Unused amplifier B is a ground follower, not floating')
cap('C7','100nF','P5V','GND','analog')
resistor('R2','20k 1%','MQ_BUF','ADC32_DIV','analog');resistor('R3','10k 1%','ADC32_DIV','GND','analog');resistor('R4','1k','ADC32_DIV','ADC32','analog');cap('C8','10nF','ADC32','GND','analog')
resistor('R5','56k 1%','MQ_BUF','ADC8266_DIV','analog');resistor('R6','10k 1%','ADC8266_DIV','GND','analog');resistor('R7','1k','ADC8266_DIV','ADC8266','analog');cap('C9','10nF','ADC8266','GND','analog')
add('U3','SN74LVC2G17DCKR',{1:'SMOKE_IN',2:'GND',3:'FLAME_IN',4:'FLAME_MCU',5:'ESP_3V3',6:'SMOKE_MCU'},'Package_TO_SOT_SMD:SOT-363_SC-70-6','logic','5.5V tolerant inputs and Ioff; do not replace with non5V-tolerant HC buffer')
cap('C10','100nF','ESP_3V3','GND','logic')
resistor('R8','1k','MQ_DO','SMOKE_IN');resistor('R9','10k','MQ_DO','P5V')
resistor('R10','1k','FLAME_DO','FLAME_IN');resistor('R11','10k','FLAME_DO','SENSOR_3V3')
add('Q2','BSS138 DHT bidirectional',{1:'ESP_3V3',2:'DHT_MCU',3:'DHT_SENSOR'},'Package_TO_SOT_SMD:SOT-23','logic','Gate ESP VREF; source MCU; drain sensor. No inversion')
resistor('R12','10k','DHT_MCU','ESP_3V3');resistor('R13','10k','DHT_SENSOR','SENSOR_3V3')
add('Q3','BSS138 buzzer low-active',{1:'ESP_3V3',2:'BUZZ_MCU',3:'BUZZ_INPUT'},'Package_TO_SOT_SMD:SOT-23','logic','Module input load must be verified; MCU HIGH=off, LOW=on')
resistor('R14','10k','BUZZ_MCU','ESP_3V3');resistor('R15','10k','BUZZ_INPUT','P5V')
for i,k in enumerate(['R','G','B']):resistor('R'+str(16+i),'330','LED_'+k+'_MCU','LED_'+k)
add('J_DHT','DHT11 SOCKET',{1:'DHT_SENSOR',2:'SENSOR_3V3',3:'GND'},C3,'modules','Reference order DATA VCC GND; physical dimensions pending')
add('J_MQ','MQ2 SOCKET',{1:'MQ_AO',2:'MQ_DO',3:'GND',4:'P5V'},C4,'modules','Reference order AO DO GND VCC; verify actual module')
add('J_FLAME','FLAME SOCKET',{1:'SENSOR_3V3',2:'GND',3:'FLAME_DO'},C3,'modules','Reference order VCC GND DO; verify actual module')
add('J_BUZZ','BUZZER SOCKET',{1:'GND',2:'BUZZ_INPUT',3:'P5V'},C3,'modules','Reference order GND IO VCC; verify actual module')
add('J_RGB','RGB COMMON CATHODE',{1:'GND',2:'LED_B',3:'LED_G',4:'LED_R'},C4,'modules','Reference order GND B G R; verify actual module')
# Top view: antenna at top, USB at bottom. Each connector is separately1..15.
esp32l=['NC32_EN','NC32_VP','NC32_VN','NC32_34_unused','NC32_35','NC32_32','NC32_33','FLAME_MCU','SMOKE_MCU','DHT_MCU','NC32_14','NC32_12','NC32_13','GND','ESP32_VIN']
esp32r=['BUZZ_MCU','NC32_22','NC32_TX0','NC32_RX0','LED_B_MCU','LED_G_MCU','LED_R_MCU','NC32_5','NC32_TX2','NC32_RX2','NC32_4','NC32_2','NC32_15','GND','ESP32_3V3']
# GPIO34 is AO input, replacing its initial unused label.
esp32l[3]='ADC32'
esp8266l=['ADC8266','NC8266_RSV1','NC8266_RSV2','NC8266_SD3','NC8266_SD2','NC8266_SD1','NC8266_CMD','NC8266_SD0','NC8266_CLK','GND','ESP8266_3V3','NC8266_EN','NC8266_RST','GND','ESP8266_VIN']
esp8266r=['LED_B_MCU','LED_G_MCU','LED_R_MCU','NC8266_D3','DHT_MCU','ESP8266_3V3','GND','SMOKE_MCU','FLAME_MCU','BUZZ_MCU','NC8266_D8','NC8266_RX','NC8266_TX','GND','ESP8266_3V3']
for ref,arr in [('J32L',esp32l),('J32R',esp32r),('J8266L',esp8266l),('J8266R',esp8266r)]:add(ref,ref+' 15pin SOCKET',dict(enumerate(arr,1)),P15,'sockets','Pitch2.54mm confirmed; row spacing UNKNOWN; pin labels must be checked against actual board')
# Important named measurements.
for i,net in enumerate(['P5V','SENSOR_3V3','ESP_3V3','MQ_AO','ADC32','ADC8266','SMOKE_MCU','FLAME_MCU','GND'],1):add('TP'+str(i),net,{1:net},'TestPoint:TestPoint_Pad_D2.0mm','testpoints')
aliases={'J_DHT':'J2','J_MQ':'J3','J_FLAME':'J4','J_BUZZ':'J5','J_RGB':'J6','J32L':'J7','J32R':'J8','J8266L':'J9','J8266R':'J10'}
for part in parts:
 if part['group']=='modules':part['footprint']=part['footprint'].replace('Connector_PinHeader_2.54mm:PinHeader_','Connector_PinSocket_2.54mm:PinSocket_')
 if part['ref'] in aliases:part['notes']=part['ref']+'; '+part['notes'];part['ref']=aliases[part['ref']]
mechanical={'status':'DRAFT_NOT_FOR_FABRICATION','pins_per_side':15,'pitch_mm':2.54,'esp32_row_center_mm':None,'esp8266_row_center_mm':None,'module_dimensions_and_pin_orders_verified':False,'nominal_row_center_for_placement_only_mm':25.4,'board_outline_for_review_only_mm':[180,130]}
(H/'mechanical.json').write_text(json.dumps(mechanical,ensure_ascii=False,indent=2));(H/'circuit_source.json').write_text(json.dumps({'revision':'V1.1 review draft','parts':parts},ensure_ascii=False,indent=2))
with (H/'BOM_基板.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['位号','器件或参数','数量','封装','功能分区','核验说明'])
 for p in parts:w.writerow([p['ref'],p['value'],1,p['footprint'],p['group'],p['notes']])
with (H/'逐针网络表.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['位号','针号','网络','说明'])
 for p in parts:
  for pin,net in p['pins'].items():w.writerow([p['ref'],pin,net,p['notes']])
# Modern embedded generic pin-box symbols intentionally show exact pin numbers and nets.
# This avoids silently substituting a similarly named part with a different pinout.
def uid():return str(uuid.uuid4())
def q(t):return '"'+t.replace('\\','\\\\').replace('"','\\"')+'"'
rootid=uid();libs=[];instances=[];wires=[]
group_cols={'power':(28,35),'analog':(210,35),'logic':(395,35),'modules':(210,230),'sockets':(28,230),'testpoints':(395,300)}
counts={g:0 for g in group_cols}
for part in parts:
 ref=part['ref'];pins=list(part['pins'].items());n=len(pins);group=part['group'];idx=counts[group];counts[group]+=1
 gx,gy=group_cols[group]
 if group=='sockets':x=gx+(idx%2)*88;y=gy+(idx//2)*88
 elif group=='modules':x=gx+(idx%2)*88;y=gy+(idx//2)*45
 elif group=='testpoints':x=gx+(idx%3)*55;y=gy+(idx//3)*25
 else:x=gx+(idx%2)*88;y=gy+(idx//2)*25
 pitch=2.54;height=max(7.62,(n+1)*pitch);width=43.18
 name='RG_'+ref;lib='RoomGuard:'+name
 prop='''(property "Reference" "''' +ref+'''" (at 0 3.81 0)(effects(font(size 1.27 1.27))))
(property "Value" '''+q(part['value'])+''' (at 0 6.35 0)(effects(font(size 1.0 1.0))))'''
 body='(rectangle(start 0 0)(end '+str(width)+' '+str(-height)+')(stroke(width 0.254)(type default))(fill(type background)))'
 ps=[]
 for k,(pin,net) in enumerate(pins):
  yy=-(k+1)*pitch;label=pin+':'+net
  ps.append(f'(pin passive line(at -5.08 {yy} 0)(length 5.08)(name {q(label)} (effects(font(size 0.90 0.90))))(number {q(pin)} (effects(font(size 0.9 0.9)))))')
 libs.append(f'(symbol {q(lib)} (pin_names(offset 0.5))(in_bom yes)(on_board yes){prop}(symbol {q(name+"_0_1")}{body})(symbol {q(name+"_1_1")}{"".join(ps)}))')
 props=f'(property "Reference" {q(ref)} (at {x+2} {y-4} 0)(effects(font(size 1.27 1.27))(justify left)))'
 props+=f'(property "Value" {q(part["value"])} (at {x+2} {y-1} 0)(effects(font(size 1 1))(justify left)))'
 props+=f'(property "Footprint" {q(part["footprint"])} (at {x} {y} 0)(effects(font(size 1 1))(hide yes)))'
 pininst=''.join(f'(pin {q(pin)} (uuid {uid()}))' for pin,net in pins)
 instances.append(f'(symbol(lib_id {q(lib)})(at {x} {y} 0)(unit 1)(in_bom yes)(on_board yes)(dnp no)(uuid {uid()}){props}{pininst}(instances(project "RoomGuard_Baseboard_DRAFT"(path "/{rootid}"(reference {q(ref)})(unit 1)))))')
 for k,(pin,net) in enumerate(pins):
  xx=x-5.08;yy=y+(k+1)*pitch
  if net.startswith('NC'):
   wires.append(f'(no_connect(at {xx} {yy})(uuid {uid()}))');continue
  left=xx-5.08
  wires.append(f'(wire(pts(xy {xx} {yy})(xy {left} {yy}))(stroke(width 0)(type default))(uuid {uid()}))')
  wires.append(f'(label {q(net)} (at {left} {yy} 0)(effects(font(size 0.9 0.9))(justify right bottom))(uuid {uid()}))')
texts=[]
for x,y,t in [(20,15,'RoomGuard V1.1 BASEBOARD - REVIEW DRAFT - NOT FOR FABRICATION'),(20,23,'15 pins/side, pitch2.54 confirmed. Both ESP row spacings and module connector orders require measurement.'),(22,29,'POWER / VIN / VREF'),(202,29,'ANALOG BUFFER / DIVIDERS'),(390,29,'DIGITAL LEVEL ADAPTATION'),(20,222,'TWO SOCKETS - POPULATE ONE ESP ONLY'),(200,222,'MODULE SOCKETS - PIN ORDER PENDING'),(390,292,'TEST POINTS')]:
 texts.append(f'(text {q(t)} (at {x} {y} 0)(effects(font(size 1.4 1.4))(justify left bottom))(uuid {uid()}))')
sch='(kicad_sch(version 20250114)(generator "roomguard_draft")(uuid '+rootid+')(paper "A2")(title_block(title "RoomGuard Baseboard - MECHANICAL REVIEW REQUIRED")(rev "1.1-DRAFT"))(lib_symbols '+''.join(libs)+')'+''.join(texts+wires+instances)+')'
(H/'RoomGuard_Baseboard_DRAFT.kicad_sch').write_text(sch)
print('Circuit parts',len(parts),'schematic written; PCB is generated separately with pcbnew.')
