# -*- coding: utf-8 -*-
import random
import re
import configparser
import requests
from urllib.parse import unquote

import model

course_url = ''

# Loading config
config = configparser.ConfigParser()
config.read("settings.conf", encoding="utf-8-sig")

# Download_Setting
Download_Docs = config["icourse163"]["Download_Docs"]
Download_Srt = config["icourse163"]["Download_Srt"]
Download_Path = config["icourse163"]["Download_Path"]
downloadVideoType = ['mp4ShdUrl', 'mp4HdUrl', 'mp4SdUrl',
                     'flvShdUrl', 'flvHdUrl', 'flvSdUrl']  # Choose first video download link(if exists)

# Session
session = model.login(site="icourse163", conf=config)
httpSessionId = session.cookies["NTESSTUDYSI"]


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

    rdata = session.post(cs_url, data=payload, timeout=None).text
    # print(rdata)
    info = {}  # info.clear()
    # Sort data depend on it's contentType into dict info
    if contentType == 1:  # Video
        info['videoImgUrl'] = str(re.search(r's\d+.videoImgUrl="(.+?)";', rdata).group(1))

        video_type = []  # Get Video download type
        for k in downloadVideoType:
            if re.search(r's\d+.' + str(k) + '=".+?";', rdata):
                info[k] = str(re.search(r's\d+.' + str(k) + r'="(.+?\.mp4).+?";', rdata).group(1))
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
class SortedLesson:
    contentType = ""
    name = ""
    info = ""

    def load(self, index):
        self.contentType = int(re.search(r'.contentType=(\d+);', index).group(1))
        self.name = model.clean_filename(str(re.search(r'.name="(.+)";', index).group(1)).encode('utf-8').decode(
            'unicode_escape').encode('gbk', 'ignore').decode('gbk', 'ignore'))
        self.info = getLessonUnitLearnVo(re.search(r'.contentId=(\d+);', index).group(1),
                                         re.search(r'.id=(\d+);', index).group(1),
                                         int(re.search(r'.contentType=(\d+);', index).group(1)))
        return self


# Download things
# TODO 使用model.download替换该方法
def downloadCourseware(path, link, filename):
    model.mkdir_p(path)
    r = requests.get(link)
    with open(path + "\\" + filename, "wb") as code:
        code.write(r.content)
        print("Download \"" + filename + "\" OK!")


# -*- End of Api

# -*- Main
def main(course_url):
    # handle the course_url links to Get right courseId and termId
    if not re.search(r'([A-Za-z]*-\d*)', course_url):
        print("No course Id,Please check!")
        return
    else:
        info = model.out_info(info_page_url=course_url, download_path=Download_Path)
        course_path = f"{Download_Path}\\{info.folder}"

        # Get course's chapter
        cont = [0, 0]  # count [video,docs]
        payload = {
            'callCount': 1,
            'scriptSessionId': '${scriptSessionId}' + str(random.randint(0, 200)),
            'httpSessionId': httpSessionId,
            'c0-scriptName': 'CourseBean',
            'c0-methodName': 'getLastLearnedMocTermDto',
            'c0-id': 0,
            'c0-param0': info.id,
            'batchId': random.randint(1000000000000, 20000000000000)
        }
        cs_url = 'http://www.icourse163.org/dwr/call/plaincall/CourseBean.getLastLearnedMocTermDto.dwr'
        rdata = session.post(cs_url, data=payload, timeout=None).text
        # print(rdata)
        if re.search(r'var s\d+=\{\}', rdata):
            rdata = rdata.splitlines()  # str -> list
            # Data cleaning
            for index in rdata:
                # Structure lesson
                if re.match(r's(\d+).anchorQuestions=', index):
                    lesson = SortedLesson().load(index=index)
                    lessontype = lesson.contentType
                    if lessontype == 1:  # Video
                        bestvideo = lesson.info.get('videoType')  # Choose download video Type
                        # Output video download link
                        dllink = lesson.info.get(bestvideo[0])
                        open(course_path + "\\dllink.txt", "a").write(dllink + "\n")
                        # Output video rename command
                        dlfile = re.search(r'/(\d+?_.+?\.(mp4|flv))', dllink).group(1)
                        videotype = re.search(r'^(flv|mp4)(Sd|Hd|Shd)Url', str(bestvideo[0]))

                        if str(videotype.group(2)) == "Shd":
                            new = "ren " + dlfile + " \"" + str(lesson.name) + "." + str(
                                videotype.group(1)) + "\"\n"
                        else:
                            new = "ren " + dlfile + " \"" + str(lesson.name) + "_" + str(
                                videotype.group(2)) + "." + str(videotype.group(1)) + "\"\n"
                        print(str(lesson.name) + " : " + dllink)
                        open(course_path + "\\ren.bat", "a").write(new)
                        cont[0] += 1
                        # Subtitle
                        if Download_Srt:
                            if lesson.info.get('ChsSrt'):
                                print("Find Chinese Subtitle for this lesson,Begin download.")
                                downloadCourseware(path=course_path + "\\" + "srt",
                                                   link=str(lesson.info.get('ChsSrt')),
                                                   filename=str(lesson.name) + '.chs.srt')

                            if lesson.info.get('EngSrt'):
                                print("Find English Subtitle for this lesson,Begin download.")
                                downloadCourseware(path=course_path + "\\" + "srt",
                                                   link=str(lesson.info.get('EngSrt')),
                                                   filename=str(lesson.name) + '.eng.srt')

                    if lessontype == 3:  # Documentation
                        wdlink = lesson.info.get('textOrigUrl')
                        # print(wdlink)
                        print("Find Document,Begin download.")
                        downloadCourseware(path=course_path + "\\" + "docs",
                                           link=wdlink,
                                           filename=str(cont[1]) + " " + unquote(
                                               re.search(r'&download=(.+)', wdlink).group(1)).replace("+", " "))
                        cont[1] += 1
            print("Found {0} Video(es),and {1} Text(s) on this page".format(cont[0], cont[1]))
        else:
            print("Error:" + re.search(r'message:(.+)\}\)', rdata).group(
                1) + ",Please make sure you login by 163-email and your \"Session-Cookies\" pair is right.")


if __name__ == '__main__':
    main(course_url)
