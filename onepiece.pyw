# -*- coding: utf-8 -*-
import os
import re
import smtplib
import threading
import time
from email.mime.text import MIMEText
from email.utils import formataddr
from multiprocessing import Process, Queue

import pandas
import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait


def send_email():
    my_sender = '13322468550@163.com'  # 发件人邮箱账号，为了后面易于维护，所以写成了变量
    my_user = '757320383@qq.com'  # 收件人邮箱账号，为了后面易于维护，所以写成了变量
    try:
        msg = MIMEText('已爬取到第' + str(crawling_settings['last_episode']) + "话", 'plain', 'utf-8')
        msg['From'] = formataddr(["海贼王爬虫", my_sender])  # 括号里的对应发件人邮箱昵称、发件人邮箱账号
        msg['To'] = formataddr(["Jerry", my_user])  # 括号里的对应收件人邮箱昵称、收件人邮箱账号
        msg['Subject'] = "爬虫报告"  # 邮件的主题，也可以说是标题

        server = smtplib.SMTP("smtp.163.com", 25)  # 发件人邮箱中的SMTP服务器，端口是25
        server.login(my_sender, "101412315")  # 括号中对应的是发件人邮箱账号、邮箱密码
        server.sendmail(my_sender, [my_user, ], msg.as_string())  # 括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
        server.quit()  # 这句是关闭连接的意思
        print("邮件发送成功")
    except smtplib.SMTPException:
        print("Error: 无法发送邮件")


def save_pic(url, save_path):
    src = requests.get(url).content
    with open(save_path, 'wb') as file:
        file.write(src)


def init_browser(comic_you_need):
    """用于爬取的浏览器初始化"""
    # 浏览器设置
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    the_init_browser = webdriver.Chrome(chrome_options=chrome_options)

    # 补全网址
    url = "http://ac.qq.com/Comic/ComicInfo/id/" + comic_you_need

    # 访问海贼王动漫的页面
    the_init_browser.get(url)
    return the_init_browser


def get_end_of_episode():
    first_browser = init_browser(crawling_settings['comic'])
    if first_browser:
        try:
            end_of_episode_text = first_browser.find_element_by_class_name('works-ft-new').text
            end_of_episode = int(re.search("第\d+[话 ]", end_of_episode_text).group(0)[1:4])
        except NoSuchElementException or ValueError:
            end_of_episode = crawling_settings['last_episode'] + 3
    else:
        end_of_episode = crawling_settings['last_episode'] + 3
    return end_of_episode, first_browser


def get_right_title(actual_start_episode, last_cid=None):
    if last_cid:
        cid = last_cid
    else:
        cid = actual_start_episode
    first_browser.get("http://ac.qq.com/ComicView/index/id/" + crawling_settings['comic'] + 'cid/' +
                      str(cid))
    right_title = 0
    while actual_start_episode != right_title:
        # 获取当前爬取的正确集数
        try:
            right_title = int(re.search("第\d+[话 ]", first_browser.title).group(0)[1:-1])
        except AttributeError:
            right_title = actual_start_episode - 1

        if right_title < actual_start_episode:
            cid = cid + actual_start_episode - right_title
            first_browser.get("http://ac.qq.com/ComicView/index/id/505430/cid/" + str(cid))
    return cid


def crawling_comic(q, r, crawling_settings2, browser=None):
    """开始爬取"""
    if not browser:
        # 初始化浏览器
        comic_you_need = crawling_settings2['comic']
        browser = init_browser(comic_you_need)

        # 访问海贼王动漫的页面
        try:
            WebDriverWait(browser, 10).until(
                expected_conditions.element_to_be_clickable((By.LINK_TEXT, "开始阅读"))).click()
        except TimeoutException:
            browser.quit()
            print("网络可能未连接")

    settings = q.get(True)
    if not browser:
        return
    if settings['start_episode'] > settings['end_of_episode']:
        browser.quit()
        return
    browser.get("http://ac.qq.com/ComicView/index/id/505430/cid/" + str(settings['cid']))

    thread = list()
    # 正式开始爬取图片
    while settings['start_episode'] <= settings['end_of_episode']:
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
            try:
                while not re.match("^https://", img.get_attribute('src')):
                    img = i.find_element_by_tag_name('img')
            except StaleElementReferenceException:
                time.sleep(1)
                img = i.find_element_by_tag_name('img')
                while not re.match("^https://", img.get_attribute('src')):
                    img = i.find_element_by_tag_name('img')
            url = img.get_attribute('src')
            t = threading.Thread(target=save_pic, args=(url, pic_all_name))
            thread.append(t)
            t.start()
            pic_name += 1

        print("第%d话爬取完成！" % settings['start_episode'])

        settings['start_episode'] += 1
        # 点击下一话
        try:
            browser.find_element_by_id('next_item').click()  # 模拟用户点击下一话
        except:
            print("已到最后一话，第%d话。" % (settings['start_episode'] - 1))
            break

    while len(thread) != 0:
        for i in thread:
            if not i.is_alive():
                thread.remove(i)
    r.put(settings['start_episode'] - 1)
    browser.quit()


if __name__ == '__main__':
    # 加载配置文件
    try:
        settings_file_1 = pandas.read_csv("settings.csv").to_dict()
        crawling_settings = dict()
        crawling_settings['comic'] = settings_file_1['comic'][0]
        crawling_settings['save_path'] = settings_file_1['save_path'][0]
        crawling_settings['last_episode'] = settings_file_1['last_episode'][0]
    except:
        crawling_settings = {'comic': '505430/', 'save_path': 'D:\\tem\\', 'last_episode': 916}
    finally:
        pass
    q_msg = Queue()
    r_msg = Queue()
    p_browser0 = Process(target=crawling_comic, args=(q_msg, r_msg, crawling_settings))
    p_browser1 = Process(target=crawling_comic, args=(q_msg, r_msg, crawling_settings))
    p_browser0.start()
    p_browser1.start()

    settings = dict()
    # 爬取的集数设置
    settings['start_episode'] = crawling_settings['last_episode'] + 1
    settings['end_of_episode'], first_browser = get_end_of_episode()

    # 访问海贼王动漫的页面
    try:
        WebDriverWait(first_browser, 10).until(expected_conditions.element_to_be_clickable((By.LINK_TEXT, "开始阅读"))) \
            .click()
    except TimeoutException:
        first_browser.quit()
        print("网络可能未连接")
        exit()

    # 进程间的负载均衡
    short_of_episode = settings['end_of_episode'] - settings['start_episode'] + 1
    if short_of_episode > 1:
        remainder = short_of_episode % 3

        tem = int(short_of_episode / 3) + settings['start_episode'] - 1
        if remainder > 0:
            tem += 1
            remainder -= 1
        tem_cid = get_right_title(settings['start_episode'])
        q_msg.put({'start_episode': settings['start_episode'], 'end_of_episode': tem, 'cid': tem_cid})

        tem2 = tem + int(short_of_episode / 3)
        if remainder > 0:
            tem2 += 1
            remainder -= 1
        tem_cid = get_right_title(tem + 1, tem_cid + 1)
        q_msg.put({'start_episode': tem + 1, 'end_of_episode': tem2, 'cid': tem_cid})
        if tem2 + 1 <= settings['end_of_episode']:
            tem_cid = get_right_title(tem2 + 1, tem_cid + 1)
            q_msg.put({'start_episode': tem2 + 1, 'end_of_episode': settings['end_of_episode'], 'cid': tem_cid})
        else:
            q_msg.put({'start_episode': 1, 'end_of_episode': 0, 'cid': 0})

    elif short_of_episode < 1:
        time.sleep(3)
        q_msg.put({'start_episode': 1, 'end_of_episode': 0, 'cid': 0})
        q_msg.put({'start_episode': 1, 'end_of_episode': 0, 'cid': 0})
        q_msg.put({'start_episode': 1, 'end_of_episode': 0, 'cid': 0})
    else:
        q_msg.put({'start_episode': 1, 'end_of_episode': 0, 'cid': 0})
        q_msg.put({'start_episode': 1, 'end_of_episode': 0, 'cid': 0})
        settings['cid'] = get_right_title(settings['start_episode'])
        q_msg.put(settings)

    start_time = time.time()
    crawling_comic(q_msg, r_msg, crawling_settings, first_browser)
    p_browser0.join()
    p_browser1.join()

    while not r_msg.empty():
        tem = r_msg.get()
        if tem > crawling_settings['last_episode']:
            crawling_settings['last_episode'] = tem
    try:
        settings_file_1 = pandas.DataFrame(crawling_settings, index=[0])
        settings_file_1 = settings_file_1.to_csv("settings.csv")
    except:
        print("配置文件保存失败")

    send_email()
