# onepiece
用以爬取腾讯动漫上的航海王漫画

chromedriver.exe必须和脚本放在同一目录下
理论上支持腾讯动漫所包括的全部动漫，但现在在代码层面只设置了爬取航海王的
设置隐式等待时间为10s，当鼠标拖拽到具体图片时，会暂停（sleep）2s，保证图片加载完成，同时防止被反

不知道什么时候才做的改进方案
改用headless chrome，使得爬取时，更节省资源
记录上一次爬取的位置，从而可以在意外中断（关机）之后，继续爬取
结合上一条，做到章节更新的检测
提供更丰富的细节反馈，更简单地发现爬虫爬取数据时的异常

2018.6.6更新
将隐式等待时间更改为显式等待时间，当图片一准备好，马上开始下载，速度大为提升
经测试，原始版本爬取海贼王第904，905话，共用时150s，改进后用时48s

2018.6.9更新
在让小伙伴给我测试的时候，他提到，要是我没有chrome怎么办，这确实是我没有考虑到的问题
创建chrome的webdriver失败之后，会尝试创建IE的webdriver（未测试）
可以选择爬取之后的图片储存位置
