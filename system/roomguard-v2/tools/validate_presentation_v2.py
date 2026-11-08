"""Validate rendered text and notes; export architecture and slide contact sheets."""
from pathlib import Path
import fitz,json,re,unicodedata
from pptx import Presentation
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];P=R/'presentation'
ppt=P/'RoomGuard_V2_竞赛展示_教师后台与自适应节点.pptx';pdf=ppt.with_suffix('.pdf')
prs=Presentation(ppt);doc=fitz.open(pdf);assert len(prs.slides)==len(doc)==24
norm=lambda s:re.sub(r'\s+','',unicodedata.normalize('NFKC',s))
missing=[]
for i,s in enumerate(prs.slides):
 text=norm(doc[i].get_text())
 for sh in s.shapes:
  if not sh.has_text_frame:continue
  for para in sh.text_frame.paragraphs:
   label=norm(para.text)
   if label and label not in text:missing.append({'page':i+1,'text':para.text})
 assert s.has_notes_slide and '同学' in s.notes_slide.notes_text_frame.text
 assert s._element.get('show','1')==('1' if i<20 else '0')
 assert s._element.find('{http://schemas.openxmlformats.org/presentationml/2006/main}transition') is not None
assert not missing,missing
for group in range(2):
 sheet=Image.new('RGB',(1600,780),'#e5ebf2');d=ImageDraw.Draw(sheet)
 for local in range(12):
  idx=group*12+local;pix=doc[idx].get_pixmap(matrix=fitz.Matrix(.4,.4),alpha=False)
  img=Image.frombytes('RGB',[pix.width,pix.height],pix.samples);img.thumbnail((388,225))
  x=6+(local%4)*400;y=6+(local//4)*260;sheet.paste(img,(x,y));d.text((x+4,y+232),str(idx+1),fill='#18354f')
 sheet.save(P/f'总览{group+1}.png')
architecture=fitz.open();architecture.insert_pdf(doc,from_page=5,to_page=5);architecture.save(R/'docs/系统架构图_V2.pdf')
doc[5].get_pixmap(matrix=fitz.Matrix(2,2),alpha=False).save(R/'docs/系统架构图_V2.png')
report={'ppt_pages':24,'pdf_pages':24,'main_pages':20,'hidden_backup_pages':4,'notes_all_present':True,'fade_transitions':True,'missing_rendered_text':missing}
(P/'PPT检查.txt').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
