from pathlib import Path
from math import sin,cos,pi
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.xmlchemy import OxmlElement
from PIL import Image
import json

ROOT=Path(__file__).resolve().parent;OUT=ROOT;ART=ROOT.parent/'artifacts'
OUT.mkdir(exist_ok=True)
prs=Presentation();prs.slide_width=Inches(13.333);prs.slide_height=Inches(7.5)
prs.core_properties.title='RoomGuard 楼宇房间环境监测与异常声光告警系统｜竞赛汇报'
prs.core_properties.subject='中职学生竞赛展示 · 主讲与硬件操作双人配合'
prs.core_properties.author='项目指导团队'
C={'navy':'102C46','ink':'18354F','muted':'687F93','teal':'00A78F','mint':'DFF5EE','bg':'F3F6FA','white':'FFFFFF','line':'DCE5EC','orange':'F29A45','pale':'FFF0DE','red':'DC5560','pink':'FCE9EB','blue':'3F78D5','lightblue':'E8F0FC'}
notes=[]; titles=[];times=[]
def rgb(c):return RGBColor.from_string(C.get(c,c))
def rect(s,x,y,w,h,fill='white',line=None,r=0):
 sh=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if r else MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
 sh.fill.solid();sh.fill.fore_color.rgb=rgb(fill)
 if line:sh.line.color.rgb=rgb(line);sh.line.width=Pt(1)
 else:sh.line.fill.background()
 if r:
  try:sh.adjustments[0]=r
  except:pass
 return sh

def circle(s,x,y,d,fill='teal',line=None):
 sh=s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d));sh.fill.solid();sh.fill.fore_color.rgb=rgb(fill)
 if line:sh.line.color.rgb=rgb(line)
 else:sh.line.fill.background()
 return sh

def txt(s,x,y,w,h,text,size=18,color='ink',bold=False,align=None):
 box=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=box.text_frame;tf.clear();tf.word_wrap=True
 tf.margin_left=tf.margin_right=0;tf.margin_top=tf.margin_bottom=0
 for i,line in enumerate(str(text).split('\n')):
  p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.text=line;p.space_before=Pt(0);p.space_after=Pt(0);p.line_spacing=1.17
  if align is not None:p.alignment=align
  for run in p.runs:
   run.font.name='Microsoft YaHei';run.font.size=Pt(size);run.font.bold=bold;run.font.color.rgb=rgb(color)
   rp=run._r.get_or_add_rPr();rp.set('lang','zh-CN');rp.set('altLang','en-US');ea=OxmlElement('a:ea');ea.set('typeface','Microsoft YaHei');rp.append(ea)
 return box

def ln(s,x1,y1,x2,y2,color='line',width=1.5,dash=False):
 sh=s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,Inches(x1),Inches(y1),Inches(x2),Inches(y2));sh.line.color.rgb=rgb(color);sh.line.width=Pt(width)
 if dash:
  from pptx.enum.dml import MSO_LINE_DASH_STYLE
  sh.line.dash_style=MSO_LINE_DASH_STYLE.DASH
 return sh

def arrow(s,x,y,w=.45,color='teal'):
 sh=s.shapes.add_shape(MSO_SHAPE.CHEVRON,Inches(x),Inches(y),Inches(w),Inches(.22));sh.fill.solid();sh.fill.fore_color.rgb=rgb(color);sh.line.fill.background();return sh

def pill(s,x,y,w,label,fill='mint',color='teal',size=11):
 rect(s,x,y,w,.32,fill,r=.45);txt(s,x,y+.045,w,.23,label,size,color,True,PP_ALIGN.CENTER)

def icon(s,kind,x,y,z=.55,color='teal',bg=None):
 if bg:circle(s,x-.12,y-.12,z+.24,bg)
 def L(a,b,c,d):ln(s,x+a*z,y+b*z,x+c*z,y+d*z,color,2)
 def B(a,b,w,h):
  sh=rect(s,x+a*z,y+b*z,w*z,h*z,bg or 'white',color,r=.08);return sh
 if kind=='building':
  B(.15,.06,.7,.89)
  for yy in [.22,.43,.64]:
   for xx in [.29,.56]:rect(s,x+xx*z,y+yy*z,.12*z,.12*z,color)
  L(.05,.96,.95,.96)
 elif kind=='bell':
  L(.23,.63,.23,.36);L(.23,.36,.37,.17);L(.37,.17,.63,.17);L(.63,.17,.77,.36);L(.77,.36,.77,.63);L(.23,.63,.1,.78);L(.77,.63,.9,.78);L(.1,.78,.9,.78);L(.4,.94,.6,.94);L(.5,.04,.5,.17)
 elif kind=='wifi':
  for r in [.4,.25,.11]:
   last=None
   for j in range(13):
    a=pi*1.2+j*(pi*.6/12);pt=(.5+r*cos(a),.85+r*sin(a))
    if last:L(*last,*pt)
    last=pt
  circle(s,x+.45*z,y+.86*z,.10*z,color)
 elif kind=='screen':
  B(.04,.12,.92,.60);L(.5,.72,.5,.94);L(.28,.95,.72,.95)
 elif kind=='phone':B(.22,.03,.56,.94);L(.43,.85,.57,.85)
 elif kind=='server':
  for yy in [.08,.4,.72]:
   B(.12,yy,.76,.23);circle(s,x+.22*z,y+(yy+.08)*z,.065*z,color);L(.42,yy+.11,.73,yy+.11)
 elif kind=='sensor':
  B(.2,.2,.6,.6)
  for v in [.3,.5,.7]:L(v,.05,v,.2);L(v,.8,v,.95);L(.05,v,.2,v);L(.8,v,.95,v)
 elif kind=='clock':
  sh=s.shapes.add_shape(MSO_SHAPE.OVAL,Inches(x+.08*z),Inches(y+.08*z),Inches(.84*z),Inches(.84*z));sh.fill.background();sh.line.color.rgb=rgb(color);sh.line.width=Pt(2);L(.5,.25,.5,.53);L(.5,.53,.72,.62)
 elif kind=='check':L(.13,.5,.39,.77);L(.39,.77,.91,.19)
 elif kind=='doc':B(.17,.05,.66,.90);L(.3,.3,.68,.3);L(.3,.5,.68,.5);L(.3,.7,.6,.7)
 elif kind=='pin':
  sh=s.shapes.add_shape(MSO_SHAPE.TEAR,Inches(x+.17*z),Inches(y+.08*z),Inches(.64*z),Inches(.64*z));sh.rotation=135;sh.fill.solid();sh.fill.fore_color.rgb=rgb(color);sh.line.fill.background();circle(s,x+.38*z,y+.29*z,.2*z,bg or 'white')
 elif kind=='people':
  circle(s,x+.34*z,y+.05*z,.32*z,color);B(.18,.5,.64,.40)
 elif kind=='temp':
  B(.4,.08,.2,.60);circle(s,x+.25*z,y+.55*z,.5*z,color);rect(s,x+.465*z,y+.24*z,.07*z,.5*z,color)
 elif kind=='flame':
  sh=s.shapes.add_shape(MSO_SHAPE.TEAR,Inches(x+.2*z),Inches(y+.1*z),Inches(.6*z),Inches(.77*z));sh.rotation=225;sh.fill.solid();sh.fill.fore_color.rgb=rgb(color);sh.line.fill.background()
 elif kind=='db':
  sh=s.shapes.add_shape(MSO_SHAPE.CAN,Inches(x+.1*z),Inches(y+.05*z),Inches(.8*z),Inches(.9*z));sh.fill.solid();sh.fill.fore_color.rgb=rgb(bg or 'white');sh.line.color.rgb=rgb(color);sh.line.width=Pt(2)
 elif kind=='link':B(.02,.3,.4,.34);B(.58,.3,.4,.34);L(.3,.47,.7,.47)
 else:B(.16,.16,.68,.68);L(.3,.5,.7,.5)

def base(title,chapter,num,dark=False,subtitle=None):
 s=prs.slides.add_slide(prs.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=rgb('navy' if dark else 'bg')
 txt(s,.53,.28,8,.25,chapter,11,'teal' if not dark else 'B8E7E0',True)
 txt(s,10.6,.26,2.2,.3,'RoomGuard  /  V2.0',11,'muted' if not dark else 'A1B5C8',False,PP_ALIGN.RIGHT)
 if title:txt(s,.53,.85,12.2,.78,title,30,'white' if dark else 'ink',True)
 if subtitle:txt(s,.56,1.61,12,.42,subtitle,14,'muted' if not dark else 'B7C8D8')
 ln(s,.55,7.1,12.78,7.1,'line' if not dark else '2B465F',.7)
 txt(s,.55,7.19,10,.2,'楼宇房间环境监测与异常声光告警系统 · 比赛首版',9,'muted' if not dark else 'A1B5C8')
 txt(s,11.5,7.14,1.25,.25,(f'{num:02d} / 20' if num<=20 else f'备页 {num-20} / 4'),10,'muted' if not dark else 'A1B5C8',False,PP_ALIGN.RIGHT)
 titles.append(title);return s

def note(s,secs,script,ops='保持设备正常，关注主讲提示。',cue=''):
 n=f'建议时长：{secs}秒\nB同学｜展示讲解\n{script}\n\nA同学｜硬件操作\n{ops}\n\n配合提示\n{cue or "主讲结束本页后翻页；操作未完成时先确认状态。"}'
 s.notes_slide.notes_text_frame.text=n;notes.append(n);times.append(secs)

def cover_building(s,x,y):
 # Editable vector model: two rooms and one local alarm; no simulated physical test photo.
 rect(s,x,y,5.65,3.98,'193B57',r=.04);rect(s,x+.2,y+.2,5.25,.28,'284B66');txt(s,x+.4,y+.225,4,.2,'ROOMGUARD / BUILDING NETWORK',10,'A1B5C8',True)
 for i in range(2):
  xx=x+.35+i*2.55;fill='26465D' if i else '343C53';rect(s,xx,y+.78,2.35,2.52,fill,r=.04)
  pill(s,xx+.16,y+.95,.8,'101' if i==0 else '102','pink' if not i else 'mint','red' if not i else 'teal',15)
  for j in range(3):rect(s,xx+.18+j*.65,y+1.58,.48,.70,'38637C')
  icon(s,'sensor',xx+.25,y+2.55,.43,'B8D4E4',fill)
  icon(s,'bell',xx+1.48,y+2.48,.52,'red' if not i else 'teal',fill)
  txt(s,xx+.17,y+3.53,2.2,.25,'本地声光报警' if not i else '独立采集与上报',12,'B7C8D8')
 rect(s,x+.18,y+3.3,5.3,.10,'orange');ln(s,x+1.45,y+.65,x+4.05,y+.65,'teal',2)

def fit_pic(s,path,x,y,w,h,top=True):
 iw,ih=Image.open(path).size;sr=iw/ih;tr=w/h;pic=s.shapes.add_picture(str(path),Inches(x),Inches(y),width=Inches(w),height=Inches(h))
 if sr<tr:
  total=1-sr/tr;pic.crop_top=0 if top else total/2;pic.crop_bottom=total if top else total/2
 else:
  total=1-tr/sr;pic.crop_left=total/2;pic.crop_right=total/2
 return pic

def browser(s,path,x,y,w,h,label='实际软件界面 · 模拟数据'):
 rect(s,x,y,w,h,'white','line',.03);rect(s,x+.01,y+.01,w-.02,.30,'E5EDF4',r=.03)
 for i,col in enumerate(['red','orange','teal']):circle(s,x+.12+i*.15,y+.10,.07,col)
 txt(s,x+.7,y+.065,w-1,.2,label,9,'muted')
 fit_pic(s,path,x+.04,y+.33,w-.08,h-.38)


ROOT=Path(__file__).resolve().parent;OUT=ROOT;ART=ROOT.parent/'artifacts'
prs.core_properties.title='RoomGuard V2.0｜楼宇房间环境监测与异常声光告警系统'
def cards_slide(title,chapter,num,items,subtitle='',secs=25,script=''):
 s=base(title,chapter,num,subtitle=subtitle or None);n=len(items);w=(12.1-.22*(n-1))/n
 for i,(h,body,ic,col) in enumerate(items):
  x=.62+i*(w+.22);rect(s,x,2.28,w,3.92,'white',r=.05);icon(s,ic,x+.28,2.65,.58,col);txt(s,x+.28,3.58,w-.56,.82,h,23,'ink',True);txt(s,x+.28,4.63,w-.56,1.25,body,16,'muted')
 note(s,secs,script or title+'。'+''.join(a[0]+'，'+a[1].replace('\n','，')+'。' for a in items));return s
# 01
s=base('', '项目展示 / 从现场提醒到教师管理',1,True);txt(s,.65,1.20,6.6,1.8,'让异常被看见\n让管理更清楚',42,'white',True);txt(s,.69,3.23,6.1,.98,'楼宇房间环境监测\n与异常声光告警系统',24,'B9D2E4',True);cover_building(s,7.10,1.40)
for x,w,t in [(.7,1.6,'本地独立报警'),(2.48,1.6,'手机热点配网'),(4.27,1.6,'教师统一管理')]:pill(s,x,4.65,w,t,'234A61','BEEBE1',11)
txt(s,.72,5.42,6.1,.75,'学校：请填写\n讲解同学：请填写　硬件操作同学：请填写',14,'A1B5C8');txt(s,7.15,5.93,5.2,.4,'V2.0 · 可扩展节点 · 多终端同步',18,'white',True)
note(s,20,'各位评委老师好。我们的项目面向分散房间的环境监测与异常提醒。由我介绍方案，另一位同学配合硬件操作。新版重点增加了手机配网、节点自动接入和教师管理后台。','确认供电、预热、节点标签与终端连接；未通过实机测试的功能不演示为已验证。')
# 02
s=cards_slide('社会背景：分散房间，需要持续关注','01 社会背景与现实需求',2,[('校园楼宇','宿舍、教室、实训室分布分散\n管理人员难以同时在场\n环境状态需要持续可见','building','teal'),('现场人员','烟雾或火焰相关异常出现时\n需要就近声光提醒\n不能只等管理端发现','people','orange'),('管理与教学','既要看到异常在哪里\n也要便于配置、维护和复盘\n让学生掌握完整工程过程','doc','blue')],secs=25)
txt(s,.74,6.50,11.7,.3,'背景为典型应用场景分析，不引用未经核实的事故数量或市场统计。',11,'muted')
# 03
cards_slide('现实需求：现场、管理、教学，关注点不同','01 社会背景与现实需求',3,[('现场要及时提醒','房间自己判断异常\n蜂鸣器与灯光直接响应\n网络断开仍保留本地能力','bell','red'),('管理要准确定位','明确房间与异常原因\n区分离线、故障与正常\n知道谁确认、何时恢复','pin','teal'),('教师要易于操作','浏览器批准新设备\n统一设置参数与显示\n维护操作有权限和记录','screen','blue')],secs=25)
# 04
s=base('行业痛点：信息分散，接入与维护有门槛','01 痛点与项目回应',4,subtitle='针对教学及小规模楼宇场景中的不足，不笼统否定现有成熟产品。')
for i,(a,b,c) in enumerate([('巡查有间隔','持续采样 + 现场声光','clock'),('房间信息分散','集中展示 + 异常定位','pin'),('网络依赖风险','节点本地判断 + 离线识别','wifi'),('新增设备较繁琐','手机配网 + 教师批准 + 自动显示','sensor')]):
 y=2.18+i*1.0;rect(s,.65,y,12.0,.78,'white',r=.04);icon(s,c,.9,y+.17,.43,'orange');txt(s,1.75,y+.2,3.5,.38,a,22,'ink',True);arrow(s,5.24,y+.29,.45);txt(s,6.1,y+.2,6.0,.39,b,21,'teal',True)
note(s,25,'本项目不是说现有产品都没有这些能力，而是针对我们的小规模教学场景，把持续监测、房间定位、断网提醒和新设备接入整合起来，并降低教师使用与维护的门槛。')
# 05
cards_slide('项目目标：感知、提醒、管理、扩展形成闭环','02 系统目标',5,[('房间自主运行','温湿度采集展示\n烟雾或火焰触发报警\n断网继续本地判断','sensor','teal'),('中心统一管理','树莓派收集与存储\n教师配置节点和服务\n告警与操作可追溯','server','blue'),('新增无需改页面','唯一设备身份\n批准后绑定房间\n各终端动态生成内容','link','orange')],secs=20)
# 06 architecture
s=base('系统架构：房间现场与教师中心协同','02 整体架构',6,subtitle='局域网独立运行；配置、数据、告警与回执分别处理。')
for x,w in [(.62,2.75),(3.78,2.06),(6.25,2.86),(9.52,3.18)]:rect(s,x,2.25,w,3.92,'white',r=.04)
pill(s,.8,2.44,2.39,'ESP 房间节点');txt(s,.92,3.06,2.17,1.76,'ESP32 / ESP8266\n传感器与声光模块\n本地判断，5秒常规上报\n可按教师参数调整',16,'ink',True);txt(s,.91,5.25,2.2,.6,'手机连接节点热点\n完成网络与接入码配置',12,'muted')
icon(s,'wifi',4.42,3.1,.63,'blue');txt(s,3.98,4.15,1.7,.8,'MW305R\n2.4GHz Wi-Fi',16,'ink',True,PP_ALIGN.CENTER);txt(s,3.99,5.28,1.7,.3,'无需公网运行',12,'teal',True,PP_ALIGN.CENTER)
pill(s,6.47,2.44,2.42,'树莓派 3B');txt(s,6.53,3.16,2.30,1.95,'MQTT + 设备认证\n数据库 + 告警管理\n教师 Web 管理中心\n参数下发与执行回执',16,'ink',True);txt(s,6.53,5.49,2.3,.31,'服务、权限、备份与显示',12,'muted')
for j,(ic,t) in enumerate([('screen','监控大屏 / 轮播'),('screen','PC网页 / Windows EXE'),('phone','手机网页 / Android APK'),('people','教师 / 学生分权操作')]):icon(s,ic,9.77,3.04+j*.68,.37,'teal');txt(s,10.39,3.06+j*.68,2.1,.36,t,13,'ink',True)
for x in [3.42,5.89,9.16]:arrow(s,x,4.05,.30)
note(s,35,'数据从房间节点经过路由器进入树莓派。节点负责本地报警，树莓派负责集中管理。教师后台批准设备、分配房间和参数，再把显示方案分发给终端。管理员的控制指令必须有回执，不能把已发送当作已执行。')
# 07
cards_slide('节点硬件：五类模块，各自承担明确任务','02 感知与输出',7,[('温湿度与气体','DHT11：只采集展示\nMQ-2：响应趋势与阈值状态\n未经标定不输出准确 ppm','temp','blue'),('火焰与声光','火焰模块：参与异常判断\n有源蜂鸣器：低电平触发\nRGB：正常绿、异常红闪','bell','red'),('接口与供电','5V模块必须电平适配\n两种板分别规划GPIO与ADC\n基板尺寸与电气仍待实测','sensor','orange')],secs=25)
# 08
s=cards_slide('通用程序：同一源码，两种芯片分别编译','03 Arduino 烧录与手机配网',8,[('ESP32 固件','同型号节点使用同一份程序\n设备身份由芯片MAC生成\n不再为每个房间改源码','sensor','teal'),('ESP8266 固件','统一业务逻辑与配置页面\n使用对应芯片的编译目标\n不能与ESP32共用同一个BIN','sensor','blue'),('手机配置','Android 5.1浏览器可访问\n连接节点加密配置热点\n手动打开192.168.4.1','phone','orange')],secs=30)
txt(s,.74,6.49,11.8,.3,'首次仍通过 USB＋Arduino IDE 烧录；配网不等于无线更新固件。',12,'muted')
# 09
s=base('新增节点：配网、批准、绑定，终端自动出现','03 新设备接入流程',9)
for i,(h,b) in enumerate([('教师生成接入码','有效10分钟\n绑定一台设备'),('手机配置节点','输入Wi-Fi与服务器IP\n填写教师接入码'),('教师批准并绑定','查看设备型号与编号\n分配楼层和房间'),('所有终端更新','动态卡片、统计、筛选\n无需改网页或重打客户端')]):
 x=.62+i*3.14;rect(s,x,2.5,2.87,2.95,'white',r=.04);pill(s,x+.25,2.77,.48,str(i+1));txt(s,x+.25,3.47,2.37,.77,h,22,'ink',True);txt(s,x+.25,4.41,2.37,.68,b,15,'muted')
 if i<3:arrow(s,x+2.92,3.71,.15)
rect(s,.66,5.83,12.0,.63,'navy',r=.05);txt(s,.91,6.0,11.4,.32,'已登记设备自动重连；陌生设备不会因为连上同一路由器就自动获得管理权限。',17,'white',True)
note(s,30,'教师先生成有时效的接入码，学生用手机连接ESP热点，填写网络、树莓派地址和接入码。节点提交申请后，教师批准并绑定房间。系统发放独立凭据，随后网页、EXE和APK读取同一清单自动展示。')
# 10
s=base('教师后台：让日常管理从命令行走向网页','04 教师操作中心',10,subtitle='节点接入、参数、账号权限、显示方案、服务与备份集中操作。');browser(s,ART/'V2_教师节点管理.png',.62,2.15,8.65,4.55)
for j,(h,b) in enumerate([('设备管理','批准 / 绑定 / 停用'),('参数同步','期望版本与实际生效'),('权限分工','教师 / 学生 / 只读')]):txt(s,9.63,2.6+j*1.15,2.9,.40,h,23,'teal',True);txt(s,9.63,3.11+j*1.15,2.9,.45,b,15,'muted')
note(s,30,'这是教师管理页面的实际软件截图，使用的是模拟节点。教师可以批准和绑定设备，调整参数，查看版本是否已经生效，也能分配学生操作权限。截图不是已经完成实物部署的证明。')
# 11
s=base('报警机制：现场判断先于网络通知','05 本地声光报警',11)
for j,(ic,t,col) in enumerate([('sensor','烟雾阈值触发','orange'),('flame','火焰信号触发','red')]):
 y=2.54+j*1.17;rect(s,.63,y,2.8,.8,'white',r=.05);icon(s,ic,.85,y+.18,.4,col);txt(s,1.5,y+.21,1.8,.4,t,18,'ink',True)
ln(s,3.45,2.94,3.88,2.94,'teal',2);ln(s,3.45,4.11,3.88,4.11,'teal',2);ln(s,3.88,2.94,3.88,4.11,'teal',2);arrow(s,4.03,3.4,.4);circle(s,4.58,3.02,.98);txt(s,4.58,3.27,.98,.4,'或',25,'white',True,PP_ALIGN.CENTER);arrow(s,5.73,3.4,.4)
rect(s,6.32,2.60,2.72,2.06,'navy',r=.05);icon(s,'sensor',7.37,2.90,.6,'BEEBE1','navy');txt(s,6.58,3.77,2.2,.58,'节点独立判断\n持续异常保持告警',16,'white',True,PP_ALIGN.CENTER);arrow(s,9.2,3.4,.35);rect(s,9.73,2.60,2.92,2.06,'pink',r=.05);icon(s,'bell',10.91,2.88,.6,'red','pink');txt(s,10.0,3.76,2.38,.6,'蜂鸣器 + 红灯\n提醒房间周围人员',16,'red',True,PP_ALIGN.CENTER)
txt(s,.76,5.48,11.6,.8,'温湿度仅上报展示，不触发环境报警。\n异常发生、原因变化和恢复即时上报；不必等待下一轮常规数据。',20,'ink',True)
note(s,25,'烟雾或火焰任一有效触发，本地就会启动声光报警，两项同时触发显示两个原因。温湿度不参与报警。网络用于通知和管理，不是启动本地报警的必要条件。')
# 12
s=cards_slide('告警闭环：确认、消音、解除分开处理','05 告警生命周期',12,[('确认','表示已经看到\n记录操作人和时间\n不清除持续异常','doc','blue'),('本次消音','关闭当前事件蜂鸣器\n红灯和异常状态保留\n新增原因重新鸣叫','bell','orange'),('稳定解除','所有原因恢复正常\n连续稳定N秒后解除\nN默认10秒、教师可配置','check','teal')],secs=25)
txt(s,.74,6.5,11.9,.3,'指令无执行回执不能宣称成功；离线节点不排队执行过期消音。',12,'muted')
# 13
cards_slide('断网与恢复：现场继续，中心明确标记','05 故障与恢复',13,[('房间仍报警','传感器和声光由ESP控制\n不会等待树莓派命令\n网络尝试与采集分开调度','bell','red'),('中心显示离线','默认5秒常规上报\n约20秒无有效消息判离线\n保留最后数据与异常状态','clock','orange'),('重连报当前状态','连接恢复后自动上报\n参数按版本重新同步\n首版不补完整断网历史','link','teal')],secs=25)
# 14
s=base('自适应终端：新增节点，不再固定两张卡片','06 动态展示',14,subtitle='统计、卡片、历史选项与参数列表来自同一设备清单。');browser(s,ART/'V2_四节点自动显示.png',.62,2.17,8.2,4.5);rect(s,9.16,2.17,1.86,4.5,'navy',r=.09);fit_pic(s,ART/'V2_手机显示.png',9.28,2.39,1.62,4.06);txt(s,11.26,2.67,1.43,1.2,'电脑\n手机\n大屏',23,'teal',True);txt(s,11.23,4.28,1.5,1.75,'EXE与APK\n复用业务接口\n页面适配屏幕\n异常优先展示',13,'muted');note(s,25,'新增节点批准后，卡片、统计和查询选项自动更新，不再固定为两个房间。电脑和手机使用适合各自屏幕的布局；大屏按教师设定分页，避免节点一多就把字缩得很小。')
# 15
s=base('终端设置：教师统一方案，本机保留必要授权','06 显示方案与轮播',15);browser(s,ART/'V2_教师终端设置.png',.62,2.17,8.23,4.50)
txt(s,9.24,2.5,3.4,.5,'可统一配置',25,'teal',True);txt(s,9.25,3.16,3.35,1.72,'标题 / 主题 / 字号\n楼层与房间范围\n显示字段与历史窗口\n每页数量 / 轮播 / 刷新',18,'ink');txt(s,9.25,5.23,3.35,1.01,'声音仍需浏览器授权\nAPK后台仍需系统许可\n显示方案不是保密访问控制',13,'muted');note(s,25,'教师可给不同终端分配不同方案，例如大厅大屏按楼层轮播，手机只看负责的房间。方案会自动拉取。但树莓派不能绕过浏览器声音授权，也不能替手机关闭系统省电限制。')
# 16
cards_slide('数据价值：不只看当前，还能回看处理过程','07 数据与追溯',16,[('环境历史','默认采样保留30天\n按房间和时间查询曲线\n导出CSV便于整理','db','blue'),('告警与审计','事件默认保留180天\n记录确认、消音和恢复\n维护操作有操作者与结果','doc','teal'),('位置变化有记录','设备ID保持稳定\n房间绑定可以调整\n采样保留当时房间信息','pin','orange')],secs=25)
# 17
s=base('服务维护：可操作，但有边界、有记录','07 教师维护与恢复',17);browser(s,ART/'V2_教师服务管理.png',.62,2.17,8.3,4.5);txt(s,9.28,2.55,3.25,.5,'受限维护入口',24,'teal',True);txt(s,9.28,3.22,3.24,1.66,'指定服务启动 / 停止 / 重启\n脱敏日志与磁盘状态\n一致性备份与受控恢复\n校时、保留期限与账号',16,'ink');txt(s,9.28,5.31,3.24,.95,'不提供任意命令执行\n业务服务不以root运行\n页面不可达时保留SSH恢复',13,'muted');note(s,25,'教师可以维护指定业务服务和MQTT代理，查看日志、备份与恢复。所有操作都受权限和白名单限制。重启业务服务可能让页面断开，所以排队成功不等于执行成功，要在重连后看维护结果。')
# 18
s=cards_slide('双人演示：一人操作，一人解释状态变化','08 现场演示与分工',18,[('场景一：正常监测','A：指认两个房间和模块\nB：说明设备ID与房间绑定\n观察数据归属与在线状态','sensor','teal'),('场景二：异常处置','A：受控触发测试异常\nB：确认、消音并解释区别\n观察红灯保留和恢复计时','bell','red'),('场景三：扩展或断网','A：按排练步骤配网／断网\nB：展示批准、自动出现与离线\n结束后恢复正常连接','wifi','orange')],secs=120)
notes[-1]+='\n操作提醒：新增和断网按赛时取舍；只有两个实物节点时，扩展采用明确标识的模拟演示或日志证据，不能冒充第三块实物。断网保持节点供电；真实传感器与数字测试输入必须分清。'
s.notes_slide.notes_text_frame.text=notes[-1]
# 19
s=base('验证结果：软件证据与整机验收分开说明','08 测试与边界',19)
rect(s,.63,2.25,5.94,3.92,'white',r=.05);rect(s,6.84,2.25,5.85,3.92,'white',r=.05);pill(s,.92,2.51,2.3,'已完成的软件验证');pill(s,7.13,2.51,2.3,'仍需目标机实测','pale','orange')
for j,t in enumerate(['两种Arduino目标编译通过','自动注册、权限、显示配置自动测试','本机真实MQTT代理多节点联调','教师后台与自适应页面浏览器测试']):icon(s,'check',.96,3.2+j*.60,.25);txt(s,1.48,3.17+j*.60,4.73,.43,t,17,'ink')
for j,t in enumerate(['树莓派ARM64首次部署与系统维护','手机实际连接ESP热点与无线稳定性','供电、电平、预热、物理触发与长测','Windows与OPPO后台／锁屏验收']):circle(s,7.2,3.32+j*.60,.07,'orange');txt(s,7.48,3.17+j*.60,4.88,.43,t,17,'ink')
txt(s,.74,6.52,11.8,.3,'截图为实际软件的模拟数据；系统维护提权助手未在用户树莓派执行，不将其写成整机终验通过。',11,'muted');note(s,25,'我们按证据报告结果。固件编译、自动测试、真实本机消息代理联调和浏览器流程已经验证。树莓派、真实配网、电气以及指定手机后台仍要实测。未做过的项目明确列为待验收，不把模拟数据当真实环境。')
# 20
s=base('项目效益：让现场有提醒，让管理有依据','09 价值与下一步',20,True)
for i,(h,b,ic,col) in enumerate([('现场与管理','就近声光提醒，房间定位清楚\n历史可查，确认与处置有记录','bell','orange'),('部署与教学','复用局域网、浏览器与现有板卡\n训练接线、烧录、联调、维护与表达','people','BEEBE1')]):
 y=2.3+i*1.7;icon(s,ic,.95,y+.15,.65,col,'navy');txt(s,2.0,y,3.2,.48,h,27,'white',True);txt(s,5.4,y+.04,6.7,.93,b,21,'B7C8D8')
txt(s,.94,6.0,11.6,.58,'下一步：完成整机实测，再完善离线补传与时间保持。汇报完毕，请老师指导。',20,'BEEBE1',True);note(s,20,'项目的预期效益是增加现场提醒，让管理信息更清楚，也让学生训练完整工程技能。我们不编造成本节省和事故降低比例。本系统是教学演示原型，不替代合规消防设施。下一步先把实机验收做完整。','恢复设备到正常或已明确说明的状态。')
# 21-24 backups
cards_slide('答辩备页｜为什么不能让两种ESP共用同一BIN？','补充 / 芯片与固件',21,[('公共业务源码','统一通信、告警与配置逻辑\n设备ID与房间不编译绑定\n同型号节点可共用程序','doc','teal'),('分别编译目标','ESP32与ESP8266架构不同\n启动、驱动、引脚和内存不同\n必须选对芯片固件','sensor','blue'),('配网不是OTA','USB首次烧录仍需要\n手机负责网络与接入配置\n本版不提供无线固件升级','phone','orange')],secs=0)
cards_slide('答辩备页｜5V模块与通用基板怎样处理？','补充 / 电气与机械',22,[('电平与ADC','MQ AO分别缓冲与分压\nDO经过适合的电平适配\n软件比例对应实物电路','sensor','teal'),('供电与参考','模块5V与3.3V分区\n不并联两个稳压器输出\nUSB烧录按手册取下板卡','link','blue'),('基板尚未定稿','已知每侧15针、针距2.54mm\n两排针中心距仍待测\n当前未布线，不可直接打板','doc','orange')],secs=0)
cards_slide('答辩备页｜安全与权限怎样落实？','补充 / 接入与授权',23,[('新设备接入','有时效接入码绑定一台设备\n教师批准后独立MQTT凭据\n不使用共享默认接入密码','sensor','teal'),('操作权限','教师管理全局\n学生只操作授权节点\n只读展示不提供控制权限','people','blue'),('系统维护','限制服务、路径和操作类型\n保留审计与SSH恢复\n可信局域网，非公网安全方案','server','orange')],secs=0)
cards_slide('答辩备页｜还存在哪些边界？','补充 / 后续完善',24,[('离线数据','本地报警继续\n重连上报当前状态\n完整事件缓存补传待完善','wifi','teal'),('旧手机后台','需要原生APK与系统许可\n断网或被强停不能保证新告警\n指定OPPO必须真机验收','phone','blue'),('规模与应用','自适应不代表无限容量\n按树莓派负载逐步测试\n教学原型不替代正式消防','building','orange')],secs=0)
# Modest genuine slide animations: fade transitions, manual advance only.
for i,slide in enumerate(prs.slides,1):
 if i>20:slide._element.set('show','0')
 for sh in slide.shapes:
  if hasattr(sh._element,'spPr'):
   sh._element.spPr.append(OxmlElement('a:effectLst'))
   for ref in sh._element.iter():
    if ref.tag.endswith('}effectRef'):ref.set('idx','0')
 tr=OxmlElement('p:transition');tr.set('spd','med');tr.set('advClick','1');tr.append(OxmlElement('p:fade'));slide._element.append(tr)
 # Slightly more explanatory content than the prior edition; no time-based slide advances.
file=OUT/'RoomGuard_V2_竞赛展示_教师后台与自适应节点.pptx';prs.save(file)
(ROOT/'逐页讲稿.json').write_text(json.dumps([{'page':i+1,'title':titles[i],'seconds':times[i],'notes':notes[i]} for i in range(len(titles))],ensure_ascii=False,indent=2))
print(file,len(prs.slides),'slides; main',sum(times[:20]),'seconds')
