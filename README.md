# ATRI-BOT

目前该项目主要用于搬运推特发送到微博的机器人BOT

运行项目需要准备以下文件

---
### atri_bot/twitter/config.py

config.py里需要放入你的推特抓取API

字段：

> consumer_key = ""
> 
> consumer_secret = ""
> 
> access_token = ""
> 
> access_token_secret = ""
> 
> client_id = ""
> 
> client_secret = ""
> 
> bearer_token = ""
> 
> #代理端口
> 
> proxy = ""

---

### data_processing/datri_bot_db.json

此文件用于MySQL数据库文件连接

可以用项目中的atribot.sql来创建数据库

字段

> {
> 
>        "host": "localhost",
> 
>        "port": 3306,
> 
>        "user": "root",
> 
>        "password": "",
> 
>        "database": "atribot", # 数据库名指定atribot
> 
>        "autocommit": true
> 
> }

---

### data_processing/spider_user.txt

此文件用于维护收集推特用户列表，需要填写推特用户id

e.g

> @TorinoAqua
> 
> @Bren_biren
> 
> @ainy120
> 
> @hanekoto2424
> 
> @canvas2929

---

## 项目运行

在 https://m.weibo.cn 登录你的微博账号

寻找m.weibo.cn的文件并提取其中的cookies

并保存在data_processing/setting.py中的WEIBO_COOKIES中

在运行前需要在data_processing/common/setting.py中修改你需要保存媒体文件的路径

> PROFILE_IMAGE_PATH 是头像存储路径
> 
> MEDIA_IMAGE_PATH 是推文视频存储路径
> 
> MEDIA_VIDEO_PATH 是推文视频存储路径

并根据项目安装对应库

运行star.py即可