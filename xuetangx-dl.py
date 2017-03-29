# -*- coding: utf-8 -*-
import json
import re
from bs4 import BeautifulSoup

import model


class VideoInfo:
    def __init__(self, resp_json):
        self.sources = resp_json['sources']
        self.hd = None
        if self.sources:
            if self.sources['quality20']:
                self.hd = self.sources['quality20'][0]
            if self.sources['quality10']:
                self.sd = self.sources['quality10'][0]


# 从用户给的url中寻找课程id
def main(course_url, config):
    session = model.login(site="xuetangx", conf=config)
    course_id_search = re.search(r"courses/(?P<id>.+)/(courseware|info|discussion|wiki|progress|about)", course_url)
    if course_id_search:
        course_id = course_id_search.group("id")
        main_page = "http://www.xuetangx.com/courses/{course_id}".format(course_id=course_id)
        info = model.out_info(url=main_page, download_path=config.Download_Path)
        main_path = model.generate_path([config.Download_Path, info.folder])

        # 下载信息缓存列表
        info_list = []
        video_list = []
        srt_list = []
        doc_list = []

        # info中提取的img_link,video_link
        if info.img_link:
            img_file_name = r"课程封面图-{title}.jpg".format(title=info.title)
            img_file_path = model.generate_path([main_path, img_file_name])
            print("课程封面图: {link}".format(link=info.img_link))
            info_list.append((info.img_link, img_file_path))
        if info.video_link:
            video_file_name = r"课程简介-{title}.mp4".format(title=info.title)
            video_file_path = model.generate_path([main_path, video_file_name])
            print("课程简介视频: {link}".format(link=info.video_link))
            info_list.append((info.video_link, video_file_path))

        # 获取课程参与信息及判断是否已经参加课程
        page_courseware = session.get(url="{0}/courseware".format(main_page))
        if page_courseware.url.find("about") == -1 and page_courseware.url.find("login") == -1:  # 成功获取目录
            # 这里根据url判断：
            # 1、如果登陆了，但是没有参加该课程，会跳转到 ../about页面
            # 2、如果未登录(或密码错误)，会跳转到http://www.xuetangx.com/accounts/login?next=.. 页面
            print("Generate Download information.")

            # 处理courseware页面
            courseware_bs = BeautifulSoup(page_courseware.text, "lxml")
            chapter = courseware_bs.find_all("div", class_="chapter")

            for week in chapter:
                week_name = week.h3.a.string.strip()
                for lesson in week.ul.find_all("a"):
                    # 获取课程信息
                    lesson_name = model.clean_filename(lesson.p.string)  # 主标题
                    lesson_page = session.get(url="http://www.xuetangx.com{href}".format(href=lesson['href'])).text
                    lesson_bs = BeautifulSoup(lesson_page, "lxml")

                    tab_list = {}
                    for tab in lesson_bs.find_all("a", role="tab"):
                        tab_list[tab.get('id')] = re.search("(.+)", tab.get('title')).group(1)

                    seq_contents = lesson_bs.find_all('div', class_="seq_contents")

                    seq_video_content_len = 0
                    for seq in seq_contents:
                        if re.search(r"data-type=[\'\"]Video[\'\"]", seq.text):
                            seq_video_content_len += 1

                    for i, seq in enumerate(seq_contents):
                        seq_name = lesson_name
                        seq_path = model.generate_path([main_path, week_name])
                        srt_path = model.generate_path([main_path, "srt", week_name])
                        doc_path = model.generate_path([main_path, "docs", week_name])
                        if seq_video_content_len > 1:  # 如果只有一个的话，就不用建立子文件夹了
                            seq_name_raw = model.clean_filename(tab_list[seq.get("aria-labelledby")])
                            seq_name = r"{0} {1}".format(i, seq_name_raw)
                            seq_path = model.generate_path([seq_path, lesson_name])
                            srt_path = model.generate_path([srt_path, lesson_name])
                            doc_path = model.generate_path([doc_path, lesson_name])

                        if re.search(r"data-type=[\'\"]Video[\'\"]", seq.text):  # 视频
                            lesson_ccsource = re.search(r"data-ccsource=[\'\"](.+)[\'\"]", seq.text).group(1)
                            r = session.get(url="http://www.xuetangx.com/videoid2source/{0}".format(lesson_ccsource))
                            video = VideoInfo(resp_json=json.loads(r.text))
                            if video.sources is not None:
                                if video.hd:  # AttributeError
                                    video_link = video.hd
                                    video_file_name = "{0}.mp4".format(seq_name)
                                elif video.sd:
                                    video_link = video.sd
                                    video_file_name = "{0}_sd.mp4".format(seq_name)
                                else:
                                    raise FileNotFoundError(r.text)

                                video_file_path = model.generate_path([seq_path, video_file_name])
                                print("视频: \"{name}\" \"{link}\"".format(name=video_file_name, link=video_link))
                                video_list.append((video_link, video_file_path))
                                seq_bs = BeautifulSoup(seq.text, "lxml")
                                if config.Download_Srt and seq_bs.find("a", text="下载字幕"):  # 字幕
                                    raw_link = seq_bs.find("a", text="下载字幕")["href"]
                                    srt_link = "http://www.xuetangx.com{0}".format(raw_link)
                                    srt_file_name = "{0}.srt".format(seq_name)
                                    srt_file_path = model.generate_path([srt_path, srt_file_name])
                                    print("字幕: \"{name}\" \"{link}\"".format(name=srt_file_name, link=srt_link))
                                    srt_list.append((srt_link, srt_file_path))
                                if config.Download_Docs and seq_bs.find("a", text="下载讲义"):  # 讲义
                                    raw_link = seq_bs.find("a", text="下载讲义")["href"]
                                    doc_link = "http://www.xuetangx.com{0}".format(raw_link)
                                    doc_file_name = model.clean_filename(doc_link.split("/")[-1])
                                    doc_file_path = model.generate_path([doc_path, doc_file_name])
                                    print("文档: \"{name}\" \"{link}\"".format(name=doc_file_name, link=doc_link))
                                    doc_list.append((doc_link, doc_file_path))

        else:  # 未登陆成功或者没参加该课程
            print("Something Error,You may not Join this course or Enter the wrong password.")
            return

        # 处理info页面
        page_info = session.get(url="{0}/info".format(main_page))
        info_bs = BeautifulSoup(page_info.text, "lxml")
        doc_menu = info_bs.find("section", attrs={"aria-label": re.compile("讲义导航")})
        for each in doc_menu.find_all("a"):
            doc_name = each["href"].split("/")[-1]
            doc_link = "http://www.xuetangx.com{0}".format(each["href"])
            doc_file_path = model.generate_path([main_path, "docs", doc_name])
            print("文档: \"{name}\" \"{link}\"".format(name=doc_name, link=doc_link))
            doc_list.append((doc_link, doc_file_path))

        # TODO 写数据库，方便快速恢复下载

        # 下载
        if config.Download:
            if config.Download_Method == "Aria2":  # 这里是调用aria2的下载
                model.aira2_download(info_list + video_list + doc_list)
                model.download_queue(session, srt_list, queue_length=config.Download_Queue_Length)  # 需要session或者有时间期限的
            else:  # 默认调用自建下载
                model.download_queue(session, info_list + video_list + srt_list + doc_list,
                                     queue_length=config.Download_Queue_Length)

    else:
        print("No course Id,Please check!")

    return


if __name__ == '__main__':
    course_url = ""
    # Loading config
    config = model.config("settings.conf", "xuetangx")
    main(course_url, config)
