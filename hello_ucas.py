# -*- coding=utf-8 -*-
import http.cookiejar
from bs4 import BeautifulSoup
import requests
import urllib,urllib.request
import re
import os
import datetime
import time







def validate_title(title):
    ''' 判断windows下改文件名是否合法并修改 '''
    rstr = r"[\/\\\:\*\?\"\<\>\|]"  # '/ \ : * ? " < > |'
    new_title = re.sub(rstr, "", title)  # 替换为下划线
    return new_title


def print_log(msg='', end='\n'):
    now = datetime.datetime.now()
    t = str(now.year) + '/' + str(now.month) + '/' + str(now.day) + ' ' \
      + str(now.hour).zfill(2) + ':' + str(now.minute).zfill(2) + ':' + str(now.second).zfill(2)
    print('[' + t + '] ' + str(msg), end=end) 


class UCAS_spider(object):
    def __init__(self):
        # hello
        print_log('-'*30)
        print_log('\t\tHello UCAS O_o\'')
        print_log('-'*30)

        
        self.root_url = 'http://sep.ucas.ac.cn'
        self.login_url = self.root_url + '/slogin'

        
        self.headers = {
            'Host': 'sep.ucas.ac.cn',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.80 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate, sdch',
            'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6',
        }
        self.session = requests.Session()
        self.session.headers = self.headers
        self.user_info = dict()

        self.course2id = dict()
        self.course2Homework = dict()
        self.course2resource = dict()
        self.course2bs = dict()

        # save dir
        self.save_root_dir = '.'



    def login(self, username=None, password=None, cfg='./config.txt'):
        if username is None or password is None:
            #print_log(os.path.realpath(__file__))
            #cfg = input("Input 'config.txt' path:")
            if os.path.isfile(cfg):
                with open(cfg, 'r') as f:
                    l = f.readline()
                    while l:

                        if len(l) > 9:
                            if l[0:9] == "username:":
                                self.user_info['userName'] = l.split(':')[-1].strip()
                            elif l[0:9] == "password:":
                                self.user_info['pwd'] = l.split(':')[-1].strip()
                        l = f.readline()
            else:
                print_log("Please write your login info in "+os.getcwd()+"/config.txt.")
                self.exit()
        else:
            self.user_info['userName'] = username
            self.user_info['pwd'] = password

        self.user_info['sb'] = 'sb'
        self.user_info['rememberMe'] = 1
        result = self.session.post(self.login_url, data=self.user_info)  
        if 'sepuser' in self.session.cookies.get_dict():
            print_log('Successfully logged in.')
            bs = self.get_bs(self.root_url)
            text = bs.find("li", {"class":"btnav-info", "title":"当前用户所在单位"}).get_text()
            name = re.compile(r"\s*(\S*)\s*(\S*)\s*").match(text).group(2)
            print_log('Hello ' + name + '!')  
        else:
            print_log('Login failed. Please check the login info.')
            self.exit()


        
    def get_all_courses(self):
        bs = self.get_bs(self.root_url)
        self.course_url = self.root_url + bs.find("li", {"class":"app-black m-black-col1"}).find("a", {"title":"课程网站"}).get('href')
        bs = self.get_bs(self.course_url)
        bs = self.get_bs(bs.find("noscript").meta.get("content")[6:])
        bs = self.get_bs('http://course.ucas.ac.' + bs.find('a',{'class':'Mrphs-toolsNav__menuitem--link ', 'title':'我的课程 - 查看或加入站点'}).get('href').split('.')[-1])
        courses_bs = bs.findAll('div',{'class':'fav-title '})
        self.course2id.clear()
        for c_bs in courses_bs:
            c_id = c_bs.find('a').get('href').split('/')[-1]
            c_name = c_bs.find('a').get('title')
            self.course2id[c_name] = c_id
            self.course2bs[c_name] = self.get_bs(self.id2course_url(c_id))
            

    def logout_courses(self):
        courses_n = len(self.course2id)
        print_log('已选 ' + str(courses_n) + ' 门课:')
        for i, course in enumerate(self.course2id):
            print_log('\t(' + '%*d'%(len(str(courses_n)), i+1) + '/' + str(courses_n) + ') ' + course)
        print_log()
        


    def sync_homework(self):
        print_log()
        print_log("作业提醒：")
        self.course2Homework.clear()
        # traverse courses
        homework_n = 0
        for i, c in enumerate(self.course2id):
            c_url = self.id2course_url(self.course2id[c])
            c_bs = self.course2bs[c]
            homework_url = c_url + '/tool/' + c_bs.find('a',{'class':'Mrphs-toolsNav__menuitem--link ', 'title':'作业 - 在线发布、提交和批改作业'}).get('href').split('/')[-1]
            homework_bs = self.get_bs(homework_url)
            homework_div = homework_bs.find('table', {'class':'table table-hover table-striped table-bordered'})
            if homework_div is None: continue
            homework_div = homework_div.findAll('tr')
            # traverse homework
            for i, homework in enumerate(homework_div):
                if i == 0: continue

                title = homework.find('a').text
                status = homework.find('td', {'headers':'status'}).text.strip()
                dueDate = homework.find('td', {'headers':'dueDate'}).text.strip()
                openDate = homework.find('td', {'headers':'openDate'}).text.strip()
                href = homework.find('a').get('href')
                f_id = href.split('?')[0].split('/')[-1]
                f_list = []

                if status == '尚未提交':
                    print_log('\t' + c + ' > ' + title + '\t截止: ' + dueDate)
                    homework_n += 1
        
        print_log('共 ' + str(homework_n) + ' 项未提交作业.')
                



    def sync_resources(self):
        print_log()
        print_log("同步课件中...")
        self.course2resource.clear()
        resource_n = 0
        for i, c in enumerate(self.course2id):
            c_url = self.id2course_url(self.course2id[c])
            c_bs = self.course2bs[c]
            resource_url = c_url + '/tool/' + c_bs.find('a',{'class':'Mrphs-toolsNav__menuitem--link ', 'title':'资源 - 上传、下载课件，发布文档，网址等信息'}).get('href').split('/')[-1]
            resource_bs = self.get_bs(resource_url)
            resource_div = [*resource_bs.findAll('a',{'title':'Word '}), *resource_bs.findAll('a',{'title':'PDF'}), *resource_bs.findAll('a',{'title':'PowerPoint '})]

            cur_dir = os.path.join(self.save_root_dir, c, 'src')
            for i, a_bs in enumerate(resource_div):        
                href = a_bs.get('href')
                href = urllib.parse.unquote(href)
                f_n = href.split('/')[-1]
                f_href = self.f_url(self.course2id[c], f_n, category='src')
                res = self.download(cur_dir, f_n, f_href)

                if res: 
                    resource_n += 1
                    print_log('\t' + os.path.join(cur_dir, f_n))

        print_log('新增 ' + str(resource_n) + ' 项资源.')

                
        

    def download(self, save_dir, fn, url):
        if os.path.exists(save_dir) == False:
            os.makedirs(save_dir)
        save_path = os.path.join(save_dir, fn)
        if os.path.exists(save_path) ==  False:
            content = self.session.get(url).content
            with open(save_path, "wb") as f:
                f.write(content)
            return True
        else:
            return False


    def id2course_url(self, c_id):
        return 'http://course.ucas.ac.cn/portal/site/' + c_id

    def f_url(self, c_id, f_n, f_id='', category='src'):
        if category == 'assignments':
            return 'http://course.ucas.ac.cn/access/content/attachment/' + c_id + '/作业/' + f_id + '/' + f_n
        elif category == 'src':
            return 'http://course.ucas.ac.cn/access/content/group/' + c_id + '/' + f_n


    def get_bs(self, url, max_try=20, headers=None):
        cnt_try = 0
        while max_try > cnt_try:
            try:
                #content = self.session.get(url, allow_redirects=False).content 
                if headers is None:
                    content = self.session.get(url).content 
                else:
                    content = self.session.get(url, headers=headers).content 
                bs = BeautifulSoup(content, "lxml")
                #bs = BeautifulSoup(content)
                return bs
            except Exception as e:
                if cnt_try == max_try:
                    raise e
                else:
                    cnt_try += 1
                    time.sleep(cnt_try)
                    print_log('\t' + str(e) + '\n\tReconnecting... num: ' + str(cnt_try))
        return None


    def exit(self):
        print_log()
        print_log(end='')
        input('按Enter退出...')
        os._exit(0)




    def control_panel(self):
        print_log()
        print_log("正在获取课程列表...")
        self.get_all_courses()
        self.logout_courses()

        print_log('同步选项(仅下载Word、PPT和PDF,跳过已存在同名文件):')
        print_log('  0 -- 作业')
        print_log('  1 -- 课件')
        print_log('  2 -- Both')
        print_log(end='')

        

        self.command = input("Your choice (deflaut 0): ")
        while len(self.command) != 1 or (self.command not in ['0', '1', '2']):
            if len(self.command) == 0: 
                self.command = 0
                break
            print_log('Invalid input.')
            print_log(end='')
            self.command = input("Your choice (deflaut 0): ")
        self.command = int(self.command)

        
        if self.command == 0 or self.command == 2:
            self.sync_homework()
        if self.command == 1 or self.command == 2:
            self.sync_resources()
            

        self.exit()
        





if __name__ == "__main__":        
    ucas = UCAS_spider()
    ucas.login()
    ucas.control_panel()
    
    
        

