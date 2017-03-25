# -*- coding: utf-8 -*-
import re
import os
import time
import json

import requests
from bs4 import BeautifulSoup

# Session
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.87 Safari/537.36',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.8',
    'Content-Type': 'text/plain',
}
session = requests.Session()
session.headers.update(headers)


class CourseInfo:
    # Url
    url = None
    id = None
    # Basic information
    title = ""
    school = ""
    teacher = ""
    folder = None
    # spider information
    spider_info = ""
    description = ""
    introduction = ""
    # Other introduction
    img_link = None
    video_link = None

    def generate_folder(self):
        self.folder = '-'.join([self.title, self.school, self.teacher])


def sort_teacher(teacher_list):
    teacher_name = []
    for i in teacher_list:
        teacher_name.append(i.string)
        if len(teacher_name) >= 3:
            teacher_name[2] += '等'
            break
    return '、'.join(teacher_name)


def xuetanx_info(info=CourseInfo(), url=""):
    course_id = re.search(r"courses/(?P<id>[\w:+-]+)/?", url).group("id")
    page_about = session.get(url=f"http://www.xuetangx.com/courses/{course_id}/about")
    if page_about.text.find("页面无法找到") == -1:  # 存在该课程
        page_about_bs = BeautifulSoup(page_about.text, "html5lib")
        # 获取课程信息
        info.id = course_id
        info.url = f"http://www.xuetangx.com/courses/{course_id}/about"
        courseabout_detail_bs = page_about_bs.find("section", class_="courseabout_detail")
        course_name_tag = courseabout_detail_bs.find("h3", class_="courseabout_title")

        info.title = course_name_tag.get_text()
        info.school = course_name_tag.find_next("a").get_text()
        info.teacher = sort_teacher(page_about_bs.find("ul", class_="teacher_info").find_all("span", class_="name"))
        CourseInfo.generate_folder(info)

        # spider_info （建议在抓取完后检查修改）
        info_div = page_about_bs.find("div", class_="course_info")
        course_type = None
        course_type_search = re.search(r"[(（](?P<type>(\d{,4}[春夏秋冬])|(自主模式).+?)[)）]", info.title)
        if course_type_search:
            course_type = course_type_search.group("type")
        # TODO 请考虑这里使用split分割后在取前段合适还是直接使用字符串截取方便
        start_time = info_div["data-start"].split("+")[0]  # '2017-03-15 01:00:00+00:00' -> '2017-03-15 01:00:00'
        end_time = info_div["data-end"].split("+")[0]
        if course_type:
            info.spider_info += "抓取开课类型（次数）：{0}\n".format(course_type)
        else:
            info.spider_info += "抓取开课类型（次数）：未知\n"
        info.spider_info += "课程时间：\n开课：{start}\n结束：{end}\n\n".format(start=start_time, end=end_time) \
                            + "抓取内容：\n课程视频（MP4超清源）\n课程文档（PDF）\n字幕\n\n抓取补充说明：\n无"
        info.description = info_div.p.get_text()
        # TODO 优化学堂在线的简介部分导出方法
        info.introduction = page_about_bs.find("section", id="courseIntro").get_text().encode('gbk', 'ignore').decode('gbk','ignore')

        info.img_link = f"http://www.xuetangx.com{courseabout_detail_bs.find('div',id='video')['data-poster']}"
        # video_link
        video_ccid = courseabout_detail_bs.find("div", id="video")["data-ccid"]
        r = session.get(url=f"http://www.xuetangx.com/videoid2source/{video_ccid}")
        r_json = json.loads(r.text)
        if r_json["sources"]:
            if r_json["sources"]["quality20"][0]:
                info.video_link = r_json["sources"]["quality20"][0]
            else:
                info.video_link = r_json["sources"]["quality10"][0]
        return info
    else:
        raise FileNotFoundError("Not found this course in \"xuetangx.com\",Check Please")


def icourse163_info(info=CourseInfo(), url=""):
    cid = re.search(r"(?:(learn)|(course))/(?P<id>(?P<cid>[\w:+-]+)(\?tid=(?P<tid>\d+))?)#?/?", url)
    if cid:
        tid_flag = False
        if cid.group("tid"):
            # 当使用者提供tid的时候默认使用使用者tid
            info.id = cid.group("tid")
            info_url = f"http://www.icourse163.org/course/{cid.group('id')}#/info"
            tid_flag = True
        else:
            # 否则通过info页面重新获取最新tid
            print("No termId which you want to download.Will Choose the Lastest term.")
            info_url = f"http://www.icourse163.org/course/{cid.group('cid')}#/info"  # 使用课程默认地址
        page_about = session.get(url=info_url)
        if page_about.url == page_about.request.url:  # 存在该课程
            # 当课程不存在的时候会302重定向到http://www.icourse163.org/，通过检查返回、请求地址是否一致判断
            bs = BeautifulSoup(page_about.text, "html5lib")
            course_info_raw = bs.find("script", text=re.compile(r"termDto")).string.replace("\n", "")
            if not tid_flag:  # 没有提供tid时候自动寻找最新课程信息
                info.id = re.search(r"termId : \"(\d+)\"", course_info_raw).group(1)
            # 获取课程信息
            info.url = page_about.url
            info.title = re.search(r'(.+?)_(.+?)_(.+?)', bs.title.string).group(1)
            info.school = re.search(r'(.+?)_(.+?)_(.+?)', bs.title.string).group(2)
            info.teacher = sort_teacher(bs.find_all('h3', class_="f-fc3"))
            CourseInfo.generate_folder(info)

            info.description = re.search(r"spContent=(.+)", bs.find("p", id="j-rectxt").string).group(1)

            # spider_info （建议在抓取完后检查修改）
            start_time = time.gmtime(int(re.search(r"startTime : \"(\d+)\"", course_info_raw).group(1)) / 1000)
            end_time = time.gmtime(int(re.search(r"endTime : \"(\d+)\"", course_info_raw).group(1)) / 1000)
            # TODO 请检查这里关于开课次数有没有更好的抓取方法
            term_info_list = re.search(r"window.termInfoList = \[(?P<termInfoList>.+?)\]", course_info_raw, re.M).group(
                "termInfoList")
            id_list = re.findall(r"id : \"(\d+)\"", term_info_list)
            id_order = id_list.index(info.id) + 1
            info.spider_info = "抓取开课次数：第{0}次开课\n".format(id_order) \
                               + "课程时间：\n" \
                               + "开课：{0}\n".format(time.strftime("%Y-%m-%d %H:%M:%S", start_time)) \
                               + "结束：{0}\n\n".format(time.strftime("%Y-%m-%d %H:%M:%S", end_time)) \
                               + "抓取内容：\n课程视频（MP4超清源）\n课程文档（PDF）\n字幕\n\n抓取补充说明：\n无"
            # TODO 优化中国大学MOOC的简介部分导出方法
            info.introduction = bs.find("div", class_="m-infomation").get_text().encode('gbk', 'ignore').decode('gbk',
                                                                                                                'ignore')
            info.img_link = bs.find("div", id="j-courseImg").img["src"]
            # intro_video
            video_id = re.search(r"termId : \"(\d+)\"", course_info_raw).group(1)
            payload = {
                'callCount': 1,
                'scriptSessionId': '${scriptSessionId}190',  # 最后三个为随机数字，貌似不加也行
                'httpSessionId': session.cookies["NTESSTUDYSI"],
                'c0-scriptName': 'CourseBean',
                'c0-methodName': 'getLessonUnitPreviewVo',
                'c0-id': 0,
                'c0-param0': video_id,
                'c0-param1': 1,
                'batchId': 1489407453123  # 随机数字(int(1e12~2e12))，这里随机选了个，就不引入随机数模块了
            }
            ask_video_url = "http://www.icourse163.org/dwr/call/plaincall/CourseBean.getLessonUnitPreviewVo.dwr"
            resp = session.post(url=ask_video_url, data=payload).text
            download_video_type = ['mp4ShdUrl', 'mp4HdUrl', 'mp4SdUrl', 'flvShdUrl', 'flvHdUrl', 'flvSdUrl']
            video_link_list = []  # Get Video download type
            for k in download_video_type:
                video_search_group = re.search(r's\d+.(?P<VideoType>' + str(k) + ')="(?P<dllink>.+?)";', resp)
                if video_search_group:
                    dllink = video_search_group.group("dllink")
                    video_link_list.append(dllink)
            if video_link_list:
                info.video_link = video_link_list[0]
        return info
    else:
        raise FileNotFoundError("Not found this course in \"icourse163.org\",Check Please")


def make_intro_file(info, path):
    if not os.path.exists(path):
        os.makedirs(path)
    if not os.path.exists(f"{path}\\课程介绍及抓取说明.txt"):
        print("生成\"课程介绍及抓取说明\"中~")
        intro = open(f"{path}\\课程介绍及抓取说明.txt", "a")
        intro.write(f"MOOC课程地址：{info.url}\n")
        intro.write("\n")
        intro.write(f"{info.folder}\n")
        intro.write("\n")
        intro.write(f"发布大学：{info.school}\n")
        intro.write(f"发布课程：{info.title}\n")
        intro.write(f"授课老师：{info.teacher}\n")
        intro.write(f"课程简介：{info.description}\n")
        intro.write("\n")
        intro.write(f"{info.spider_info}\n")
        intro.write("\n")
        intro.write(f"{info.introduction}\n")


def out_info(info_page_url="", download_path=None):
    # 生成配置信息
    info = CourseInfo()  # 默认情况
    print("Loading Course's info")
    if info_page_url.find("www.xuetangx.com") != -1:
        info = xuetanx_info(url=info_page_url)
    if info_page_url.find("www.icourse163.org") != -1:
        info = icourse163_info(url=info_page_url)
    if info.folder:  # 确认已经获取到信息
        path = f"{download_path}\\{info.folder}"
        print(f"The Download INFO:\n"
              f"link:{info.url}\n"
              f"Course:{info.folder}\n"
              f"id:{info.id}")
        make_intro_file(info, path)
        return info
    else:
        raise FileNotFoundError()
