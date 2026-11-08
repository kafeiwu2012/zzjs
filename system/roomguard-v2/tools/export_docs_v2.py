from pathlib import Path
from xml.sax.saxutils import escape
from docx import Document
from docx.shared import Pt,Cm
from docx.oxml.ns import qn
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
R=Path(__file__).resolve().parents[1];pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
normal=ParagraphStyle('cn',fontName='STSong-Light',fontSize=10,leading=16,wordWrap='CJK',spaceAfter=6);head=ParagraphStyle('h',parent=normal,fontSize=15,leading=22,spaceBefore=12,spaceAfter=8);title=ParagraphStyle('t',parent=head,fontSize=20,leading=28);cell=ParagraphStyle('cell',parent=normal,fontSize=8,leading=12);code=ParagraphStyle('code',parent=normal,fontSize=8.5,leading=13,backColor=colors.HexColor('#EDF3F8'),leftIndent=6,spaceAfter=0)
for f in sorted((R/'docs').glob('*_V2.md')):
 D=Document();sec=D.sections[0];sec.top_margin=sec.bottom_margin=Cm(1.8)
 for n in ['Normal','Title','Heading 1','Heading 2','Heading 3']:
  st=D.styles[n];st.font.name='Microsoft YaHei';st.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Microsoft YaHei')
 D.styles['Normal'].font.size=Pt(10);story=[];lines=f.read_text().splitlines();i=0;fenced=False
 while i<len(lines):
  line=lines[i]
  if line.startswith('```'):fenced=not fenced;i+=1;continue
  if fenced:D.add_paragraph(line,'No Spacing');story.append(Paragraph(escape(line or ' '),code));i+=1;continue
  if not line.strip():story.append(Spacer(1,3));i+=1;continue
  if line.startswith('|'):
   rows=[]
   while i<len(lines) and lines[i].startswith('|'):
    row=[x.strip() for x in lines[i].strip('|').split('|')]
    if not all(set(x)<=set('-: ') for x in row):rows.append(row)
    i+=1
   tab=D.add_table(rows=1,cols=len(rows[0]));tab.style='Light Shading Accent 1'
   for j,x in enumerate(rows[0]):tab.rows[0].cells[j].text=x
   for row in rows[1:]:
    cc=tab.add_row().cells
    for j,x in enumerate(row):cc[j].text=x
   widths=[495/len(rows[0])]*len(rows[0])
   if len(rows[0])==2:widths=[150,345]
   t=Table([[Paragraph(escape(x),cell) for x in row] for row in rows],colWidths=widths,repeatRows=1);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DFF4EF')),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#C7D6E2')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.extend([t,Spacer(1,8)]);continue
  if line.startswith('#'):
   level=len(line)-len(line.lstrip('#'));text=line[level:].strip();D.add_heading(text,0 if level==1 else min(level-1,3));story.append(Paragraph(escape(text),title if level==1 else head))
  else:D.add_paragraph(line);story.append(Paragraph(escape(line),normal))
  i+=1
 sec.footer.paragraphs[0].text='RoomGuard V2.0 · 实物与系统维护以目标机验收记录为准'
 D.save(f.with_suffix('.docx'))
 def page(c,doc):c.setFont('STSong-Light',9);c.drawRightString(550,24,f'RoomGuard V2.0 | {doc.page}')
 SimpleDocTemplate(str(f.with_suffix('.pdf')),pagesize=(595.28,841.89),leftMargin=50,rightMargin=50,topMargin=42,bottomMargin=40).build(story,onFirstPage=page,onLaterPages=page)
 print(f.stem)
