import os
import re
import requests
import time
from bs4 import BeautifulSoup
import locale

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.87 Safari/537.36',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.8',
    'Content-Type': 'text/plain',
}
locale.setlocale(locale.LC_CTYPE, 'chinese')


class ReturnInfo:
    url = ""
    id = ""
    title = ""
    school = ""
    teacher = ""
    path = ""
    spider_info = ""
    description = ""
    introduction = ""
    img_link = ""
    video_link = ""

    def generate_path(self):
        return '-'.join([self.title, self.school, self.teacher])


def sort_teacher(teacher_list):
    teacher_name = []
    for i in teacher_list:
        teacher_name.append(i.string)
        if len(teacher_name) >= 3:
            teacher_name[2] += '等'
            break
    return '、'.join(teacher_name)


def xuetanx_info(info=ReturnInfo(), url=""):
    course_id = re.search(r"courses/(?P<id>[\w:+-]+)/?", url).group("id")
    s = requests.Session()
    page_about = s.get(url=f"http://www.xuetangx.com/courses/{course_id}/about", headers=headers)
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
        info.path = ReturnInfo.generate_path(info)
        info.img_link = f"http://www.xuetangx.com{courseabout_detail_bs.find('div',id='video')['data-poster']}"
        # video_link = ""
        # spider_info = ""
        info.description = courseabout_detail_bs.find("div", class_="course_intro").p.get_text()
        info.introduction = page_about_bs.find("section", id="courseIntro").get_text().replace(" ", "")
        return info
    else:
        raise FileNotFoundError("Not found this course in \"xuetangx.com\",Check Please")


def icourse163_info(info=ReturnInfo(), url=""):
    course_seacrh = re.search(r"(?:(learn)|(course))/(?P<id>(?P<cid>[\w:+-]+)(\?tid=(?P<tid>\d+))?)#?/?", url)
    if course_seacrh:
        tid_flag = False
        if course_seacrh.group("tid"):
            # 当使用者提供tid的时候默认使用使用者tid
            info.id = course_seacrh.group("tid")
            info_url = f"http://www.icourse163.org/course/{course_seacrh.group('id')}#/info"
            tid_flag = True
        else:
            # 否则通过info页面重新获取最新tid
            print("No termId which you want to download.Will Choose the Lastest term.")
            info_url = f"http://www.icourse163.org/course/{course_seacrh.group('cid')}#/info"  # 使用课程默认地址
        s = requests.Session()
        s.get(url=info_url)
        page_about = s.get(url=info_url)
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
            info.path = ReturnInfo.generate_path(info)

            info.description = re.search(r"spContent=(.+)", bs.find("p", id="j-rectxt").string).group(1)

            # spider_info
            start_time = time.gmtime(int(re.search(r"startTime : \"(\d+)\"", course_info_raw).group(1)) / 1000)
            end_time = time.gmtime(int(re.search(r"endTime : \"(\d+)\"", course_info_raw).group(1)) / 1000)
            term_info_list = re.search(r"window.termInfoList = \[(?P<termInfoList>.+?)\]", course_info_raw, re.M).group(
                "termInfoList")
            id_list = re.findall(r"id : \"(\d+)\"", term_info_list)
            id_order = id_list.index(info.id) + 1
            info.spider_info = f"抓取开课次数：第{id_order}次开课\n" \
                               + "课程时间：\n" \
                               + "开课：{0}\n".format(time.strftime("%Y年%m月%d日 %H:%M", start_time)) \
                               + "结束：{0}\n".format(time.strftime("%Y年%m月%d日 %H:%M", end_time))

            info.introduction = bs.find("div", class_="m-infomation").get_text().encode('gbk', 'ignore').decode('gbk',
                                                                                                                'ignore')
            info.img_link = bs.find("div", id="j-courseImg").img["src"]
            # intro_video
            video_id = re.search(r"termId : \"(\d+)\"", course_info_raw).group(1)
            payload = {
                'callCount': 1,
                'scriptSessionId': '${scriptSessionId}190',
                'httpSessionId': s.cookies["NTESSTUDYSI"],
                'c0-scriptName': 'CourseBean',
                'c0-methodName': 'getLessonUnitPreviewVo',
                'c0-id': 0,
                'c0-param0': video_id,
                'c0-param1': 1,
                'batchId': 1489407453123
            }
            resp = s.post(url="http://www.icourse163.org/dwr/call/plaincall/CourseBean.getLessonUnitPreviewVo.dwr",
                          headers=headers, data=payload).text
            downloadVideoType = ['mp4ShdUrl', 'mp4HdUrl', 'mp4SdUrl', 'flvShdUrl', 'flvHdUrl', 'flvSdUrl']
            video_link_list = []  # Get Video download type
            for k in downloadVideoType:
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
        intro.write(f"{info.path}\n")
        intro.write("\n")
        intro.write(f"发布大学：{info.school}\n")
        intro.write(f"发布课程：{info.title}\n")
        intro.write(f"授课老师：{info.teacher}\n")
        intro.write(f"课程简介：{info.description}\n")
        intro.write("\n")
        intro.write(f"{info.spider_info}\n")
        intro.write("\n")
        intro.write(f"{info.introduction}\n")


def out_info(info_page_url="", download_path=""):
    # 生成配置信息
    info = ReturnInfo()  # 默认情况
    print("Loading Course's info")
    if info_page_url.find("www.xuetangx.com") != -1:
        info = xuetanx_info(url=info_page_url)
    if info_page_url.find("www.icourse163.org") != -1:
        info = icourse163_info(url=info_page_url)
    path = f"{download_path}\\{info.path}"
    print(f"The Download INFO:\n"
          f"link:{info.url}\n"
          f"Course:{info.path}\n"
          f"id:{info.id}")
    make_intro_file(info, path)
    return info
