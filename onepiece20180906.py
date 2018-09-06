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
import pandas as pd


def init_browser():
    """用于爬取的浏览器初始化"""
    # 爬取的动漫相关设置
    comic_you_need = '505430/'  # 海贼王 505430/

    # 浏览器设置
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    browser = webdriver.Chrome(chrome_options=chrome_options)

    # 补全网址
    url = "http://ac.qq.com/Comic/ComicInfo/id/" + comic_you_need

    # 访问并打开海贼王动漫的页面
    browser.get(url)
    try:
        WebDriverWait(browser, 10).until(expected_conditions.element_to_be_clickable((By.LINK_TEXT, "开始阅读"))).click()
    except TimeoutException:
        browser.quit()
        print("网络可能未连接")
        return None

    return browser


def crawling_comic(q):
    """开始爬取"""
    comic_you_need = '505430/'  # 海贼王 505430/
    end_sign = 0
    browser = init_browser()
    settings = q.get(True)
    browser.get("http://ac.qq.com/ComicView/index/id/" + comic_you_need + 'cid/' + str(settings['start_episode']))
    cid = settings['start_episode']

    # 检查是否还在应当爬取的范围内
    while settings['start_episode'] <= settings['end_of_episode'] and browser:
        # 检测即将爬取的集数是否存在
        try:
            WebDriverWait(browser, 2).until(expected_conditions.visibility_of_element_located(
                (By.PARTIAL_LINK_TEXT, "很遗憾，该漫画不存在或章节已被删除，我们为您推荐了下面一些漫画")))
            if end_sign == 1:
                end_sign = 2
            else:
                end_sign = 1
        except TimeoutException:
            end_sign = 0
        if end_sign == 1:
            print("很遗憾，该漫画不存在或章节已被删除，或许是漫画尚未更新到该集。")
            continue
        elif end_sign == 2:
            break
        print(end_sign)

        # 获取当前爬取的正确集数
        try:
            print(browser.title)
            right_title = int(re.search("第\d+话", browser.title).group(0)[1:-1])
        except NoSuchElementException:
            right_title = settings['start_episode']
            print("无法获取当前正确的话数")

        # 正式开始爬取图片
        if right_title == settings['start_episode']:
            print('正在爬取第%d话' % right_title)

            pic_name = 0
            # 获取图片标签
            comic_contain = browser.find_element_by_id('comicContain')
            comic = comic_contain.find_elements_by_tag_name('li')

            # 创建文件夹
            path = 'D:\\tem\\' + str(right_title) + '\\'
            folder = os.path.exists(path)
            if not folder:
                os.makedirs(path)

            # 爬取图片
            for i in comic[0:-2]:
                if i.get_attribute('class') == 'main_ad_top' or i.get_attribute('class') == 'main_ad_bottom':
                    continue
                browser.execute_script("arguments[0].scrollIntoView();", i)  # 拖动到可见的元素去

                if pic_name < 10:
                    pic_all_name = str(path) + '0' + str(pic_name) + '.png'
                else:
                    pic_all_name = str(path) + str(pic_name) + '.png'

                img = i.find_element_by_tag_name('img')
                while img.get_attribute('src') == r'//ac.gtimg.com/media/images/pixel.gif':
                    img = i.find_element_by_tag_name('img')
                src = requests.get(img.get_attribute('src')).content
                with open(pic_all_name, 'wb') as file:
                    file.write(src)
                pic_name += 1

            print("第%d话爬取完成！" % right_title)
            settings['start_episode'] += 1

            # 点击下一话
            try:
                browser.find_element_by_id('next_item').click()  # 模拟用户点击下一话
            except:
                print("已到最后一话，第%d话。" % right_title)
                break

        elif right_title < settings['start_episode']:
            cid = cid + settings['start_episode'] - right_title
            browser.get("http://ac.qq.com/ComicView/index/id/505430/cid/" + str(cid))
        else:
            right_title = settings['start_episode']
    q.put(settings['end_of_episode'])
    browser.quit()


if __name__ == '__main__':
    try:
        crawling_settings = dict(pd.DataFrame(pd.read_csv('settings.csv')))
        option = int(input("上次爬取到了第%d集，是否继续爬取至最新集？1为是，其他为否\n" % crawling_settings['last_episode']))
    except FileNotFoundError:
        crawling_settings = {'comic': '505430/', 'save_path': 'D:\\tem\\', 'last_episode': 0}
        option = 0
    except ValueError:
        option = 0
    q_msg = Queue()
    p_browser0 = Process(target=crawling_comic, args=(q_msg,))
    p_browser1 = Process(target=crawling_comic, args=(q_msg,))
    p_browser0.start()
    p_browser1.start()

    settings = {}
    # 爬取的集数设置
    if option == 1:
        settings['start_episode'] = int(crawling_settings['last_episode']) + 1
        settings['end_of_episode'] = settings['start_episode'] + 4
    else:
        while True:
            settings['start_episode'] = int(input('开始爬取的话数\n'))
            if settings['start_episode'] > 0:
                break
            else:
                print("话数必须大于0")
        while True:
            settings['end_of_episode'] = int(input('结束话数\n'))
            if settings['end_of_episode'] >= settings['start_episode']:
                break
            else:
                print("结束集数必须大于等于开始集数")

    if settings['end_of_episode'] - settings['start_episode'] >= 1:
        tem = int((settings['end_of_episode'] - settings['start_episode']) / 2 + settings['start_episode'])
    else:
        tem = settings['start_episode']
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
    pd.DataFrame.from_dict([crawling_settings]).to_csv('settings.csv')
    print("共花费时间", end='')
    print(time.time() - start_time)
