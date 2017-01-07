# -*- coding: utf-8 -*-
import requests
from http.cookies import SimpleCookie
import random
import re
from urllib.parse import unquote

# -*- Config
# Warning:Before start ,You should fill in these forms.
# Course url (with key "tid")
url = ''
# Session
httpSessionId = ''
# cookies
raw_cookies = ''
# Post Header(Don't change)
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.87 Safari/537.36',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.8',
    'Content-Type': 'text/plain',
}
# Download Docs Immediately(True or False)
wdimmediate = True

# -*- Api
# Arrange Cookies from raw
cookie = SimpleCookie()
cookie.load(raw_cookies)
cookies = {}
for key, morsel in cookie.items():
    cookies[key] = morsel.value


# getLessonUnitLearnVo (This funciton will return a dict with download info)
def getLessonUnitLearnVo(contentId, id, contentType):
    'VERSION : 20170107'
    # prepare data and post
    payload = {
        'callCount': 1,
        'scriptSessionId': '${scriptSessionId}' + str(random.randint(0, 200)),
        'httpSessionId': httpSessionId,
        'c0-scriptName': 'CourseBean',
        'c0-methodName': 'getLessonUnitLearnVo',
        'c0-id': 1,
        'c0-param0': contentId,
        'c0-param1': contentType,
        'c0-param2': 0,
        'c0-param3': id,
        'batchId': random.randint(1000000000000, 20000000000000)
    }
    cs_url = 'http://www.icourse163.org/dwr/call/plaincall/CourseBean.getLessonUnitLearnVo.dwr'

    rdata = requests.post(cs_url, data=payload, headers=headers, cookies=cookies).text
    # print(rdata)
    info = {}  # info.clear()
    # Sort data depend on it's contentType into dict info
    if contentType == 1:  # Video
        info['contentType'] = 1
        info['videoImgUrl'] = str(re.search(r's\d+.videoImgUrl="(.+?)";', rdata).group(1))

        # Get Video download link
        videoType = []
        # flv
        if re.search(r's\d+.flvSdUrl=".+?";', rdata):  # flvSd
            info['flvSdUrl'] = str(re.search(r's\d+.flvSdUrl="(.+?\.flv).+?";', rdata).group(1))
            videoType.append("flvSdUrl")
        if re.search(r's\d+.flvHdUrl=".+?";', rdata):  # flvHd
            info['flvHdUrl'] = str(re.search(r's\d+.flvHdUrl="(.+?\.flv).+?";', rdata).group(1))
            videoType.append("flvHdUrl")
        if re.search(r's\d+.flvShdUrl=".+?";', rdata):  # flvShd
            info['flvShdUrl'] = str(re.search(r's\d+.flvShdUrl="(.+?\.flv).+?";', rdata).group(1))
            videoType.append("flvShdUrl")
        # mp4
        if re.search(r's\d+.mp4SdUrl=".+?";', rdata):  # mp4Sd
            info['mp4SdUrl'] = str(re.search(r's\d+.mp4SdUrl="(.+?\.mp4).+?";', rdata).group(1))
            videoType.append("mp4SdUrl")
        if re.search(r's\d+.mp4HdUrl=".+?";', rdata):  # mp4Hd
            info['mp4HdUrl'] = str(re.search(r's\d+.mp4HdUrl="(.+?\.mp4).+?";', rdata).group(1))
            videoType.append("mp4HdUrl")
        if re.search(r's\d+.mp4ShdUrl=".+?";', rdata):  # mp4Shd
            info['mp4ShdUrl'] = str(re.search(r's\d+.mp4ShdUrl="(.+?\.mp4).+?";', rdata).group(1))
            videoType.append("mp4ShdUrl")
        # type of resulting video
        info["videoType"] = list(reversed(videoType))

        # Subtitle
        if re.search(r's\d+.name="\\u4E2D\\u6587";s\d+.url="(.+?)"', rdata):  # Chinese
            info['ChsSrt'] = str(re.search(r's\d+.name="\\u4E2D\\u6587";s\d+.url="(.+?)"', rdata).group(1))
        if re.search(r's\d+.name="\\u82F1\\u6587";s\d+.url="(.+?)"', rdata):  # English
            info['EngSrt'] = str(re.search(r's\d+.name="\\u82F1\\u6587";s\d+.url="(.+?)"', rdata).group(1))

    # if contentType == 2: # Test
    if contentType == 3:  # Documentation
        info['contentType'] = 3
        info['textOrigUrl'] = str(re.search(r'textOrigUrl:"(.+?)"', rdata).group(1))
    # if contentType == 4:  # Rich text
    # if contentType == 5:  # Examination
    # if contentType == 6:  # Discussion

    #print(info)
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


# Download things
def downloadCourseware(dllink,filename):
    r = requests.get(dllink)
    with open(filename, "wb") as code:
        code.write(r.content)
        print("Download \"" + filename + "\" OK!")
# -*- End of Api

# -*- Main
print('Begin~')
tid = re.search(r'tid=(\d+)', url).group(1)
cont = [0,0]
payload = {
        'callCount': 1,
        'scriptSessionId': '${scriptSessionId}' + str(random.randint(0, 200)),
        'httpSessionId': httpSessionId,
        'c0-scriptName': 'CourseBean',
        'c0-methodName': 'getLastLearnedMocTermDto',
        'c0-id': 0,
        'c0-param0': tid,
        'batchId': random.randint(1000000000000, 20000000000000)
    }
cs_url = 'http://www.icourse163.org/dwr/call/plaincall/CourseBean.getLastLearnedMocTermDto.dwr'
rdata = requests.post(cs_url, data=payload, headers=headers, cookies=cookies).text
# print(rdata)
rdata = rdata.splitlines()              # str -> list
# Data cleaning
for index in rdata:
    # Structure lesson
    if re.match(r's(\d+).anchorQuestions=', index):
        lesson = sort_lesson(index)
        lessontype = lesson['info'].get('contentType')
        if lessontype == 1:    # Video
            bestvideo = lesson['info'].get('videoType')        # Choose download video Type
            # Output video download link
            dllink = lesson['info'].get(bestvideo[0])
            print(dllink)
            open("dllink.txt", "a").write(dllink + "\n")
            # Output video rename command
            dlfile = re.search(r'/(\d+?_.+?\.(mp4|flv))', dllink).group(1)
            videotype = re.search(r'^(flv|mp4)(Sd|Hd|Shd)Url',str(bestvideo[0]))
            new = "ren " + dlfile + " \"" + str(lesson.get('name')) + "_" + str(videotype.group(2)) + "."+ str(videotype.group(1)) + "\"\n"
            print(new)
            open("ren.bat", "a").write(new)
            cont[0] += 1
            # Subtitle
            if lesson['info'].get('ChsSrt'):
                print("Find Chinese Subtitle for this lesson,Begin download.")
                srtdlink = str(lesson['info'].get('ChsSrt'))
                chssrtname = str(lesson.get('name')) + '.chs.srt'
                downloadCourseware(srtdlink, chssrtname)

            if lesson['info'].get('EngSrt'):
                print("Find English Subtitle for this lesson,Begin download.")
                srtdlink = str(lesson['info'].get('EngSrt'))
                engsrtname = str(lesson.get('name')) + '.eng.srt'
                downloadCourseware(srtdlink, engsrtname)

        if lessontype == 3:  # Documentation
            wdlink = lesson['info'].get('textOrigUrl')
            print(wdlink)
            if wdimmediate:
                filename = unquote(re.search(r'&download=(.+)', wdlink).group(1)).replace("+", " ")
                downloadCourseware(wdlink, filename)
            else:
                open("docsdllink.txt", "a").write(wdlink + "\n")
            cont[1] += 1

print("Found {0} Videoes and {1} Text on this page".format(cont[0],cont[1]))