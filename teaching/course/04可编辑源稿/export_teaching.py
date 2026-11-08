"""Export the teaching Markdown to editable Word and printable PDF."""
from pathlib import Path
import re
from xml.sax.saxutils import escape
from docx import Document
from docx.shared import Pt,Cm,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image,KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
R=Path(__file__).resolve().parent
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
navy=colors.HexColor('#18354F');teal=colors.HexColor('#008E7D')
styles={
 'normal':ParagraphStyle('cn',fontName='STSong-Light',fontSize=10.5,leading=17,wordWrap='CJK',spaceAfter=7,textColor=navy),
 'title':ParagraphStyle('title',fontName='STSong-Light',fontSize=25,leading=35,spaceAfter=16,textColor=navy),
 'h2':ParagraphStyle('h2',fontName='STSong-Light',fontSize=15,leading=23,spaceBefore=14,spaceAfter=9,textColor=teal,keepWithNext=True),
 'h3':ParagraphStyle('h3',fontName='STSong-Light',fontSize=14,leading=22,spaceBefore=12,spaceAfter=8,textColor=navy,keepWithNext=True),
 'cell':ParagraphStyle('cell',fontName='STSong-Light',fontSize=9,leading=14,wordWrap='CJK',textColor=navy),
 'cellhead':ParagraphStyle('cellhead',fontName='STSong-Light',fontSize=9,leading=14,wordWrap='CJK',textColor=colors.white),
 'code':ParagraphStyle('code',fontName='STSong-Light',fontSize=9,leading=14,wordWrap='CJK',backColor=colors.HexColor('#EEF3F8'),leftIndent=7,rightIndent=7,spaceAfter=0),
}
def clean(s):return s.replace('`','').replace('**','')
def para(s,style='normal'):return Paragraph(escape(clean(s)),styles[style])
def shading(cell,fill):
 tcpr=cell._tc.get_or_add_tcPr();v=OxmlElement('w:shd');v.set(qn('w:fill'),fill);tcpr.append(v)
def layout(D):
 sec=D.sections[0];sec.page_width=Cm(21);sec.page_height=Cm(29.7);sec.top_margin=Cm(1.8);sec.bottom_margin=Cm(1.7);sec.left_margin=sec.right_margin=Cm(1.8)
 for name in ['Normal','Title','Heading 1','Heading 2','Heading 3','No Spacing']:
  st=D.styles[name];st.font.name='Microsoft YaHei';st.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Microsoft YaHei');st.font.color.rgb=RGBColor.from_string('18354F')
 D.styles['Normal'].font.size=Pt(10.5);D.styles['Normal'].paragraph_format.line_spacing=1.25;D.styles['Normal'].paragraph_format.space_after=Pt(7)
 D.styles['Title'].font.size=Pt(26)
 for name in ['Heading 1','Heading 2']:D.styles[name].font.color.rgb=RGBColor.from_string('008E7D')
 sec.header.paragraphs[0].text='RoomGuard V2  |  中职竞赛项目教学'
 sec.header.paragraphs[0].style=D.styles['Caption']
 foot=sec.footer.paragraphs[0];foot.text='教师指导 · 学生实操 · 过程证据    |    '
 fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');foot._p.append(fld)
 for run in foot.runs:run.font.size=Pt(8);run.font.color.rgb=RGBColor.from_string('6A8096')
 D.core_properties.author='RoomGuard 项目教学';D.core_properties.subject='36学时项目化教学与双人竞赛训练'

def export(path):
 D=Document();layout(D);story=[];lines=path.read_text().splitlines();i=0;fenced=False;title=''
 is_teacher=path.name.startswith('教师项目化');is_workbook=path.name.startswith('学生学习')
 while i<len(lines):
  s=lines[i]
  if s.startswith('```'):fenced=not fenced;i+=1;continue
  if fenced:
   p=D.add_paragraph(s,'No Spacing');p.paragraph_format.keep_with_next=i+1<len(lines) and not lines[i+1].startswith('```');story.append(para(s or ' ','code'));i+=1;continue
  if not s.strip():i+=1;continue
  if s.startswith('|'):
   rows=[]
   while i<len(lines) and lines[i].startswith('|'):
    row=[clean(c.strip()) for c in lines[i].strip('|').split('|')]
    if not all(set(c)<=set('-: ') for c in row):rows.append(row)
    i+=1
   count=len(rows[0]);t=D.add_table(rows=1,cols=count);t.style='Light Shading Accent 1';t.autofit=True
   for j,val in enumerate(rows[0]):
    c=t.rows[0].cells[j];c.text=val;shading(c,'18354F')
    for run in c.paragraphs[0].runs:run.font.color.rgb=RGBColor(255,255,255);run.bold=True
   rep=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(rep)
   for row in rows[1:]:
    cells=t.add_row().cells
    for j,val in enumerate(row):cells[j].text=val
   for row in t.rows:
    for cell in row.cells:
     for p in cell.paragraphs:
      p.paragraph_format.space_after=Pt(4)
      for run in p.runs:run.font.size=Pt(9)
   if count==2:widths=[150,345]
   elif count==3:widths=[95,230,170]
   else:widths=[68,160,45,222] if '学时' in rows[0] else [110,145,135,105]
   data=[[para(c,'cellhead' if n==0 else 'cell') for c in row] for n,row in enumerate(rows)]
   table=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT');table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),navy),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F0F6F9')]),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#D3DFE9')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]));story.extend([table,Spacer(1,8)]);continue
  if s.startswith('#'):
   level=len(s)-len(s.lstrip('#'));label=s[level:].strip()
   page_task=(level==3 and label.startswith('任务') and (is_teacher or is_workbook))
   if page_task:D.add_page_break();story.append(PageBreak())
   D.add_heading(clean(label),0 if level==1 else min(level-1,3));story.append(para(label,'title' if level==1 else 'h2' if level==2 else 'h3'))
   if level==1:
    title=label
    if is_teacher:
     D.add_paragraph('36学时教学设计  /  12个任务  /  双人协作与个人过关')
     D.add_picture(str(R/'教学路线图_V2.png'),width=Cm(17))
     story.extend([para('36学时教学设计  /  12个任务  /  双人协作与个人过关'),Image(str(R/'教学路线图_V2.png'),width=495,height=309)])
   i+=1;continue
  D.add_paragraph(clean(s));story.append(para(s));i+=1
 D.core_properties.title=title
 D.save(path.with_suffix('.docx'))
 def page(canvas,doc):
  canvas.setStrokeColor(colors.HexColor('#D5E2EC'));canvas.line(50,30,545,30);canvas.setFillColor(colors.HexColor('#657F94'));canvas.setFont('STSong-Light',8);canvas.drawString(50,19,'RoomGuard V2 | 中职项目教学');canvas.drawRightString(545,19,f'{doc.page}')
 pdf=SimpleDocTemplate(str(path.with_suffix('.pdf')),pagesize=(595.28,841.89),leftMargin=50,rightMargin=50,topMargin=40,bottomMargin=43,title=title,author='RoomGuard 项目教学');pdf.build(story,onFirstPage=page,onLaterPages=page)
 print(path.stem)
if __name__=='__main__':
 for p in sorted(R.glob('*_V2.md')):export(p)
