import uvicorn, requests, json, random, httpx, asyncio, urllib, re
import numpy as np
import sympy as sp
from fastapi import FastAPI, Request

app = FastAPI()
url = "http://127.0.0.1:3000/"
imageurl = "https://derpibooru.org/api/v1/json/search/images"
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

dictionary = {}
for i in range(len(tags)):
    dictionary = dictionary | dict.fromkeys(common_alias[i],tags[i])
for j in range(len(tags)):
    dictionary = dictionary | dict.fromkeys(other_alias[i],tags[i])

with open('data.json','r') as file:
    pages = json.load(file)

with open('self.json','r') as file:
    self_id = json.load(file)

async def send_txtimg(group_id, txt='', img=''):
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
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            apidata = await client.get(url + f'&page={page}')
            apijson = apidata.json()
            if 'error' in apijson:
                if apijson['error'] == 'Expected a term.':
                    response = await send_txtimg(group_id,txt='搜索词条错误，请重试')
                if apijson['error'] == 'Internal Error':
                    response = await send_txtimg(group_id,txt='图片服务器出错，请稍后重试')
                return
            if apijson['total'] == 0:
                response = await send_txtimg(group_id,txt='未找到相应图片，请重试')
                return
            if len(apijson['images']) == 0:
                await scrape_img(group_id, url, random.randint(1,(apijson['total']//15)+1),save)
                return
            global pages
            if url not in pages and save:
                pages[url] = apijson['total']
            images = apijson['images']
            image_num = random.randint(0,len(images)-1)
            sourceurl = images[image_num]['representations']['medium']
            response = await send_txtimg(group_id,img=sourceurl)
            status = response.json()
            i = 0
            while status['status'] == 'failed' and i < 3:
                i += 1
                response = await send_txtimg(group_id,txt=f'图片下载失败，正在尝试重新下载({i}/3)')
                response = await send_txtimg(group_id,img=sourceurl)
                status = response.json()
            if status['status'] == 'failed':
                response = await send_txtimg(group_id,txt='图片下载失败，请重试')
        except KeyError:
            print('Key not Found!')
        except json.JSONDecodeError:
            response = await send_txtimg(group_id,txt='请求过于频繁，请一分钟后再试')
            print(response.text)
        except (httpx.ConnectTimeout, httpx.ReadTimeout):
            response = await send_txtimg(group_id,txt='连接/读取超时(>10s)，请重试')


async def pony_img(group_id,msg):
    url = imageurl + "?sd=desc&sf=wilson_score&per_page=15&q=safe+%26%26+pony+%26%26+-human"
    if '搜索' in msg:
        msg = msg.replace('搜索','')
        if msg:
            msg = msg.strip()
            url += '+%26%26+' + urllib.parse.quote_plus(msg)
        save = False
    else:
        tags_copy = tags[:]
        if 'm6' in msg:
            msg = msg.replace('m6','tsrdppfsrraj')
        for key in dictionary.keys():
            if key in msg:
                url += '+%26%26+'+dictionary[key]
                tags_copy.remove(dictionary[key])
        if len(tags_copy) != len(tags):
            url += '+%26%26+-' + '+%26%26+-'.join(tags_copy)
        else:
            response = await send_txtimg(group_id,txt='未检测到关键词，默认随机小马图')
        save = True
    print(url)
    if url in pages:
        try:
            page = random.randint(1,pages[url]//150)
        except ValueError:
            page = 1
    else:
        page = random.randint(1,100)
    await scrape_img(group_id, url, page, save)


async def calculator(group_id,msg):
    msg = msg.strip()
    msg = msg.replace('^','**')
    msg = re.sub(r'(true|false)',lambda m: m.group(0).title(),msg)
    msg = msg.replace('mod','%')
    msg = msg.replace('ln','log')
    msg = re.sub(r'(\))([a-z\(])',r'\1*\2',msg)
    msg = re.sub(r'(?<![a-z0-9])(\d+)([a-z\(])',r'\1*\2',msg)
    msg = msg.replace('lg','log10')
    msg = re.sub(r'(?<=[a-z0-9\(\)]) (?=[a-z0-9\(\)])',r'*',msg)
    msg = re.sub(r'(?<![a-z])i',r'j',msg)
    msg = re.sub(r'(?<![a-z0-9])j',r'1j',msg)
    msg = re.sub(r'(?<![A-Za-z0-9])([a-z]+)',r'np.\1',msg)
    msg = re.sub(r'\*?(np\.)?(and|or|not)\*?',r' \2 ',msg)
    print(msg)
    try:
        result = eval(msg)
        if msg[:8] != 'np.round' and not isinstance(result, bool):
            result = np.round(result,5)
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


async def algebra(group_id,msg,det):
    msg = msg.strip()
    msg = msg.replace('^','**')
    msg = re.sub(r'(\))([a-z\(])',r'\1*\2',msg)
    msg = re.sub(r'(?<![a-z0-9])(\d+)([a-z\(])',r'\1*\2',msg)
    msg = re.sub(r'(?<=[a-z0-9\(\)]) (?=[a-z0-9\(\)])',r'*',msg)
    msg = re.sub(r'log(\d+)\((.*)\)',r'log(\2,\1)',msg)
    msg = re.sub(r'lg\((.*)\)',r'log(\1,10)',msg)
    msg = re.sub(r'(?<![a-z])(i|e)(?![a-z])',lambda m: m.group(1).upper(),msg)
    print(msg)
    try:
        match det:
            case '化简':
                result = sp.simplify(msg)
            case '展开':
                result = sp.expand(msg)
            case '分解':
                result = sp.factor(msg)
            case '解方程':
                if re.search(r'\)$',msg):
                    arg = re.split(r'(\(.*\),)',msg)[1:]
                    arg[0] = re.sub(r'=(.*?)(,|\)$)',r'-(\1)\2',arg[0][:-1])
                    for i in range(len(arg)):
                        arg[i] = tuple(arg[i][1:-1].split(','))
                else:
                    arg = msg.split(',')
                    arg[0] = re.sub(r'=(.*)',r'-(\1)',arg[0])
                result = sp.solve(*arg,dict=True)
            case '代入':
                arg = msg.split(',')
                value = {n.split('=')[0]:n.split('=')[1] for n in arg[1:]}
                result = sp.simplify(arg[0]).subs(value)
            case _:
                response = await send_txtimg(group_id,txt='关键词错误，请重新输入')
                return
        response = await send_txtimg(group_id,txt=f'结果为{result}')
    except:
        response = await send_txtimg(group_id,txt='运算错误，请重新输入')


@app.post("/")
async def root(request: Request):
    data = await request.json()  # 获取事件数据
    print(data)
    try:
        message = data['message']
    except KeyError:
        print('Key not Found!')
    else:
        if message[0]['type'] == 'at' and message[0]['data']['qq'] == self_id:
            msg = message[-1]['data']['text'].lower()
            if '图' in msg:
                msg = msg.replace('图','')
                await pony_img(data['group_id'],msg)
                return '图片发送'
            if '计算' in msg:
                msg = msg.replace('计算','')
                await calculator(data['group_id'],msg)
                return '数值计算'
            match = re.search(r'(化简|分解|解方程|代入)',msg)
            if match:
                det = match.group()
                msg = msg.replace(det,'')
                await algebra(data['group_id'],msg,det)
                return '代数运算'
    return {}



if __name__ == "__main__":
    try:
        uvicorn.run(app, port=3090)
    finally:
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(pages, f, indent=4)