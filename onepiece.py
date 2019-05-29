# -*- coding: utf-8 -*-
"""
腾讯动漫爬虫脚本

第一个参数选项
1.无 将按配置文件的默认设置进行爬取，无配置文件报错 无后接详细配置参数
2. m (modify file) 在配置文件的基础上进行修改（永久性） 后接可选的详细配置参数，见下
3. t (temporary) 在配置文件的基础上，进行临时性的爬取  后接可选的详细配置参数，见下
4. s (set file) 建立一个配置文件，若之前已经存在，则会被覆盖，修改参数也可通过直接修改配置文件完成  后接必选的详细配置参数，见下
5. h 输出帮助文档

具体的参数配置 mf/t 下列参数均为可选参数 s则必须包含下列所有参数（除-e外）
-c xxx 如 -c 505430/  将要爬取的漫画设置为海贼王 从你要爬取的漫画的url中取得
-se xxx 如 -se 945  将开始爬取的话数设定为第945话 ！！！（不包括第945话）！！！
-n xxx 如 -n 5  从设置的开始爬取话数开始，一共爬取5话（如有更新），默认为4，仅对本次有效，不记录到配置文件
-p xxx 如 -p D:\\tem\\  将漫画图片的保存路径设置为D:\\tem\\
-e xxx 如 -e 13322468550@163.com  设置将爬取结果以邮件方式发送的发送者邮箱  ！！！此参数后必须带有以下的参数 -r xxx 爬取结果的收件人邮箱 -psw xxx 发送邮箱的密码

示例：
脚本名.pyw s -c 505430/ -se 945 -n 5 -p D:\tem\ -e 133xxxx8550@163.com -r 757xxx393@qq.com -psw xxx
第一次使用脚本或需要生成新的配置文件 爬取海贼王 从945集开始 连续爬取5话 爬取的图片保存在D:\tem\下 最后的爬取结果通过133xxxx8550@163.com发送到757xxx383@qq。com 其中发送邮箱的密码是xxx

由于本人相当懒，暂时不打算做选项的输入检测
"""
import os
import re
import smtplib
import sys
import threading
import time
from email.mime.text import MIMEText
from email.utils import formataddr
from multiprocessing import Process, Queue

import json
import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait


def send_email():
    """
    用于向指定邮箱发送爬取结果邮件，相应的设置在crawling_settings中
    :return: None
    """
    try:
        msg = MIMEText('已爬取到第' + str(crawling_settings['last_episode']) + "话", 'plain', 'utf-8')
        msg['From'] = formataddr(["海贼王爬虫", crawling_settings['sender']])  # 括号里的对应发件人邮箱昵称、发件人邮箱账号
        msg['To'] = formataddr(["Jerry", crawling_settings['receiver']])  # 括号里的对应收件人邮箱昵称、收件人邮箱账号
        msg['Subject'] = "爬虫报告"  # 邮件的主题，也可以说是标题

        server = smtplib.SMTP("smtp.163.com", 25)  # 发件人邮箱中的SMTP服务器，端口是25
        server.login(crawling_settings['sender'], crawling_settings['password'])  # 括号中对应的是发件人邮箱账号、邮箱密码
        server.sendmail(crawling_settings['sender'], [crawling_settings['receiver'], ], msg.as_string())
        # 括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
        server.quit()  # 这句是关闭连接的意思
        print("邮件发送成功")
    except smtplib.SMTPException:
        print("Error: 无法发送邮件")


def save_pic(url, save_path):
    """
    单个用于下载和保存图片的线程
    :param url: 下载图片的url
    :param save_path: 图片保存完整路径
    :return: None
    """
    src = requests.get(url).content
    with open(save_path, 'wb') as file:
        file.write(src)


def init_browser(comic_you_need):
    """
    用于爬取的浏览器初始化
    :return:webdriver.Chrome
    """
    # 浏览器设置
    chrome_options = Options()
    # 无界面
    chrome_options.add_argument('--headless')
    the_init_browser = webdriver.Chrome(chrome_options=chrome_options)

    # 用于补全网址
    url = "http://ac.qq.com/Comic/ComicInfo/id/" + comic_you_need

    # 访问海贼王动漫的页面
    the_init_browser.get(url)
    return the_init_browser


def get_end_of_episode():
    """
    用于获取当前海贼王的最新话数
    :return: int 最新话数,webdriver.Chrome
    """
    first_browser = init_browser(crawling_settings['comic'])
    if first_browser:
        try:
            end_of_episode_text = first_browser.find_element_by_class_name('works-ft-new').text
            end_of_episode = min(int(re.search("第\d+[话 ]", end_of_episode_text).group(0)[1:4]),
                                 int(crawling_settings['last_episode']) + int(crawling_settings['num']))
        except NoSuchElementException or ValueError:
            end_of_episode = int(crawling_settings['last_episode']) + int(crawling_settings['num'])
    else:
        end_of_episode = int(crawling_settings['last_episode']) + int(crawling_settings['num'])
    return end_of_episode, first_browser


def get_right_title(actual_start_episode, last_cid=None):
    """
    用于获取正确话数对应的url中的cid
    :param actual_start_episode: 需要爬取的话数
    :param last_cid: 上一次的cid
    :return: int 正确话数对应的cid
    """
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
    """
    爬取主函数，爬取指定的几话漫画
    :param q: 进程间的通信，要爬取的集数
    :param r: 进程间的通信，爬取结果
    :param crawling_settings2: 爬取设置
    :param browser: webdriver
    :return: None
    """
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

    # 获取这个进程要爬取的话数区间
    settings = q.get(True)
    if not browser:
        return
    if settings['start_episode'] > settings['end_of_episode']:
        browser.quit()
        return
    browser.get("http://ac.qq.com/ComicView/index/id/505430/cid/" + str(settings['cid']))

    # 正式开始爬取图片
    # 下载图片线程列表
    thread = list()
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
            url = img.get_attribute('src')
            while re.search('gif$', url):
                time.sleep(0.5)
                img = i.find_element_by_tag_name('img')
                url = img.get_attribute('src')

            t = threading.Thread(target=save_pic, args=(url, pic_all_name))
            thread.append(t)
            # 为避免被封禁，对同时下载图片数量进行限制
            while len(thread) > 2:
                time.sleep(0.2)
                for i in thread:
                    if not i.is_alive():
                        thread.remove(i)

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

    # 等待所有图片下载完毕
    while len(thread) != 0:
        for i in thread:
            if not i.is_alive():
                thread.remove(i)

    # 返回下载结果
    r.put(settings['start_episode'] - 1)
    browser.quit()


if __name__ == '__main__':
    # 加载配置文件
    PARAMETER_MAPPING = {'-c': 'comic', '-se': 'last_episode', '-p': 'save_path', '-e': 'sender', '-psw': 'password',
                         '-r': 'receiver', '-n': 'num'}
    DEFAULT_SETTING_FILE_NAME = "settings.csv"
    DEFAULT_NUM_EACH_CRAWLING = 3
    argv = sys.argv
    crawling_settings = None
    if len(argv) == 1:
        # 未指定参数使用默认配置文件
        with open(DEFAULT_SETTING_FILE_NAME) as f:
            crawling_settings = dict(json.load(f))
    else:
        # 指定参数
        if '?' in argv[1] or 'h' in argv[1]:
            # 第一个命令为 -? ? -h h help 均认为是输出帮助
            print(__doc__)
            exit(0)
        else:
            if argv[1] == 'm' or argv[1] == 't':
                # 在源配置文件上修改部分的配置
                with open(DEFAULT_SETTING_FILE_NAME) as f:
                    crawling_settings = dict(json.load(f))
            if argv[1] == 's' or argv[1] == 'm' or argv[1] == 't':
                # 新建新的配置
                crawling_settings = dict()
                for command, value in zip(argv[2::2], argv[3::2]):
                    crawling_settings[PARAMETER_MAPPING[command]] = value

    if crawling_settings is None:
        exit(1)
    if 'num' in crawling_settings.keys():
        DEFAULT_NUM_EACH_CRAWLING = int(crawling_settings['num'])

    # try:
    #     settings_file_1 = pandas.read_csv("settings.csv").to_dict()
    #     crawling_settings = dict()
    #     crawling_settings['comic'] = settings_file_1['comic'][0]
    #     crawling_settings['save_path'] = settings_file_1['save_path'][0]
    #     crawling_settings['last_episode'] = settings_file_1['last_episode'][0]
    #     crawling_settings['sender'] = settings_file_1['sender'][0]
    #     crawling_settings['password'] = settings_file_1['password'][0]
    #     crawling_settings['receiver'] = settings_file_1['receiver'][0]
    # except:
    #     crawling_settings = {'comic': '505430/', 'save_path': 'D:\\tem\\', 'last_episode': 916}
    #     settings_file_1 = pandas.DataFrame(crawling_settings, index=[0])
    #     settings_file_1 = settings_file_1.to_csv("settings.csv")
    #     input("已生成默认的配置文件，请在当前工作目录下打开并配置，再重新启动此脚本")
    #     os._exit(0)
    # finally:
    #     pass

    # 用于进程间的通信，要爬取的集数，爬取结果
    q_msg = Queue()
    r_msg = Queue()

    # 打开两个爬取进程
    p_browser0 = Process(target=crawling_comic, args=(q_msg, r_msg, crawling_settings))
    p_browser1 = Process(target=crawling_comic, args=(q_msg, r_msg, crawling_settings))
    p_browser0.start()
    p_browser1.start()

    # 爬取的集数设置
    settings = dict()
    settings['start_episode'] = int(crawling_settings['last_episode']) + 1
    settings['end_of_episode'], first_browser = get_end_of_episode()

    # 访问海贼王动漫的页面
    try:
        WebDriverWait(first_browser, 10).until(expected_conditions.element_to_be_clickable((By.LINK_TEXT, "开始阅读"))) \
            .click()
    except TimeoutException:
        first_browser.quit()
        print("网络可能未连接")
        exit()

    # 进程间的负载均衡，即分配各自要爬取的集数
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

    # 三个进程开始爬取
    start_time = time.time()
    crawling_comic(q_msg, r_msg, crawling_settings, first_browser)
    p_browser0.join()
    p_browser1.join()

    # 获取爬取结果
    while not r_msg.empty():
        tem = r_msg.get()
        if tem > int(crawling_settings['last_episode']):
            crawling_settings['last_episode'] = tem

    with open(DEFAULT_SETTING_FILE_NAME, 'w') as f:
        json.dump(crawling_settings, f)
    # try:
    #     settings_file_1 = pandas.DataFrame(crawling_settings, index=[0])
    #     settings_file_1 = settings_file_1.to_csv("settings.csv")
    # except:
    #     print("配置文件保存失败")

    # 发送爬取结果提示邮件
    send_email()
