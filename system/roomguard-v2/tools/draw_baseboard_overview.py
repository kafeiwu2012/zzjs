from pathlib import Path
from xml.sax.saxutils import escape
r=Path(__file__).resolve().parents[1]
s=['''<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="1050" viewBox="0 0 1400 1050"><defs><marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8z" fill="#3773bc"/></marker></defs><rect width="1400" height="1050" fill="#f4f7fb"/><style>text{font-family:"Noto Sans CJK SC","Microsoft YaHei",sans-serif;fill:#16364f}.title{font-size:29px;font-weight:bold}.h{font-size:21px;font-weight:bold}.t{font-size:18px}.small{font-size:15px}.wire{stroke:#3773bc;stroke-width:3;fill:none;marker-end:url(#arr)}</style>''']
def text(x,y,t,style='t'):s.append(f'<text x="{x}" y="{y}" class="{style}">{escape(t)}</text>')
def box(x,y,w,h,fill='#ffffff'):s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="#d7e2ed" stroke-width="2"/>')
def arrow(x1,y1,x2,y2):s.append(f'<path class="wire" d="M{x1} {y1}L{x2} {y2}"/>')
text(40,50,'RoomGuard V1.1 通用基板｜电源与接口方案','title');text(40,85,'两块 ESP 均为每侧15针、间距2.54mm；两排针中心距及模块尺寸仍待实测。','small')
box(35,115,1330,145);text(60,151,'① 外部供电','h')
for x,w,title,sub in [(65,210,'稳压5V输入','J1：+5V / GND'),(340,290,'PTC＋反接保护','F1 / AO3401A'),(695,210,'总电源开关','SW1'),(970,350,'P5V 电源母线','开发板VIN / MQ-2 / 蜂鸣器')]:
 box(x,168,w,65,'#e8f1fc');text(x+15,192,title);text(x+15,220,sub,'small')
for a,b in [(275,340),(630,695),(905,970)]:arrow(a+5,200,b-10,200)
box(35,285,650,235);text(60,325,'② 两种 ESP 插座：每板只安装一块','h')
box(65,350,270,100,'#e8f6f2');text(85,390,'ESP32：101 房间','h');text(85,425,'独立VIN与3V3引出','small')
box(360,350,290,100,'#e8f6f2');text(380,390,'ESP8266：102 房间','h');text(380,425,'A0量程须核验','small')
text(68,490,'JP1选择 ESP_3V3；JP2/JP3只使能所选开发板VIN。','small')
box(715,285,650,235);text(740,325,'③ 独立3.3V传感器电源','h')
box(745,355,240,90,'#fff1de');text(765,389,'AP2112K-3.3','h');text(765,422,'输入P5V，输出SENSOR_3V3','small')
arrow(1000,398,1060,398);text(1080,385,'DHT11 / 火焰模块');text(1080,419,'传感器侧上拉','small')
text(748,490,'不把 SENSOR_3V3 与开发板自身3V3稳压器输出并联。','small')
box(35,550,1330,315);text(60,591,'④ 按信号类型分别适配，保持软件与硬件一致','h')
entries=[('MQ-2 AO','MCP6002 缓冲 → 两路分压','ESP32：20k/10k，比例3.0；ESP8266：56k/10k，比例6.6'),('MQ DO / 火焰 DO','SN74LVC2G17：5V容忍输入 → ESP参考电平','非反相、Ioff；输出供电来自所选ESP_3V3'),('DHT DATA / 蜂鸣器 I/O','BSS138：分别适配双向数据／低触发控制','两侧上拉到各自电源；模块输入电流、时序须实测'),('RGB 三色模块','共阴极接口＋各通道330Ω保护电阻','GPIO映射一致，实际亮度与电流核验后定稿')]
for i,(a,b,c) in enumerate(entries):
 y=622+i*56;text(65,y,a,'h');text(360,y,b);text(360,y+24,c,'small')
box(35,891,1330,115,'#fff1de');text(60,928,'工程状态：原理图＋未布线布局草案，不是可制造PCB。','h');text(60,966,'USB烧录须把ESP取下单独连接；尺寸、脚序、电压、热与时序验收后，再进行布线、ERC/DRC和打板定稿。','small')
s.append('</svg>');(r/'hardware/基板功能与电源图.svg').write_text(''.join(s))
