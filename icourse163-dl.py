# -*- coding: utf-8 -*-
import requests
from http.cookies import SimpleCookie
import random
import re
from urllib.parse import unquote

# -*- Config
# Warning:Before start ,You should fill in these forms.
# Session
httpSessionId = ''
# cookies
raw_cookies = ''
# Course url (with key "tid")
url = ''
#Download Docs Immediately(True or False)
wdimmediate = False
# Post Header(Don't change)
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.87 Safari/537.36',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.8',
    'Content-Type': 'text/plain',
}

# -*- Api
# Arrange Cookies from raw
cookie = SimpleCookie()
cookie.load(raw_cookies)
cookies = {}
for key, morsel in cookie.items():
    cookies[key] = morsel.value


# getLessonUnitLearnVo (This funciton will return a dict with download info)     #延迟
def getLessonUnitLearnVo(contentId, id, contentType):
    # prepare data and post
    payload = {
        'callCount': 1,
        'scriptSessionId': '${scriptSessionId}' + str(random.randint(0, 200)),
        'httpSessionId': httpSessionId,
        'c0-scriptName': 'CourseBean',
        'c0-methodName': 'getLessonUnitLearnVo',
        'c0-id': 1,
        'c0-param0': contentId,  # 1004102109,
        'c0-param1': contentType,
        'c0-param2': 0,
        'c0-param3': id,  # 1002437570,
        'batchId': random.randint(1000000000000, 20000000000000)  # 1479741724609
    }
    cs_url = 'http://www.icourse163.org/dwr/call/plaincall/CourseBean.getLessonUnitLearnVo.dwr'

    rdata = requests.post(cs_url, data=payload, headers=headers, cookies=cookies).text
    print(rdata)
    info = {}  # info.clear()
    # Sort data depend on it's contentType into dict info
    if contentType == 1:  # 视频
        info['contentType'] = 1
        info['videoImgUrl'] = str(re.search(r's\d+.videoImgUrl="(.+?)";', rdata).group(1))

        if rdata.find('flvHdUrl="http'):
            info['flvHdUrl'] = str(re.search(r's\d+.flvHdUrl="(.+?\.flv).+?";', rdata).group(1))
        if rdata.find('flvSdUrl="http'):
            info['flvSdUrl'] = str(re.search(r's\d+.flvSdUrl="(.+?\.flv).+?";', rdata).group(1))
        if rdata.find('flvShdUrl="http'):
            info['flvShdUrl'] = str(re.search(r's\d+.flvShdUrl="(.+?\.flv).+?";', rdata).group(1))
        if rdata.find('mp4HdUrl="http'):
            info['mp4HdUrl'] = str(re.search(r's\d+.mp4HdUrl="(.+?\.mp4).+?";', rdata).group(1))
        if rdata.find('mp4SdUrl="http'):
            info['mp4SdUrl'] = str(re.search(r's\d+.mp4SdUrl="(.+?\.mp4).+?";', rdata).group(1))
        if rdata.find('mp4ShdUrl="http'):
            info['mp4ShdUrl'] = str(re.search(r's\d+.mp4ShdUrl="(.+?\.mp4).+?";', rdata).group(1))

            """ 如果存在字幕的话
           s0.name="\u4E2D\u6587";s0.url="http://www.icourse163.org/video/downloadVideoSrt.htm?srcKey=D2CEC15B003DB2C6CB8DEAA45A180C56-1469109042399";
           s1.name="\u82F1\u6587";s1.url="http://www.icourse163.org/video/downloadVideoSrt.htm?srcKey=7E38EBCF9D1E932F3B9DAD349D9336A8-1469109072124";
           """
    # if contentType == 2: # 单元测试
    if contentType == 3:  # 文档
        info['textOrigUrl'] = str(re.search(r'textOrigUrl:"(.+?)"', rdata).group(1))
    # if contentType == 4:  # 富文本
    # if contentType == 5:  # 考试
    # if contentType == 6:  # 讨论

    return info


# Structure lesson(This funciton will return a dict with lesson info)
def sort_lesson(index):
    return dict(
        # chapterId=re.search(r'.chapterId=(\d+);', index).group(1),
        sid=int(re.search(r's(\d+)', index).group(1)),
        contentType=int(re.search(r'.contentType=(\d+);', index).group(1)),
        name=str(re.search(r'.name="(.+)";', index).group(1)).encode('utf-8').decode('unicode_escape').encode('gbk','ignore').decode('gbk','ignore').replace('/','_'),
        viewStatus=int(re.search(r'.viewStatus=(\d+)', index).group(1)),
        info=getLessonUnitLearnVo(re.search(r'.contentId=(\d+);', index).group(1),
                                  re.search(r'.id=(\d+);', index).group(1),
                                  int(re.search(r'.contentType=(\d+);', index).group(1))),
        level='lesson'
    )
# -*- End of Api

# -*- Main
tid = re.search(r'tid=(\d+)', url).group(1)
cont = [0,0]
payload = {
        'callCount': 1,
        'scriptSessionId': '${scriptSessionId}' + str(random.randint(0, 200)),
        'httpSessionId': httpSessionId,
        'c0-scriptName': 'CourseBean',
        'c0-methodName': 'getLastLearnedMocTermDto',
        'c0-id': 0,
        'c0-param0': tid,  # 1004102109,
        'batchId': random.randint(1000000000000, 20000000000000)  # 1479741724609
    }
cs_url = 'http://www.icourse163.org/dwr/call/plaincall/CourseBean.getLastLearnedMocTermDto.dwr'
rdata = requests.post(cs_url, data=payload, headers=headers, cookies=cookies).text  # str -> list
print(rdata)
rdata = rdata.splitlines()
# Data cleaning
for index in rdata:
    # Structure lesson
    if re.match(r's(\d+).anchorQuestions=', index):
        lesson = sort_lesson(index)
        dllink = lesson['info'].get('mp4ShdUrl')     #这里选择导出的视频文件格式和分辨率
        if dllink:
            dlfile = re.search(r'/(\d+?_.+?.mp4)', dllink).group(1)
            print(dllink)
            open("dllink.txt", "a").write(dllink + "\n")
            new = "ren " + dlfile + " \"" + str(lesson.get('name')) + ".mp4\"\n"
            print(new)
            open("ren.bat", "a").write(new)
            cont[0] += 1

        wdlink = lesson['info'].get('textOrigUrl')
        if wdlink:
            print(wdlink)
            if wdimmediate:
                filename = unquote(re.search(r'&download=(.+)', wdlink).group(1)).replace("+", " ")
                r = requests.get(wdlink)
                with open(filename, "wb") as code:
                    code.write(r.content)
                    print("Download " + filename + " OK!")
            else:
                open("docsdllink.txt", "a").write(wdlink + "\n")
            cont[1] += 1

print("共获得\n视频：", cont[0], "\n文档：", cont[1])
