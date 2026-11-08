"""KiCad9 pcbnew: placement only. Dimensions remain unverified; no tracks/Gerbers."""
import pcbnew as P
from pathlib import Path
import json,os
R=Path(__file__).resolve().parents[1];H=R/'hardware';data=json.loads((H/'circuit_source.json').read_text());b=P.BOARD()
mm=P.FromMM
netmap={}
for p in data['parts']:
 for n in p['pins'].values():
  if n.startswith('NC'):continue
  if n not in netmap:
   item=P.NETINFO_ITEM(b,n);b.Add(item);netmap[n]=item

def text(t,x,y,size=1,layer=P.F_SilkS):
 a=P.PCB_TEXT(b);a.SetText(t);a.SetPosition(P.VECTOR2I(mm(x),mm(y)));a.SetTextSize(P.VECTOR2I(mm(size),mm(size)));a.SetTextThickness(mm(.15));a.SetLayer(layer);b.Add(a)
def line(x1,y1,x2,y2,layer=P.Edge_Cuts):
 a=P.PCB_SHAPE();a.SetShape(P.SHAPE_T_SEGMENT);a.SetStart(P.VECTOR2I(mm(x1),mm(y1)));a.SetEnd(P.VECTOR2I(mm(x2),mm(y2)));a.SetWidth(mm(.1 if layer==P.Edge_Cuts else .15));a.SetLayer(layer);b.Add(a)
# Reference outline only. Unknown row spacing is intentionally visible on the drawing.
for pts in [(20,20,200,20),(200,20,200,150),(200,150,20,150),(20,150,20,20)]:line(*pts)
slot={'J7':(36,30),'J8':(61.4,30),'J9':(36,94),'J10':(61.4,94)}
modules={'J2':(160,40),'J3':(160,60),'J4':(160,80),'J5':(160,100),'J6':(160,120)}
power={'J1':(92,28),'F1':(104,28),'Q1':(116,28),'R1':(125,28),'SW1':(138,28),'U1':(92,50),'JP1':(92,70),'JP2':(112,70),'JP3':(126,70)}
counts={}
for p in data['parts']:
 name=p['footprint'];lib,fpname=name.split(':',1);fp=P.FootprintLoad('/usr/share/kicad/footprints/'+lib+'.pretty',fpname)
 if fp is None:raise RuntimeError(name)
 ref=p['ref'];g=p['group'];idx=counts.get(g,0);counts[g]=idx+1
 if ref in slot:x,y=slot[ref]
 elif ref in modules:x,y=modules[ref]
 elif ref in power:x,y=power[ref]
 elif g=='power':x,y=90+(idx%4)*12,38+(idx//4)*8
 elif g=='analog':x,y=90+(idx%4)*12,88+(idx//4)*10
 elif g=='logic':x,y=90+(idx%5)*12,118+(idx//5)*7
 else:x,y=175+(idx%2)*10,30+(idx//2)*20
 fp.SetReference(ref);fp.SetValue(p['value']);fp.SetPosition(P.VECTOR2I(mm(x),mm(y)))
 fp.Reference().SetTextSize(P.VECTOR2I(mm(.8),mm(.8)));fp.Reference().SetTextThickness(mm(.12));fp.Value().SetVisible(False)
 for pad in fp.Pads():
  n=p['pins'].get(pad.GetNumber())
  if n in netmap:pad.SetNet(netmap[n])
 b.Add(fp)
text('DRAFT - NOT FOR FABRICATION - NO ROUTING',110,23,1.3,P.Dwgs_User)
text('ESP32: 15x2 / pitch2.54',49,71,1,P.Dwgs_User);text('ESP8266: 15x2 / pitch2.54',49,137,1,P.Dwgs_User)
text('ROW SPACING25.4 IS PLACEHOLDER',49,75,.8,P.Dwgs_User)
text('FIT ONE ESP ONLY',47,82,1.2,P.F_SilkS)
text('USB: REMOVE ESP FROM BASE FIRST',113,146,.9,P.Dwgs_User)
text('MODULE PIN ORDER / BODY SIZE UNVERIFIED',160,138,.8,P.Dwgs_User)
for y in [25,89]:
 for pts in [(27,y,71,y),(71,y,71,y+7),(71,y+7,27,y+7),(27,y+7,27,y)]:line(*pts,layer=P.Dwgs_User)
 text('ANTENNA: NO COPPER / NO METAL',49,y+3,.7,P.Dwgs_User)
P.SaveBoard(str(H/'RoomGuard_Baseboard_DRAFT.kicad_pcb'),b)
print('PCB footprints',len(b.GetFootprints()),'tracks',len(b.GetTracks()),'status UNROUTED REVIEW DRAFT')
