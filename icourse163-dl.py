# -*- coding: utf-8 -*-
import requests, random, re, os
from bs4 import BeautifulSoup
from http.cookies import SimpleCookie
from urllib.parse import unquote

# -*- Config
# Warning:Before start ,You should fill in these forms.
# Course url (with key "tid")
course_url = ''
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

downloadSrt = True  # Download Chinese or English Srt (True or False)
downloadVideoType = ['mp4ShdUrl', 'mp4HdUrl', 'mp4SdUrl',
                     'flvShdUrl', 'flvHdUrl', 'flvSdUrl']  # Choose first video download link(if exists)

# -*- Api
# Arrange Cookies from raw
cookie = SimpleCookie()
cookie.load(raw_cookies)
cookies = {}
for key, morsel in cookie.items():
    cookies[key] = morsel.value


# getLessonUnitLearnVo (This funciton will return a dict with download info)
def getLessonUnitLearnVo(contentId, id, contentType):
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

    rdata = requests.post(cs_url, data=payload, headers=headers, cookies=cookies, timeout=None).text
    # print(rdata)
    info = {}  # info.clear()
    # Sort data depend on it's contentType into dict info
    if contentType == 1:  # Video
        info['videoImgUrl'] = str(re.search(r's\d+.videoImgUrl="(.+?)";', rdata).group(1))

        video_type = []    # Get Video download type
        for k in downloadVideoType:
            if re.search(r's\d+.'+ str(k) + '=".+?";', rdata):
                info[k] = str(re.search(r's\d+.'+ str(k) + r'="(.+?\.mp4).+?";', rdata).group(1))
                video_type.append(k)
        # type of resulting video
        info["videoType"] = video_type

        # Subtitle
        if re.search(r's\d+.name="\\u4E2D\\u6587";s\d+.url="(.+?)"', rdata):  # Chinese
            info['ChsSrt'] = str(re.search(r's\d+.name="\\u4E2D\\u6587";s\d+.url="(.+?)"', rdata).group(1))
        if re.search(r's\d+.name="\\u82F1\\u6587";s\d+.url="(.+?)"', rdata):  # English
            info['EngSrt'] = str(re.search(r's\d+.name="\\u82F1\\u6587";s\d+.url="(.+?)"', rdata).group(1))

    # if contentType == 2: # Test
    if contentType == 3:  # Documentation
        info['textOrigUrl'] = str(re.search(r'textOrigUrl:"(.+?)"', rdata).group(1))
    # if contentType == 4:  # Rich text
    # if contentType == 5:  # Examination
    # if contentType == 6:  # Discussion

    # print(info)
    return info


# Structure lesson(This funciton will return a dict with lesson info)
def sort_lesson(index):
    return dict(
        contentType=int(re.search(r'.contentType=(\d+);', index).group(1)),
        name=str(re.search(r'.name="(.+)";', index).group(1))
            .replace(r'\n', '')
            .encode('utf-8').decode('unicode_escape')
            .encode('gbk', 'ignore').decode('gbk', 'ignore')
            .replace('/', '_').replace(':', '：').replace('"', ''),
        info=getLessonUnitLearnVo(re.search(r'.contentId=(\d+);', index).group(1),
                                  re.search(r'.id=(\d+);', index).group(1),
                                  int(re.search(r'.contentType=(\d+);', index).group(1))),
    )


# Download things
def downloadCourseware(path, link, filename):
    if not os.path.exists(path):
        os.makedirs(path)
    r = requests.get(link)
    with open(path + "\\" + filename, "wb") as code:
        code.write(r.content)
        print("Download \"" + filename + "\" OK!")


# -*- End of Api

# -*- Main
def main():
    # handle the course_url links to Get right courseId and termId
    if not re.search(r'([A-Za-z]*-\d*)', course_url):
        print("No course Id,Please check!")
        return
    else:
        courseId = re.search(r'([A-Za-z]*-\d*)', course_url).group(1)
        bs = BeautifulSoup(requests.get(url="http://www.icourse163.org/course/" + courseId + "#/info", timeout=None).text, "lxml")
        course_info_raw = bs.find("script", text=re.compile(r"termDto")).string
        if re.search(r'tid', course_url):
            tid = re.search(r'tid=(\d+)', course_url).group(1)
        else:
            print("No termId which you want to download.Will Choose the Lastest term.")
            tid = re.search(r"termId : \"(\d+)\"", course_info_raw).group(1)

        print('Begin~')
        # Generate Grab information
        course_name = re.search(r'(.+?)_(.+?)_(.+?)', bs.title.string).group(1)
        school_name = re.search(r'(.+?)_(.+?)_(.+?)', bs.title.string).group(2)
        teacher_name = []
        for i in bs.find_all('h3', class_="f-fc3"):
            teacher_name.append(i.string)
            if len(teacher_name) >= 3:
                teacher_name[2] += '等'
                break
        teacher_name = '、'.join(teacher_name)
        path = course_name + '-' + school_name + '-' + teacher_name
        print("The Download INFO:\nCourse:" + path + "\nid: " + courseId + "\ntermID:" + tid)

        # Make course's dir
        if not os.path.exists(path):
            os.makedirs(path)

        # Get course's chapter
        cont = [0, 0]  # count [video,docs]
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
        rdata = requests.post(cs_url, data=payload, headers=headers, cookies=cookies, timeout=None).text
        # print(rdata)
        if re.search(r'var s\d+=\{\}', rdata):
            rdata = rdata.splitlines()  # str -> list
            # Data cleaning
            for index in rdata:
                # Structure lesson
                if re.match(r's(\d+).anchorQuestions=', index):
                    lesson = sort_lesson(index)
                    lessontype = lesson['contentType']
                    if lessontype == 1:  # Video
                        bestvideo = lesson['info'].get('videoType')  # Choose download video Type
                        # Output video download link
                        dllink = lesson['info'].get(bestvideo[0])
                        open(path + "\\dllink.txt", "a").write(dllink + "\n")
                        # Output video rename command
                        dlfile = re.search(r'/(\d+?_.+?\.(mp4|flv))', dllink).group(1)
                        videotype = re.search(r'^(flv|mp4)(Sd|Hd|Shd)Url', str(bestvideo[0]))
                        if str(videotype.group(2)) == "Shd":
                            new = "ren " + dlfile + " \"" + str(lesson.get('name')) + "." + str(
                                videotype.group(1)) + "\"\n"
                        else:
                            new = "ren " + dlfile + " \"" + str(lesson.get('name')) + "_" + str(
                                videotype.group(2)) + "." + str(videotype.group(1)) + "\"\n"
                        print("Find Video\n" + str(lesson.get('name')) + " : "+ dllink)
                        open(path + "\\ren.bat", "a").write(new)
                        cont[0] += 1
                        # Subtitle
                        if downloadSrt:
                            if lesson['info'].get('ChsSrt'):
                                print("Find Chinese Subtitle for this lesson,Begin download.")
                                downloadCourseware(path=path + "\\" + "srt",
                                                   link=str(lesson['info'].get('ChsSrt')),
                                                   filename=str(lesson.get('name')) + '.chs.srt')

                            if lesson['info'].get('EngSrt'):
                                print("Find English Subtitle for this lesson,Begin download.")
                                downloadCourseware(path=path + "\\" + "srt",
                                                   link=str(lesson['info'].get('EngSrt')),
                                                   filename=str(lesson.get('name')) + '.eng.srt')

                    if lessontype == 3:  # Documentation
                        wdlink = lesson['info'].get('textOrigUrl')
                        # print(wdlink)
                        print("Find Document,Begin download.")
                        downloadCourseware(path=path + "\\" + "docs",
                                           link=wdlink,
                                           filename=str(cont[1]) + " " + unquote(
                                               re.search(r'&download=(.+)', wdlink).group(1)).replace("+", " "))
                        cont[1] += 1
            print("Found {0} Video(es),and {1} Text(s) on this page".format(cont[0], cont[1]))
        else:
            print("Error:" + re.search(r'message:(.+)\}\)', rdata).group(
                1) + ",Please make sure you login by 163-email and your \"Session-Cookies\" pair is right.")

if __name__ == '__main__':
    main()
