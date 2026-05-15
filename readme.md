# Intro 简介

This project is a HTTP server code for qq bots based on [llonebot](https://luckylillia.com/). Currently the server can scrapy pony images, do numerical calculations, and solve simple algebra and calculus problems depending on what key words a user gives to the bot. More utilities and functions are to be developed. In theory, the code can be slightly modified to support other bots that can communicate with http protocols such as [NapCat](https://napneko.github.io/).

此项目为基于[llonebot](https://luckylillia.com/)的qq机器人服务端代码。目前该服务端可以根据用户提供的关键词进行小马图片抓取、数值计算以及求解简单的代数和微积分问题。更多的功能将在后期相继开发。理论上来说，只需要通过一些简单的修改就可以让此代码适配其他可以用http协议交互的机器人（例如[NapCat](https://napneko.github.io/)）。

# Environment 运行环境

Everything is written in python 3.12. You can refer to `packages.txt` to find out all the python packages required for this project. In theory, just make sure all the packages listed are up-to-date and the code should work fine.

所有代码均使用python 3.12编写。可以查看`packages.txt`以获悉此项目需要安装的所有python包。理论上来说，只要文件里列举的包都是最新版本，项目代码就可以正常运行。

# User's guide 项目安装步骤

1. Download and install llbot by following the [instructions](https://luckylillia.com/guide/choice_install).
1. 根据[教程](https://luckylillia.com/guide/choice_install)下载并安装llbot。
2. After the first successful login via llbot, configure the bot by following the [instructions](https://luckylillia.com/guide/config). The most important configurations are those for the http server port (default 3000) and webhook port (default 3090). If you want to change the default port numbers, you need to change the server code. The bot will first post events via webhook, and the server will receive them and do something (get or post) via the http server port.
2. 在第一次用llbot成功登录后，根据[教程](https://luckylillia.com/guide/config)配置机器人，其中关于http服务端接口（默认3000）和webhook接口（默认3090）的配置尤为重要。如果想要更改默认的接口码，则需要在该项目代码的相应部分同时进行修改。机器人会先通过webhook推送在群中检测到的事件，然后服务端会接收这些事件并通过http接口进行相应的操作。
3. Add `self.json` with the bot's qq id specified as a python string in it.
3. 添加`self.json`文件并在里面以python字符串的形式写明机器人的qq号。
4. Run both the llbot and the server code.
4. 同时运行llbot机器人和服务端代码。

# More info 更多信息

You can refer to the [documents](https://luckylillia.com/guide/introduction) for other things llbot can do. If you want to add more functions into the server code, this [page](https://api.luckylillia.com/doc-7202281) can be helpful. The bot can also be linked to ai agents such as [Astrbot](https://luckylillia.com/guide/install_astrbot).

有关llbot的更多信息可以参考[文档](https://luckylillia.com/guide/introduction)。如果想在该服务端代码中添加更多实用功能，查看此[网页](https://api.luckylillia.com/doc-7202281)或许会有帮助。该机器人也支持接入ai代理（例如[Astrbot](https://luckylillia.com/guide/install_astrbot)）。