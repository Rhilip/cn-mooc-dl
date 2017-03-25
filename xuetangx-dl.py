# -*- coding: utf-8 -*-
import json
import re
from queue import Queue
from bs4 import BeautifulSoup

import model

course_url = ""

# Loading config
config = model.config("settings.conf", "xuetangx")
session = model.login(site="xuetangx", conf=config)


class VideoInfo:
    def __init__(self, resp_json):
        self.sources = resp_json['sources']
        if resp_json['sources']:
            self.sd = self.sources['quality10'][0]
            self.hd = self.sources['quality20'][0]


# 从用户给的url中寻找课程id
def main(course_url):
    if not re.search(r"courses/([\w:+-]+)/?", course_url):
        print("No course Id,Please check!")
        return
    else:
        course_id = re.search(r"courses/([\w:+-]+)/?", course_url).group(1)
        main_page = f"http://www.xuetangx.com/courses/{course_id}"
        info = model.out_info(f"{main_page}/about", config.Download_Path)
        main_path = f"{config.Download_Path}\\{info.folder}"

        # 获取课程目录
        menu_raw = session.get(url="{0}/courseware".format(main_page))
        # 目录检查
        if menu_raw.url.find("about") == -1 and menu_raw.url.find("login") == -1:  # 成功获取目录
            # 这里根据url判断：
            # 1、如果登陆了，但是没有参加该课程，会跳转到 ../about页面
            # 2、如果未登录(或密码错误)，会跳转到http://www.xuetangx.com/accounts/login?next=.. 页面
            print("Generate Download information.")
            # 下载信息缓存列表
            download_list = []

            # info中提取的img_link,video_link
            if info.img_link:
                img_suffix = info.img_link.split(".")[-1]
                img_file = f"{main_path}\\课程封面图-{info.title}.{img_suffix}"
                print("课程封面图: {link}".format(link=info.img_link))
                download_list.append((info.img_link, img_file))
            if info.video_link:
                video_file = f"{main_path}\\课程简介-{info.title}.mp4"
                print("课程简介视频: {link}".format(link=info.video_link))
                download_list.append((info.video_link, video_file))

            menu_bs = BeautifulSoup(menu_raw.text, "html5lib")
            chapter = menu_bs.find_all("div", class_="chapter")
            # 获取章节信息
            for week in chapter:
                week_name = week.h3.a.string.strip()
                model.mkdir_p(f"{main_path}\\{week_name}")
                for lesson in week.ul.find_all("a"):
                    # 获取课程信息
                    lesson_name = model.clean_filename(lesson.p.string)  # 主标题
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
                            video = VideoInfo(resp_json=json.loads(r.text))
                            if video.sources is not None:
                                if video.hd:
                                    video_link = video.hd
                                else:
                                    video_link = video.sd
                                video_file_name = f"{main_path}\\{week_name}\\{lesson_name}.mp4"
                                print("视频: \"{name}\" {link}".format(name=video_file_name.split("\\")[-1],
                                                                     link=video_link))
                                download_list.append((video_link, video_file_name))
                                seq_bs = BeautifulSoup(seq.text, "lxml")
                                if config.Download_Srt and seq_bs.find("a", text="下载字幕"):  # 字幕
                                    raw_link = seq_bs.find("a", text="下载字幕")["href"]
                                    srt_link = "http://www.xuetangx.com{0}".format(raw_link)
                                    srt_file_name = f"{main_path}\\{week_name}\\{lesson_name}.srt"
                                    print("字幕: \"{name}\" {link}".format(name=srt_file_name.split("\\")[-1],
                                                                         link=srt_link))
                                    download_list.append((srt_link, srt_file_name))
                                if config.Download_Docs and seq_bs.find("a", text="下载讲义"):  # 讲义
                                    raw_link = seq_bs.find("a", text="下载讲义")["href"]
                                    doc_link = "http://www.xuetangx.com{0}".format(raw_link)
                                    doc_file_name = f"{main_path}\\{week_name}\\{lesson_name}.pdf"
                                    print("文档: \"{name}\" {link}".format(name=doc_file_name.split("\\")[-1],
                                                                         link=doc_link))
                                    download_list.append((doc_link, doc_file_name))

            # 多线程下载
            print("Begin Download~")
            queue = Queue()
            for x in range(8):
                worker = model.DownloadQueue(queue)
                worker.daemon = True
                worker.start()
            for link_tuple in download_list:
                link, file_name = link_tuple
                queue.put((session, link, file_name))
            queue.join()

        else:  # 未登陆成功或者没参加该课程
            print("Something Error,You may not Join this course or Enter the wrong password.")
            return


if __name__ == '__main__':
    main(course_url)
