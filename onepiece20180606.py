# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
import requests
import os
from reportlab.pdfgen import canvas
import unittest
import re
import shutil
from time import sleep

class scrapytest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 爬取设置
        while True:
            cls.title = int(input('开始爬取的话数\n'))
            if cls.title > 0:
                break
            else:print("话数必须大于0")
        while True:
            cls.end_of_episode = int(input('结束话数\n'))
            if cls.end_of_episode >= cls.title:
                break
            else:print("结束集数必须大于等于开始集数")
        comic_you_need = '505430/'  # 海贼王 505430/
        episode = 'cid/' + str(cls.title)
        
        # 浏览器设置
        chrome_options = Options()
        #chrome_options.add_argument('--headless')
        #chrome_options.add_argument('--disable-gpu')
        cls.browser = webdriver.Chrome(chrome_options=chrome_options)
        #cls.browser.implicitly_wait(10)

        url = "http://ac.qq.com/Comic/ComicInfo/id/" + comic_you_need

        cls.browser.get(url)
        ac = WebDriverWait(cls.browser,10).until(expected_conditions.element_to_be_clickable((By.LINK_TEXT,"开始阅读"))).click()
        #ActionChains(cls.browser).move_to_element(ac).click(ac).perform()
        url = url.replace('/ComicInfo','View/index')
        print(url+episode)
        cls.browser.get(url+episode)

    def test_scrapy_comic(self):
        print('\n--------------------')

        while self.title <= self.end_of_episode:
            try:
                cheak = WebDriverWait(self.browser,2).until(expected_conditions.visibility_of_element_located((By.PARTIAL_LINK_TEXT,"很遗憾，该漫画不存在或章节已被删除，我们为您推荐了下面一些漫画")))
            except :
                pass
            else:
                print("很遗憾，该漫画不存在或章节已被删除，或许是漫画尚未更新到该集。")
                quit_tip = int(input("是否退出？1.是  2.否\n"))
                if quit_tip == 1:
                    break
                else:
                    self.title += 1
                    continue
                
            try:
                right_title = int(re.search("第\d+话",WebDriverWait(self.browser,2).until(expected_conditions.visibility_of_element_located((By.CLASS_NAME,"title-comicHeading"))).text).group(0)[1:-1])
            except :
                print("无法获取当前正确的话数")
            
            if not right_title < self.title:                 
                print('正在爬取第%d话'%right_title)
                
                pic_name = 0
                comicContain = self.browser.find_element_by_id('comicContain')
                comic = comicContain.find_elements_by_tag_name('li')

                path = 'D:\\tem\\' + str(right_title) + '\\'
                c = canvas.Canvas('D:\\tem\\'+str(right_title)+'.pdf', pagesize = (822,1200))
                folder = os.path.exists(path)
                if not folder:  #判断是否存在文件夹如果不存在则创建为文件夹  
                    os.makedirs(path)

                for i in comic[0:-2]:
                    if i.get_attribute('class') == 'main_ad_top' or i.get_attribute('class') == 'main_ad_bottom':
                        continue
                    self.browser.execute_script("arguments[0].scrollIntoView();", i) #拖动到可见的元素去
                    img = i.find_element_by_tag_name('img')
                    while img.get_attribute('src') == '//ac.gtimg.com/media/images/pixel.gif':
                        img = i.find_element_by_tag_name('img')

                    if pic_name < 10:
                        pic_all_name = str(path) +  '0' + str(pic_name) + '.png'
                    else:
                        pic_all_name = str(path) + str(pic_name) + '.png'

                    
                    src = requests.get(img.get_attribute('src')).content
                    with open(pic_all_name, 'wb') as file:
                        file.write(src)

                    pic_name += 1
                    # 把图片画在画布上
                    c.drawImage(pic_all_name, 0, 0, 822, 1200)
                    # 结束当前页并新建页
                    c.showPage()

                # 生成pdf
                c.save()
                shutil.rmtree(path)
                print("完成！")
                print('--------------------')

                self.title += 1
                try:
                    nextpage = self.browser.find_element_by_id('next_item').click() # 模拟用户点击下一话
                except :
                    print("已到最后一话，第%d话。"%right_title)
                    break
            else:
                self.browser.get("http://ac.qq.com/ComicView/index/id/505430/cid/" + str(2*self.title-right_title))
            

    @classmethod
    def tearDownClass(self):
        self.browser.quit()

if __name__ == '__main__':
    unittest.main(verbosity=2)
