import uvicorn, requests, json, random, httpx, asyncio, urllib, re
import numpy as np
import sympy as sp
from fastapi import FastAPI, Request
import matplotlib.pyplot as plt

app = FastAPI()
url = "http://127.0.0.1:3000/" #server port 服务器接口默认3000
imageurl = "https://derpibooru.org/api/v1/json/search/images" #derpibooru api
headers = {
   'Content-Type': 'application/json'
}

common_alias = [
    ['紫悦','暮','ts'],
    ['云宝','rd'],
    ['碧琪','pp'],
    ['柔柔','蝶','fs'],
    ['珍奇','瑞','rr'],
    ['嘉','aj','杰克'],
    ['星光','熠'],
    ['余晖','师姐'],
    ['宇宙','太阳'],
    ['月亮','露娜'],
    ['音韵'],
    ['穗龙']
]

other_alias = [
    ['twilight'],
    ['rainbow','黛西'],
    ['萍琪','pinkie'],
    ['fluttershy'],
    ['rarity'],
    ['applejack'],
    ['starlight'],
    ['sunset'],
    ['大','塞','celestia'],
    ['luna'],
    ['cadance'],
    ['派克','spike']
]

tags = ['ts','rd','pp','fs','rarity','aj','starlight+glimmer','sunset+shimmer','celestia','luna','cadance','spike']

#make dict for alias search 创建同义词检索
dictionary = {}
for i in range(len(tags)):
    dictionary = dictionary | dict.fromkeys(common_alias[i],tags[i])
for j in range(len(tags)):
    dictionary = dictionary | dict.fromkeys(other_alias[i],tags[i])

#load data for total number of images for page number calculation
#加载不同检索情况下找到的图片总数以便确定可以选择的最大页码数
with open('data.json','r') as file:
    pages = json.load(file)

#load bot id 加载机器人自己的qq号 这里没有做git需要自己添加self.json文件 数据格式为字符串
with open('self.json','r') as file:
    self_id = json.load(file)

#load local server path in the form 'file://[absolute path]' 加载本地服务端路径 格式为'file://[绝对路径]'
with open('path.json','r') as file:
    local = json.load(file)

async def send_txtimg(group_id, txt='', img=''):
    """send text in str or image in url or file path 发送文字或图片 图片为链接或文件路径格式"""
    async with httpx.AsyncClient() as client:
        message = []
        if txt:
            txt_msg = {'type':'text','data':{'text':txt}}
            message.append(txt_msg)
        if img:
            img_msg = {'type':'image','data':{'file':img}}
            message.append(img_msg)
        payload = {
            "group_id": group_id,
            "message": message
        }
        try:
            response = await client.post(url + "send_group_msg", json=payload, timeout=60.0)
        except (httpx.ConnectTimeout, httpx.ReadTimeout):
            response = await send_txtimg(group_id,txt='连接/读取超时(>60s)，请重试')
        print(response.text)
        return response


async def scrape_img(group_id, url, page, save=False):
    """scrape images for derpibooru.org 从derpibooru获取图片"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            apidata = await client.get(url + f'&page={page}')
            apijson = apidata.json()
            if 'error' in apijson:
                if apijson['error'] == 'Expected a term.': #wrong query 词条错误
                    response = await send_txtimg(group_id,txt='搜索词条错误，请重试')
                if apijson['error'] == 'Internal Error': #http 500
                    response = await send_txtimg(group_id,txt='图片服务器出错，请稍后重试')
                return
            if apijson['total'] == 0: #no image found 该词条未找到任何图片
                response = await send_txtimg(group_id,txt='未找到相应图片，请重试')
                return
            if len(apijson['images']) == 0: #found images, but the page number is too large 选择的页码数过大
                await scrape_img(group_id, url, random.randint(1,(apijson['total']//15)+1),save)
                return
            global pages
            if url not in pages and save: #save the total number of images found if save is True
                #在save变量为True时存储找到的图片总数以便下次计算可以选择的最大页码数
                pages[url] = apijson['total']
            images = apijson['images']
            image_num = random.randint(0,len(images)-1)
            sourceurl = images[image_num]['representations']['medium'] #scrape the medium sized image 默认中等大小图片
            response = await send_txtimg(group_id,img=sourceurl) #send image 发送图片
            status = response.json()
            i = 0
            while status['status'] == 'failed' and i < 3: 
                #if image download failed, try three more times 图片下载失败时默认尝试三次
                i += 1
                response = await send_txtimg(group_id,txt=f'图片下载失败，正在尝试重新下载({i}/3)')
                response = await send_txtimg(group_id,img=sourceurl)
                status = response.json()
            if status['status'] == 'failed': #if still failed, send error message 如果三次仍下载失败 返回错误信息
                response = await send_txtimg(group_id,txt='图片下载失败，请重试')
        except KeyError:
            print('Key not Found!')
        except json.JSONDecodeError:
            response = await send_txtimg(group_id,txt='请求过于频繁，请一分钟后再试')
            print(response.text)
        except (httpx.ConnectTimeout, httpx.ReadTimeout):
            response = await send_txtimg(group_id,txt='连接/读取超时(>10s)，请重试')


async def pony_img(group_id,msg):
    """generate url for image scraping 生成获取图片的链接"""
    url = imageurl + "?sd=desc&sf=wilson_score&per_page=15&q=safe+%26%26+pony+%26%26+-human" 
    #pre-defined tags: safe && pony && -human; pre-defined order: descending Wilson score 预设tag 以Wilson score降序排列
    if '搜索' in msg: #start a query 开始图片搜索
        msg = msg.replace('搜索','')
        if msg:
            msg = msg.strip()
            url += '+%26%26+' + urllib.parse.quote_plus(msg)
        save = False #do not save total number of images found for a query 搜索图片时不存储找到的图片总数以节约存储空间
    else: #pre-defined keywords 如不选择搜索功能则寻找预设关键词
        tags_copy = tags[:]
        if 'm6' in msg: #support the keyword for mane 6 给m6设定的关键词
            msg = msg.replace('m6','tsrdppfsrraj')
        for key in dictionary.keys():
            if key in msg:
                url += '+%26%26+'+dictionary[key]
                tags_copy.remove(dictionary[key])
        if len(tags_copy) != len(tags):
            url += '+%26%26+-' + '+%26%26+-'.join(tags_copy)
            #eliminate other main characters that are not mentioned 其他未在关键词中出现的主角全部加上负向tag以突显选中的角色
        else:
            response = await send_txtimg(group_id,txt='未检测到关键词，默认随机小马图')
        save = True
    print(url)
    if url in pages: #see if the total number of images is saved in data 如果图片总数已经储存
        try:
            page = random.randint(1,pages[url]//150) #only get the first 10% to ensure quality 选择前10%的图片以保证质量
        except ValueError:
            page = 1
    else:
        page = random.randint(1,100) #if not saved, randomly choose from 1 to 100 for the page number 
        #如果未储存 在1-100中随机选择页码
    await scrape_img(group_id, url, page, save)


def tonp(msg):
    """convert expressions into valid numpy codes 把表达式转换为numpy语言"""
    msg = msg.strip()
    msg = msg.replace('^','**')
    msg = re.sub(r'(true|false)',lambda m: m.group(0).title(),msg) # true/false -> True/False
    msg = msg.replace('mod','%')
    msg = msg.replace('ln','log')
    msg = re.sub(r'(\))([a-z\(])',r'\1*\2',msg) # sin(pi)cos(pi)(1+2) -> sin(pi)*cos(pi)*(1+2)
    msg = re.sub(r'(?<![a-z0-9])(\d+e?\d*)([a-z\(])',r'\1*\2',msg) # 10(1+2sin(pi)) -> 10*(1+2*sin(pi))
    msg = msg.replace('lg','log10')
    msg = re.sub(r'(?<=[a-z0-9\)])\s+(?=[a-z0-9\(])',r'*',msg) # 2 x (x+y) (y-x) -> 2*x*(x+y)*(y-x)
    msg = re.sub(r'(?<![a-z])i',r'j',msg)
    msg = re.sub(r'(?<![a-z0-9])j',r'1j',msg)
    msg = re.sub(r'(?<![A-Za-z0-9])([a-z\.]+)',r'np.\1',msg) # pi -> np.pi
    msg = re.sub(r'\*?(np\.)?(and|or|not)\*?',r' \2 ',msg) # np.and -> and
    msg = re.sub(r'\*np\.(e\d+)',r'\1',msg) # 5*np.e2 -> 5e2
    return msg


async def calculator(group_id,msg):
    """do numerical calculations 做数值计算"""
    msg = tonp(msg)
    print(msg)
    try:
        result = eval(msg)
        if msg[:8] != 'np.round' and not isinstance(result, bool):
            result = np.round(result,5) #round to 5 digits by default 默认精确到小数点后5位
    except AttributeError:
        response = await send_txtimg(group_id,txt='函数名错误，请重新输入')
    except NameError:
        response = await send_txtimg(group_id,txt='含有未知变量，请重新输入')
    except SyntaxError:
        response = await send_txtimg(group_id,txt='表达式错误，请重新输入')
    except TypeError:
        response = await send_txtimg(group_id,txt='函数参数错误，请重新输入')
    except ZeroDivisionError:
        response = await send_txtimg(group_id,txt='0不可作为除数，请重新输入')
    except:
        response = await send_txtimg(group_id,txt='计算错误，请重新输入')
    else:
        response = await send_txtimg(group_id,txt=f'结果为{result}')


def tosp(msg):
    """convert expressions into valid sympy codes 把表达式转换为sympy语言"""
    msg = msg.strip()
    msg = msg.replace('^','**')
    msg = re.sub(r'(\))([a-z\(])',r'\1*\2',msg) # sin(pi)cos(pi)(1+2) -> sin(pi)*cos(pi)*(1+2)
    msg = re.sub(r'(?<![a-z0-9])(\d+e?\d*)([a-z\(])',r'\1*\2',msg) # 10(1+2sin(pi)) -> 10*(1+2*sin(pi))
    msg = re.sub(r'(?<=[a-z0-9\)])\s+(?=[a-z0-9\(])',r'*',msg) # 2 x (x+y) (y-x) -> 2*x*(x+y)*(y-x)
    msg = re.sub(r'log(\d+)\((.*)\)',r'log(\2,\1)',msg) # log2(x) -> log(x,2)
    msg = re.sub(r'lg\((.*)\)',r'log(\1,10)',msg) # lg(x) -> log(x,10)
    msg = re.sub(r'(?<![a-z0-9])(i|e)(?![a-z0-9])',lambda m: m.group(1).upper(),msg) # i/e -> I/E
    return msg


async def algebra(group_id,msg,det):
    """solve algebra problems 解决代数问题"""
    msg = tosp(msg)
    print(msg)
    try:
        match det:
            case '化简':
                result = sp.simplify(msg)
            case '展开':
                result = sp.expand(msg)
            case '分解':
                result = sp.factor(msg)
            case '解方程': #input format: (equation1, equation2, ...),(var1, var2, ...)
                #输入格式必须为(方程1, 方程2, ...),(变量1, 变量2, ...)
                if re.search(r'\)$',msg): #for multivariable equations 多变量方程
                    arg = re.split(r'(\(.*\),)',msg)[1:]
                    arg[0] = re.sub(r'=(.*?)(,|\)$)',r'-(\1)\2',arg[0][:-1])
                    for i in range(len(arg)):
                        arg[i] = tuple(arg[i][1:-1].split(','))
                elif re.search(r'^\(',msg): #for multiple single-variable equations as (equation1, equation2, ...),var1 
                    #多个单变量方程 (方程1, 方程2, ...),变量1
                    arg = re.split(r'(\(.*\),)',msg)[1:]
                    arg[0] = re.sub(r'=(.*?)(,|\)$)',r'-(\1)\2',arg[0][:-1])
                    arg[0] = tuple(arg[0][1:-1].split(','))
                else: #for a single single-variable equation as equation1, var1 单个单变量方程 方程1,变量1
                    arg = msg.split(',')
                    arg[0] = re.sub(r'=(.*)',r'-(\1)',arg[0])
                result = sp.solve(*arg,dict=True)
            case '代入': #input format: expression,var1=val1,var2=val2,...  输入格式必须为 表达式,变量1=值1,变量2=值2,...
                arg = msg.split(',')
                value = {n.split('=')[0]:n.split('=')[1] for n in arg[1:]}
                result = sp.simplify(arg[0]).subs(value)
            case _:
                response = await send_txtimg(group_id,txt='关键词错误，请重新输入')
                return
        response = await send_txtimg(group_id,txt=f'结果为{result}')
    except:
        response = await send_txtimg(group_id,txt='运算错误，请重新输入')


async def calculus(group_id,msg,det):
    """solve calculus problems 解决微积分问题"""
    msg = tosp(msg)
    print(msg)
    try:
        match det:
            case '极限': #input format: expr,var,val+/-  输入格式为 表达式,变量,值[+/-]
                arg = msg.split(',')
                arg[-1] = arg[-1].replace('inf','oo')
                if arg[-1][-1] == '+' or arg[-1][-1] == '-':
                    result = sp.Limit(*arg[:-1],arg[-1][:-1],dir=arg[-1][-1]).doit()
                else:
                    result = sp.Limit(*arg).doit()
            case '求导': #input format: expr,var,order 输入格式为 表达式,变量=值,次数
                arg = msg.split(',')
                if '=' in arg[1]:
                    arg[1] = arg[1].replace('inf','oo').split('=')
                    value = {arg[1][0]:arg[1][1]}
                    arg[1] = arg[1][0]
                    result = sp.Derivative(*arg).doit().subs(value)
                else:
                    result = sp.Derivative(*arg).doit()
            case '积分':
                arg = msg.split(',')
                if len(arg) == 2: #input format: expr,var 输入格式为 表达式,变量
                    result = sp.Integral(arg[0],sp.Symbol(arg[1])).doit()
                else: #input format: expr,var,lower_limit,upper_limit 输入格式为 表达式,变量,上界,下界
                    arg[-2] = arg[-2].replace('inf','oo')
                    arg[-1] = arg[-1].replace('inf','oo')
                    result = sp.Integral(arg[0],tuple(arg[1:])).doit()
            case _:
                response = await send_txtimg(group_id,txt='关键词错误，请重新输入')
                return
        response = await send_txtimg(group_id,txt=f'结果为{result}')
    except:
        response = await send_txtimg(group_id,txt='运算错误，请重新输入')


async def plot(group_id,msg,det):
    """make plots of functions 给函数画图像
    input format: [plt function1:]arg1,arg2,...;[plt function2:]arg1,arg2,...;...
    输入格式为 [plt函数1:]参数1,参数2,...;[plt函数2:]参数1,参数2,...;..."""
    msg = msg.strip()
    msg = re.sub(r'(true|false)',lambda m: m.group(0).title(),msg)
    arg = re.split(r';\s*',msg)
    code = 'plt.clf()\n'
    try:
        for i in range(len(arg)):
            if ':' not in arg[i]: #when no function name is provided, the default function is assumed based on det
                #如未提供函数名 则默认为det决定的函数
                match det:
                    case '图':
                        if arg[i][0] == '[': #when arguments are a list of x and y coordinantes 参数为含有x和y坐标的列表
                            code += 'plt.plot(' + arg[i] + ')\n'
                        else: #when arguments are in the form of 
                            #expression,var,domain_lower_bound,domain_upper_bound[,num_points][,more_settings]
                            #参数形式为 表达式,自变量,定义域下界,定义域上界[,点数量][,更多设置]
                            kw = arg[i].split(',')
                            if len(kw) < 5 or not re.search(r'\d',kw[4]) or '=' not in kw[4]:
                                kw.insert(4,'100')
                            var = f'linspace({kw[2]},{kw[3]},{kw[4]})'
                            kw[0] = tonp(kw[0].replace(kw[1],var))
                            code += 'plt.plot(' + tonp(var) + ',' + kw[0]
                            if len(kw) > 5:
                                code += ','.join(kw[5:])
                            code += ')\n'
                    case _:
                        response = await send_txtimg(group_id,txt='关键词错误，请重新输入')
                        return
            else: #when function name is provided, call the function directly 如提供函数名 则直接调用该函数
                arg[i] = arg[i].replace(':','(')
                if 'figure' in arg[i]: #configuration of the figure should be placed in the first place
                    #关于图像figure的设定函数必须优先调用
                    code = 'plt.' + arg[i] + ')\n' + code
                else:
                    code += 'plt.' + arg[i] + ')\n'
        if 'label' in msg and 'legend' not in msg:
            code += 'plt.legend()\n'
        print(code)
        exec(code + "plt.savefig('plot.png')")
        response = await send_txtimg(group_id,img=f'{local}/plot.png')
    except:
        response = await send_txtimg(group_id,txt='图像绘制失败，请重新输入')


@app.post("/")
async def root(request: Request):
    data = await request.json()  #get events 获取事件数据
    print(data)
    try:
        message = data['message']
    except KeyError:
        print('Key not Found!')
    else:
        if message[0]['type'] == 'at' and message[0]['data']['qq'] == self_id: #when being "at" 当被at时
            msg = message[-1]['data']['text'].lower()
            if '画' in msg:
                msg = msg.replace('画','')
                det = re.search(r'^[^a-z0-9\(\[]+',msg).group().strip()
                msg = msg.replace(det,'')
                await plot(data['group_id'],msg,det)
                return '绘制图像'
            if '图' in msg:
                msg = msg.replace('图','')
                await pony_img(data['group_id'],msg)
                return '图片发送'
            if '计算' in msg:
                msg = msg.replace('计算','')
                await calculator(data['group_id'],msg)
                return '数值计算'
            search = re.search(r'(化简|分解|解方程|代入|展开)',msg)
            if search:
                det = search.group()
                msg = msg.replace(det,'')
                await algebra(data['group_id'],msg,det)
                return '代数运算'
            search = re.search(r'(极限|求导|积分)',msg)
            if search:
                det = search.group()
                msg = msg.replace(det,'')
                await calculus(data['group_id'],msg,det)
                return '微积分运算'
    return {}



if __name__ == "__main__":
    try:
        uvicorn.run(app, port=3090) #post(webhook) port 机器人接受到消息后用于推送事件的接口
    finally:
        with open('data.json', 'w', encoding='utf-8') as f: #save total number of images when closing 程序关闭时保存图片数
            json.dump(pages, f, indent=4)