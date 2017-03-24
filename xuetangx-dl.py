# -*- coding: utf-8 -*-
import json
import re
import configparser
from bs4 import BeautifulSoup

import model

course_url = ""

# Loading config
config = configparser.ConfigParser()
config.read("settings.conf", encoding="utf-8-sig")
# Download_Setting
Download_Path = config["xuetangx"]["Download_Path"]

# Session
session = model.login(site="xuetangx", conf=config)


class VideoInfo:
    sources = []
    sd = hd = ""

    def load(self, resp_json):
        self.sources = resp_json['sources']
        if resp_json['sources']:
            self.sd = self.sources['quality10'][0]
            self.hd = self.sources['quality20'][0]
        return self


# 从用户给的url中寻找课程id
def main(course_url):
    if not re.search(r"courses/([\w:+-]+)/?", course_url):
        print("No course Id,Please check!")
        return
    else:
        course_id = re.search(r"courses/([\w:+-]+)/?", course_url).group(1)
        main_page = f"http://www.xuetangx.com/courses/{course_id}"
        info = model.out_info(f"{main_page}/about", Download_Path)
        main_path = f"{Download_Path}\\{info.folder}"

        # 获取课程目录
        menu_raw = session.get(url="{0}/courseware".format(main_page))
        # 目录检查
        if menu_raw.url.find("about") == -1 and menu_raw.url.find("login") == -1:  # 成功获取目录
            # 这里有个判断逻辑，根据url判断：
            # 1、如果登陆了，但是没有参加该课程，会跳转到 ../about页面
            # 2、如果未登录(或密码错误)，会跳转到http://www.xuetangx.com/accounts/login?next=.. 页面
            menu_bs = BeautifulSoup(menu_raw.text, "html5lib")
            chapter = menu_bs.find_all("div", class_="chapter")
            # 获取章节信息
            for week in chapter:
                week_name = week.h3.a.string.strip()
                model.mkdir_p(f"{main_path}\\{week_name}")
                # week_content = []
                for lesson in week.ul.find_all("a"):
                    # 获取课程信息
                    lesson_name = model.clean_filename(lesson.p.string.strip())  # 主标题
                    lesson_bs = BeautifulSoup(session.get(url=f"http://www.xuetangx.com{lesson['href']}").text,
                                              "html5lib")
                    tab_list = {}
                    for tab in lesson_bs.find_all("a", role="tab"):
                        tab_list[tab.get('id')] = re.search("(.+)", tab.get('title')).group(1)
                    for seq in lesson_bs.find_all('div', class_="seq_contents"):
                        if re.search(r"data-type=[\'\"]Video[\'\"]", seq.text):  # 视频
                            # seq_name = tab_list[seq.get("aria-labelledby")]
                            lesson_ccsource = re.search(r"data-ccsource=[\'\"](.+)[\'\"]", seq.text).group(1)
                            r = session.get(url=f"http://www.xuetangx.com/videoid2source/{lesson_ccsource}")
                            video = VideoInfo().load(resp_json=json.loads(r.text))
                            if video.sources is not None:
                                dllink = video.hd
                                if re.search("a href=\"(.+/download)\"", seq.text):
                                    srt_dllink = "http://www.xuetangx.com{0}".format(
                                        re.search("a href=\"(.+/download)\"", seq.text).group(1))
                                    # print(week_name, lesson_name, dllink, srt_dllink)
                                print("{2} \"{0} {1}.mp4\"".format(week_name, lesson_name, dllink))
                                download_file_name = f"{main_path}\\{week_name}\\{lesson_name}.mp4"
                                model.download_file(session=session, file=download_file_name, url=dllink)
                                # TODO 使用多线程下载
        else:  # 未登陆成功或者没参加该课程
            print("Something Error,You may not Join this course or Enter the wrong password.")
            return


if __name__ == '__main__':
    main(course_url)
