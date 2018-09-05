# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
import requests
import os
import re
import time
from fake_useragent import UserAgent
from multiprocessing import Pool


def setup():
    """爬取设置"""
    settings = {}
    # 伪装ua设置
    try:
        settings['fake_ua'] = int(input("是否需要伪装ua，可能导致爬取变慢，1为是，其他为否\n"))
    except ValueError:
        settings['fake_ua'] = 0
    finally:
        if settings['fake_ua'] != 1:
            settings['fake_ua'] = 0

    # 爬取的集数设置
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

    return settings


def init_browser(start_episode, fake_ua):
    """用于爬取的浏览器初始化"""
    print("正在启动浏览器进程")
    # 爬取的动漫相关设置
    comic_you_need = '505430/'  # 海贼王 505430/

    # 浏览器设置
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    if fake_ua == 1:
        ua = UserAgent()
        chrome_options.add_argument('user - agent =' + ua.random)
    browser = webdriver.Chrome(chrome_options=chrome_options)

    # 补全网址
    url = "http://ac.qq.com/Comic/ComicInfo/id/" + comic_you_need

    # 访问并打开海贼王动漫的页面
    browser.get(url)
    WebDriverWait(browser, 10).until(expected_conditions.element_to_be_clickable((By.LINK_TEXT, "开始阅读"))).click()
    url = url.replace('/ComicInfo', 'View/index')
    browser.get(url+'cid/' + str(start_episode))

    print("浏览器进程已启动")
    return browser


def crawling_comic(settings):
    """开始爬取"""
    browser = init_browser(settings['start_episode'], settings['fake_ua'])
    cid = settings['start_episode']

    # 检查是否还在应当爬取的范围内
    while settings['start_episode'] <= settings['end_of_episode']:

        # 检测即将爬取的集数是否存在
        retries = 10
        while retries > 0:
            try:
                browser.find_element_by_xpath("//div[@class='mod_958wr mod_wbg mod_gbd mod_of']")
                time.sleep(0.5)
                retries -= 1
            except NoSuchElementException:
                break
        if retries == 0:
            print("很遗憾，该漫画不存在或章节已被删除，或许是漫画尚未更新到该集。")
            break

        # 获取当前爬取的正确集数
        try:
            right_title = int(re.search("第\d+话", browser.title).group(0)[1:-1])
        except:
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
    browser.quit()


if __name__ == '__main__':
    start_time = time.time()
    settings_tem = setup()
    if settings_tem['end_of_episode'] - settings_tem['start_episode'] >= 1:
        tem = int((settings_tem['end_of_episode'] - settings_tem['start_episode'])/2 +
                  settings_tem['start_episode'])
        settings_all = [{'start_episode': settings_tem['start_episode'], 'end_of_episode': tem, 'fake_ua':settings_tem['fake_ua']},
                        {'start_episode': tem + 1, 'end_of_episode': settings_tem['end_of_episode'], 'fake_ua':settings_tem['fake_ua']}]
        pool = Pool(2)
        result = pool.map(crawling_comic, settings_all)
        pool.close()
        pool.join()
    else: crawling_comic(settings_tem)
    print("共花费时间", end='')
    print(time.time() - start_time)
