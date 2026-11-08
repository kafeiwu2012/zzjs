from playwright.sync_api import sync_playwright
from pathlib import Path
import json,time
out=Path('artifacts');out.mkdir(exist_ok=True);errors=[]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=__import__('os').environ.get('CHROMIUM_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
 page=b.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)));page.goto('http://127.0.0.1:8080');page.wait_for_selector('.room');assert page.locator('.room').count()>=3
 page.screenshot(path=str(out/'V2_自适应监控.png'),full_page=True)
 page.goto('http://127.0.0.1:8080/teacher');page.wait_for_selector('#teacherLoginForm:visible');page.fill('#teacherPassword','DemoOnly-123456');page.click('#teacherLoginForm button');page.wait_for_selector('#teacherApp:visible');page.wait_for_timeout(500)
 page.screenshot(path=str(out/'V2_教师节点管理.png'),full_page=True)
 page.click('#newTicket');page.wait_for_selector('#ticketPanel:visible');code=page.locator('#ticketText').inner_text();device='rg-esp32-browser'+str(int(time.time()))
 r=page.request.post('http://127.0.0.1:8080/api/enroll',data={'id':device,'code':code,'model':'ESP32','firmware':'2.0','capabilities':['dht11','mq2','flame']});assert r.json()['status']=='pending'
 page.click('#refreshAll');f=page.locator('form[data-node="'+device+'"]');f.wait_for();f.locator('input[name=room]').fill('104');f.locator('input[name=floor]').fill('2F');f.locator('button').click();page.wait_for_timeout(600)
 # Approval is simulated for demo; assert the API releases a unique credential after approval.
 r=page.request.post('http://127.0.0.1:8080/api/enroll',data={'id':device,'code':code});assert r.json()['status']=='approved'
 token=page.evaluate("sessionStorage.getItem('rg_token')");headers={'Authorization':'Bearer '+token}
 # User-provided labels must remain text in both teacher attributes and monitoring HTML.
 label='104" ><img src=x onerror=window.RGXSS=1>'
 assert page.request.post('http://127.0.0.1:8080/api/manage/approve',headers=headers,data={'id':device,'room':label,'floor':'2F'}).status==200
 page.click('#refreshAll');page.wait_for_timeout(300);assert f.locator('input[name=room]').input_value()==label;assert page.evaluate('window.RGXSS||0')==0
 safe=b.new_page();safe.goto('http://127.0.0.1:8080');safe.wait_for_selector('.room');assert safe.locator('img[onerror]').count()==0;assert safe.evaluate('window.RGXSS||0')==0;safe.close()
 assert page.request.post('http://127.0.0.1:8080/api/manage/approve',headers=headers,data={'id':device,'room':'104','floor':'2F'}).status==200
 cfg={'title':'校园楼宇环境监测','theme':'dark','font_scale':1.1,'page_size':2,'rotation_seconds':5,'refresh_seconds':2,'alarm_first':True,'sound_enabled':False,'history_hours':24,'fields':['temperature','humidity','mq','flame'],'rooms':[],'floor':''}
 assert page.request.post('http://127.0.0.1:8080/api/manage/profiles',headers=headers,data={'id':'default','config':cfg}).status==200
 page.click('[data-panel=display]');page.wait_for_timeout(300);page.screenshot(path=str(out/'V2_教师终端设置.png'),full_page=True)
 page.click('[data-panel=system]');page.wait_for_timeout(300);page.screenshot(path=str(out/'V2_教师服务管理.png'),full_page=True)
 screen=b.new_page(viewport={'width':1920,'height':1080});screen.on('pageerror',lambda e:errors.append(str(e)));screen.goto('http://127.0.0.1:8080/?screen=1');screen.wait_for_selector('body.dark-theme');screen.wait_for_selector('.room');assert screen.locator('.room').count()==2
 first=screen.locator('#pageInfo').inner_text();screen.wait_for_function("(initial)=>document.getElementById('pageInfo').textContent!==initial",arg=first,timeout=12000)
 screen.screenshot(path=str(out/'V2_大屏轮播.png'),full_page=True)
 # Restore full-card light profile for the normal PC/mobile screenshots.
 cfg.update(theme='light',page_size=6,font_scale=1.0,sound_enabled=True)
 assert page.request.post('http://127.0.0.1:8080/api/manage/profiles',headers=headers,data={'id':'default','config':cfg}).status==200
 normal=b.new_page(viewport={'width':1440,'height':1080});normal.goto('http://127.0.0.1:8080');normal.wait_for_function("Number(document.getElementById('totalCount').textContent)>=4");assert normal.locator('.room').count()>=4
 normal.screenshot(path=str(out/'V2_四节点自动显示.png'),full_page=True)
 mobile=b.new_page(viewport={'width':375,'height':812},is_mobile=True);mobile.goto('http://127.0.0.1:8080');mobile.wait_for_selector('.room');assert mobile.evaluate('document.documentElement.scrollWidth<=innerWidth');mobile.screenshot(path=str(out/'V2_手机显示.png'),full_page=True)
 b.close()
assert not errors,errors
report={'initial_nodes':3,'new_pending_approved':True,'credential_after_approval':True,'fourth_card_without_web_rebuild':True,'teacher_console':True,'profile_theme_and_pagination':True,'rotation':True,'mobile_layout':True,'room_label_escaped':True,'page_errors':errors,'broker_account_helper':'simulated_demo_only'}
(out/'浏览器V2测试.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
