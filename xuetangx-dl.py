# -*- coding: utf-8 -*-
import json
import re
from bs4 import BeautifulSoup

import model


# From video_ccid to video download link
def getvideo(session, video_id):
    r = session.get(url="http://www.xuetangx.com/videoid2source/{0}".format(video_id))
    resp_json = json.loads(r.text)
    try:
        if len(resp_json['sources']['quality20']) != 0:
            video_link = resp_json['sources']['quality20'][0]
        else:
            video_link = resp_json['sources']['quality10'][0]
    except AttributeError:
        print("Error,Server Respond:", r.text)
    else:
        return video_link


# Find course_id from url
def main(course_url):
    config = model.config("settings.conf", "xuetangx")  # Loading config
    session = model.login(site="xuetangx", conf=config)
    course_id_search = re.search(r"courses/(?P<id>.+)/(courseware|info|discussion|wiki|progress|about)", course_url)

    # Download cache list
    main_list = []
    srt_list = []
    doc_list = []

    if course_id_search:
        course_id = course_id_search.group("id")
        main_page = "http://www.xuetangx.com/courses/{course_id}".format(course_id=course_id)

        page_about_url = "{course_host}/about".format(course_host=main_page)
        page_about = session.get(url=page_about_url)
        if page_about.text.find("页面无法找到") == -1:  # if Exist
            page_about_bs = BeautifulSoup(page_about.text, "lxml")
            # load course info
            course_detail_bs = page_about_bs.find("section", class_="courseabout_detail")
            course_name_tag = course_detail_bs.find("h3", class_="courseabout_title")

            course_title = course_name_tag.get_text()
            school = course_name_tag.find_next("a").get_text()
            teacher = model.sort_teacher(
                page_about_bs.find("ul", class_="teacher_info").find_all("span", class_="name"))
            folder = '-'.join([course_title, school, teacher])

            print("The Download INFO:\n"  # Output download course info
                  "link:{url}\nCourse:{folder}\nid:{id}\n".format(url=page_about_url, folder=folder, id=course_id))

            main_path = model.generate_path([config.Download_Path, folder])

            video_box = course_detail_bs.find('div', class_='video_box')
            try:
                info_img_link = model.link_check("http://www.xuetangx.com", video_box['data-poster'])
                info_video_link = getvideo(session, video_box["data-ccid"])
                if info_video_link:
                    video_file_name = r"课程简介-{title}.mp4".format(title=course_title)
                    video_file_path = model.generate_path([main_path, video_file_name])
                    print("课程简介视频: {link}".format(link=info_video_link))
                    main_list.append((info_video_link, video_file_path))
            except KeyError:
                info_img_link = model.link_check("http://www.xuetangx.com", video_box.img["src"])

            if info_img_link:
                img_file_name = r"课程封面图-{title}.jpg".format(title=course_title)
                img_file_path = model.generate_path([main_path, img_file_name])
                print("课程封面图: {link}".format(link=info_img_link))
                main_list.append((info_img_link, img_file_path))
        else:
            print("Not found this course in \"xuetangx.com\",Check Please")
            return

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
                week_name = model.clean_filename(week.h3.a.string.strip())
                for lesson in week.ul.find_all("a"):
                    # 获取课程信息
                    lesson_name = model.clean_filename(lesson.p.string)  # 主标题
                    lesson_page = session.get(url="http://www.xuetangx.com{href}".format(href=lesson['href']),
                                              timeout=None)
                    lesson_bs = BeautifulSoup(lesson_page.text, "lxml")

                    tab_list = {}
                    for tab in lesson_bs.find_all("a", role="tab"):
                        tab_list[tab.get('id')] = re.search("(.+)", tab.get('title')).group(1)

                    seq_contents = lesson_bs.find_all('div', class_="seq_contents")

                    print("\n", week_name, lesson_name)

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
                            video_link = getvideo(session, lesson_ccsource)
                            video_file_name = "{0}.mp4".format(seq_name)
                            if video_link.find == -1:
                                video_file_name = "{0}_sd.mp4".format(seq_name)
                            video_file_path = model.generate_path([seq_path, video_file_name])
                            print("视频: \"{name}\" \"{link}\"".format(name=video_file_name, link=video_link))
                            main_list.append((video_link, video_file_path))

                            seq_bs = BeautifulSoup(seq.text, "lxml")
                            if config.Download_Srt and seq_bs.find("a", text="下载字幕"):  # 字幕
                                raw_link = seq_bs.find("a", text="下载字幕")["href"]
                                srt_link = model.link_check("http://www.xuetangx.com", raw_link)
                                srt_file_name = "{0}.srt".format(seq_name)
                                srt_file_path = model.generate_path([srt_path, srt_file_name])
                                print("字幕: \"{name}\" \"{link}\"".format(name=srt_file_name, link=srt_link))
                                srt_list.append((srt_link, srt_file_path))
                            if config.Download_Docs and seq_bs.find("a", text="下载讲义"):  # 讲义
                                raw_link = seq_bs.find("a", text="下载讲义")["href"]
                                doc_link = model.link_check("http://www.xuetangx.com", raw_link)
                                doc_file_name = model.clean_filename(doc_link.split("/")[-1])
                                doc_file_path = model.generate_path([doc_path, doc_file_name])
                                print("文档: \"{name}\" \"{link}\"".format(name=doc_file_name, link=doc_link))
                                doc_list.append((doc_link, doc_file_path))

        else:  # 未登陆成功或者没参加该课程
            print("Something Error,You may not Join this course or Enter the wrong password.")
            return

        # 处理info页面的课程讲义
        page_info = session.get(url="{0}/info".format(main_page))
        info_bs = BeautifulSoup(page_info.text, "lxml")
        doc_menu = info_bs.find("section", attrs={"aria-label": re.compile("讲义导航")})
        for each in doc_menu.find_all("a"):
            doc_name = each["href"].split("/")[-1]
            doc_link = model.link_check("http://www.xuetangx.com", each["href"])
            doc_file_path = model.generate_path([main_path, "docs", doc_name])
            print("文档: \"{name}\" \"{link}\"".format(name=doc_name, link=doc_link))
            doc_list.append((doc_link, doc_file_path))

        # 下载
        if config.Download:
            if config.Download_Method == "Aria2":  # 这里是调用aria2的下载
                model.aira2_download(main_list + doc_list)
                model.download_queue(session, srt_list, queue_length=config.Download_Queue_Length)  # 需要session或者有时间期限的
            else:  # 默认调用自建下载
                model.download_queue(session, main_list + srt_list + doc_list,queue_length=config.Download_Queue_Length)

    else:
        print("No course Id,Please check!")

    return


if __name__ == '__main__':
    course_url = ""
    main(course_url)
