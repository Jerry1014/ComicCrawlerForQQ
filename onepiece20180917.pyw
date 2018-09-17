# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
import requests
import os
import re
import time
from multiprocessing import Process, Queue
import pandas
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr


def init_browser(comic_you_need):
    """用于爬取的浏览器初始化"""
    # 浏览器设置
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    browser = webdriver.Chrome(chrome_options=chrome_options)

    # 补全网址
    url = "http://ac.qq.com/Comic/ComicInfo/id/" + comic_you_need

    # 访问海贼王动漫的页面
    browser.get(url)
    return browser


def get_end_of_episode(crawling_settings):
    browser = init_browser(crawling_settings['comic'])
    if browser:
        try:
            end_of_episode_text = browser.find_element_by_class_name('works-ft-new').text
            end_of_episode = int(re.search("第\d+(话| )",end_of_episode_text).group(0)[1:4])
        except Exception as e:
            end_of_episode = crawling_settings['last_episode'] + 3
    else:
        end_of_episode = crawling_settings['last_episode'] + 3
    return end_of_episode


def crawling_comic(q, crawling_settings2):
    """开始爬取"""
    # 初始化浏览器
    comic_you_need = crawling_settings2['comic']
    end_sign = 0
    browser = init_browser(comic_you_need)

    # 访问海贼王动漫的页面
    try:
        WebDriverWait(browser, 10).until(expected_conditions.element_to_be_clickable((By.LINK_TEXT, "开始阅读"))).click()
    except TimeoutException:
        browser.quit()
        print("网络可能未连接")
        return

    settings = q.get(True)
    if (not browser) or settings['start_episode'] > settings['end_of_episode']:
        return
    browser.get("http://ac.qq.com/ComicView/index/id/" + comic_you_need + 'cid/' + str(settings['start_episode']))
    cid = settings['start_episode']
    right_title = 0
    while settings['start_episode'] != right_title:
        # 检测即将爬取的集数是否存在
        if re.search("^错误提示", browser.title):
            if end_sign == 1:
                end_sign = 2
                break
            else:
                end_sign = 1
                continue
        else:
            end_sign = 0

        # 获取当前爬取的正确集数
        try:
            right_title = int(re.search("第\d+(话| )", browser.title).group(0)[1:-1])
        except AttributeError:
            right_title = settings['start_episode']
            print("无法获取当前正确的话数")

        if right_title < settings['start_episode']:
            cid = cid + settings['start_episode'] - right_title
            browser.get("http://ac.qq.com/ComicView/index/id/505430/cid/" + str(cid))

    # 正式开始爬取图片
    while settings['start_episode'] <= settings['end_of_episode'] and end_sign != 2:
        print('正在爬取第%d话' % settings['start_episode'])

        pic_name = 0
        # 获取图片标签
        try:
            comic_contain = browser.find_element_by_id('comicContain')
            comic = comic_contain.find_elements_by_tag_name('li')
        except NoSuchElementException:
            return

        # 创建文件夹
        path = crawling_settings2['save_path'] + str(settings['start_episode']) + '\\'
        folder = os.path.exists(path)
        if not folder:
            os.makedirs(path)

        # 爬取图片
        for i in comic[:-2]:
            if i.get_attribute('class') == 'main_ad_top' or i.get_attribute('class') == 'main_ad_bottom':
                continue
            browser.execute_script("arguments[0].scrollIntoView();", i)  # 拖动到可见的元素去

            if pic_name < 10:
                pic_all_name = str(path) + '0' + str(pic_name) + '.png'
            else:
                pic_all_name = str(path) + str(pic_name) + '.png'

            img = i.find_element_by_tag_name('img')
            while not re.match("^https://", img.get_attribute('src')):
                img = i.find_element_by_tag_name('img')
            src = requests.get(img.get_attribute('src')).content
            with open(pic_all_name, 'wb') as file:
                file.write(src)
            pic_name += 1

        print("第%d话爬取完成！" % settings['start_episode'])

        settings['start_episode'] += 1
        # 点击下一话
        try:
            browser.find_element_by_id('next_item').click()  # 模拟用户点击下一话
        except:
            print("已到最后一话，第%d话。" % (settings['start_episode']-1))
            break

    if end_sign != 2:
        q.put(settings['start_episode']-1)
    browser.quit()


if __name__ == '__main__':
    # 加载配置文件
    try:
        settings_file_1 = pandas.read_csv("settings.csv").to_dict()
        crawling_settings = dict()
        crawling_settings['comic'] = settings_file_1['comic']
        crawling_settings['save_path'] = settings_file_1['save_path']
        crawling_settings['last_episode'] = settings_file_1['last_episode']
    except:
        crawling_settings = {'comic': '505430/', 'save_path': 'D:\\tem\\', 'last_episode': 916}
    finally:
        pass
    q_msg = Queue()
    p_browser0 = Process(target=crawling_comic, args=(q_msg, crawling_settings))
    p_browser1 = Process(target=crawling_comic, args=(q_msg, crawling_settings))
    p_browser0.start()
    p_browser1.start()

    settings = {}
    # 爬取的集数设置
    settings['start_episode'] = crawling_settings['last_episode'] + 1
    settings['end_of_episode'] = get_end_of_episode(crawling_settings)

    if settings['end_of_episode'] - settings['start_episode'] >= 1:
        tem = int((settings['end_of_episode'] - settings['start_episode']) / 2 + settings['start_episode'])
    elif settings['end_of_episode'] - settings['start_episode'] >= 0:
        tem = settings['start_episode']
    else:
        exit()

    q_msg.put({'start_episode': tem + 1, 'end_of_episode': settings['end_of_episode']})
    q_msg.put({'start_episode': settings['start_episode'], 'end_of_episode': tem})

    start_time = time.time()
    p_browser0.join()
    p_browser1.join()
    crawling_settings['last_episode'] = 0
    while not q_msg.empty():
        tem = q_msg.get()
        if tem > crawling_settings['last_episode']:
            crawling_settings['last_episode'] = tem
    try:
        settings_file_1 = pandas.Series(crawling_settings)
        settings_file_1 = settings_file_1.to_csv("settings.csv")
    except:
        print("配置文件保存失败")

    my_sender = 'XXXXXXXX@163.com'  # 发件人邮箱账号，为了后面易于维护，所以写成了变量
    my_user = 'XXXXXXXX@qq.com'  # 收件人邮箱账号，为了后面易于维护，所以写成了变量
    try:
        msg = MIMEText('已爬取到第'+str(tem)+"话", 'plain', 'utf-8')
        msg['From'] = formataddr(["海贼王爬虫", my_sender])  # 括号里的对应发件人邮箱昵称、发件人邮箱账号
        msg['To'] = formataddr(["XXXXX", my_user])  # 括号里的对应收件人邮箱昵称、收件人邮箱账号
        msg['Subject'] = "爬虫报告"  # 邮件的主题，也可以说是标题

        server = smtplib.SMTP("smtp.163.com", 25)  # 发件人邮箱中的SMTP服务器，端口是25
        server.login(my_sender, "XXXXXXXX")  # 括号中对应的是发件人邮箱账号、邮箱密码
        server.sendmail(my_sender, [my_user, ], msg.as_string())  # 括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
        server.quit()  # 这句是关闭连接的意思
        print("邮件发送成功")
    except smtplib.SMTPException:
        print("Error: 无法发送邮件")
