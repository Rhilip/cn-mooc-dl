# -*- coding: utf-8 -*-
import json
import re
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
        main_page = "http://www.xuetangx.com/courses/{course_id}".format(course_id=course_id)
        info = model.out_info(f"{main_page}/about", config.Download_Path)
        main_path = model.generate_path([config.Download_Path, info.folder])

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
                img_file_name = r"课程封面图-{title}.jpg".format(title=info.title)
                img_file_path = model.generate_path([main_path, img_file_name])
                print("课程封面图: {link}".format(link=info.img_link))
                download_list.append((info.img_link, img_file_path))
            if info.video_link:
                video_file_name = r"课程简介-{title}.mp4".format(title=info.title)
                video_file_path = model.generate_path([main_path, video_file_name])
                print("课程简介视频: {link}".format(link=info.video_link))
                download_list.append((info.video_link, video_file_path))

            menu_bs = BeautifulSoup(menu_raw.text, "html5lib")
            chapter = menu_bs.find_all("div", class_="chapter")
            # 获取章节信息
            for week in chapter:
                week_name = week.h3.a.string.strip()
                for lesson in week.ul.find_all("a"):
                    # 获取课程信息
                    lesson_name = model.clean_filename(lesson.p.string)  # 主标题
                    lesson_bs = BeautifulSoup(session.get(url=f"http://www.xuetangx.com{lesson['href']}").text,
                                              "html5lib")

                    tab_list = {}
                    for tab in lesson_bs.find_all("a", role="tab"):
                        tab_list[tab.get('id')] = re.search("(.+)", tab.get('title')).group(1)

                    seq_contents = lesson_bs.find_all('div', class_="seq_contents")
                    seq_contents_len = len(seq_contents)
                    for i, seq in enumerate(seq_contents):
                        seq_name = ""
                        if seq_contents_len != 1:  # 如果只有一个的话，就不用建立子文件夹了
                            seq_name_raw = model.clean_filename(tab_list[seq.get("aria-labelledby")])
                            seq_name = r"{0} {1}".format(i, seq_name_raw)

                        if re.search(r"data-type=[\'\"]Video[\'\"]", seq.text):  # 视频
                            lesson_ccsource = re.search(r"data-ccsource=[\'\"](.+)[\'\"]", seq.text).group(1)
                            r = session.get(url=f"http://www.xuetangx.com/videoid2source/{lesson_ccsource}")
                            video = VideoInfo(resp_json=json.loads(r.text))
                            if video.sources is not None:
                                if video.hd:
                                    video_link = video.hd
                                else:
                                    video_link = video.sd
                                video_file_name = model.generate_path([lesson_name, "{}.mp4".format(seq_name)])
                                video_file_path = model.generate_path([main_path, week_name, video_file_name])
                                print("视频: \"{name}\" {link}".format(name=video_file_name, link=video_link))
                                download_list.append((video_link, video_file_path))
                                seq_bs = BeautifulSoup(seq.text, "lxml")
                                if config.Download_Srt and seq_bs.find("a", text="下载字幕"):  # 字幕
                                    raw_link = seq_bs.find("a", text="下载字幕")["href"]
                                    srt_link = "http://www.xuetangx.com{0}".format(raw_link)
                                    srt_file_name = model.generate_path([lesson_name, "{}.srt".format(seq_name)])
                                    srt_file_path = model.generate_path([main_path, "srt", week_name, srt_file_name])
                                    print("字幕: \"{name}\" {link}".format(name=srt_file_name, link=srt_link))
                                    download_list.append((srt_link, srt_file_path))
                                if config.Download_Docs and seq_bs.find("a", text="下载讲义"):  # 讲义
                                    raw_link = seq_bs.find("a", text="下载讲义")["href"]
                                    doc_link = "http://www.xuetangx.com{0}".format(raw_link)
                                    doc_file_name = doc_link.split("@")[-1]  # TODO 请多抓几门课程看这样是否可以，还是像srt一样处理的好
                                    doc_file_path = model.generate_path([main_path, "docs", week_name, doc_file_name])
                                    print("文档: \"{name}\" {link}".format(name=doc_file_name, link=doc_link))
                                    download_list.append((doc_link, doc_file_path))
            if config.Download:
                print("Begin Download~")
                model.download_queue(session, download_list)  # 多线程下载
            else:
                # TODO 这里是不使用model.download时候的输出方法
                pass
        else:  # 未登陆成功或者没参加该课程
            print("Something Error,You may not Join this course or Enter the wrong password.")
            return


if __name__ == '__main__':
    main(course_url)
