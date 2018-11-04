# Jerry1014/Comic-Onepiece-Crawler
- 爬取腾讯动漫上的漫画
- 环境：py3    第三方库：selenium，requests，pandas

## 使用步骤
- 1.下载py脚本
- 2.如果你有chrome浏览器的话，仅需下载chromedriver.exe
- 3.否则，根据你的电脑下载对应的IEDriverServer(32/64).exe   （在将来支持）
  - 注意：XXX.exe必须和脚本放在同一目录下
- 4.打开脚本

## 使用说明
- 配置文件会在第一次运行时被创建，在当前工作目录。
- 并会默认会从第0集开始爬取，可手动关闭，修改配置文件，重新打开脚本爬取
- 也可以在配置文件中修改要爬取的动漫，默认为海贼王   （未全部测试）
***
- 爬取的图片会保存在D:\tem下，可通过配置文件修改
- 建议使用Kindle Comic Converter生成mobi漫画，在kindle上看会更舒服哦
***
- 通过邮件将爬取结果发送到我的邮箱 （可修改代码实现发送到自己的邮箱，通过配置文件修改的方式会在将来被支持）

## 碎碎念
- 使用headless chrome，爬取更省资源（吧）
- 一共会启动三个进程，主进程在自己爬取漫画之前，还负责任务的分配，每个进程对图片的爬取则会用多线程
- 配置文件中还有一项为最后爬取的集数，爬虫会将正常结束的最大集数写入，且在运行爬虫是，可以选择按照最后爬取的集数再往下爬取4集
- 新增多进程爬取，在选择集数时，会在后台打开两个浏览器进程，爬取更快更省时间
- 一切通过配置文件配置，没有人为的选择和操作，适用于计划任务

## 等哪天我不再摸鱼的时候
- 1.在此版本的基础上，添加日志功能/没有丑丑的命令行输出，将整个过程用更丰富的形式以邮箱的方式发送给使用者，特别是出错信息（自动化爬取方向）
- 2.在此版本的基础上，结合上上上版本，完成一个可选择可设置的，更丰富灵活的爬虫，可能会加入图形界面（人工爬取方向）
