# -*- coding: utf-8 -*-
import random
import re
from bs4 import BeautifulSoup

import model


def main(course_url):
    config = model.config("settings.conf", "study163")
    session = model.login(site="study163", conf=config)
    http_session_id = session.cookies["NTESSTUDYSI"]
    c_tid = re.search(r"(?:(learn)|(course))/(?P<id>(?P<c_id>[\w:+-]+)(\?tid=(?P<t_id>\d+))?)#?/?", course_url)

    # Download cache list
    main_list = []
    srt_list = []
    doc_list = []

    if c_tid:
        if c_tid.group("t_id"):  # 当使用者提供tid的时候默认使用使用者tid
            term_id = c_tid.group("t_id")
            info_url = "http://mooc.study.163.com/course/{id}#/info".format(id=c_tid.group('id'))
        else:  # 否则通过info页面重新获取最新tid
            term_id = None
            print("No termId which you want to download.Will Choose the Lastest term.")
            info_url = "http://mooc.study.163.com/course/{id}#/info".format(id=c_tid.group('c_id'))  # 使用课程默认地址

        page_about = session.get(url=info_url)
        if page_about.url == info_url:  # 存在该课程
            # 当课程不存在的时候会302重定向到http://study.163.com/，通过检查返回、请求地址是否一致判断
            page_about_bs = BeautifulSoup(page_about.text, "lxml")
            course_info_raw = page_about_bs.find("script", text=re.compile(r"termDto")).string.replace("\n", "")
            if term_id is None:  # 没有提供tid时候自动寻找最新课程信息
                term_id = re.search(r"termId : \"(\d+)\"", course_info_raw).group(1)
            course_title = model.clean_filename(page_about_bs.find("h2", class_="f-fl").get_text())
            school = re.search(r"window.schoolDto = {.+?name:\"(.+?)\"}", course_info_raw).group(1)
            teacher = model.sort_teacher(page_about_bs.find_all('h3', class_="f-fc3"))
            folder = model.clean_filename('-'.join([course_title, school, teacher]))

            print("The Download INFO:\n"  # Output download course info
                  "link:{url}\nCourse:{folder}\nid:{id}\n".format(url=info_url, folder=folder, id=term_id))

            main_path = model.generate_path([config.Download_Path, folder])

            info_img_link = page_about_bs.find("div", id="j-courseImg").img["src"]
            img_file_name = r"课程封面图-{title}.png".format(title=course_title)
            img_file_path = model.generate_path([main_path, img_file_name])
            print("课程封面图: {link}".format(link=info_img_link))
            main_list.append((info_img_link, img_file_path))

            video_search = re.search(r"videoId : \"(\d+)\"", course_info_raw)
            if video_search:
                payload = {
                    'callCount': 1,
                    'scriptSessionId': '${scriptSessionId}' + str(random.randint(0, 200)),
                    'httpSessionId': http_session_id,
                    'c0-scriptName': 'CourseBean',
                    'c0-methodName': 'getLessonUnitPreviewVo',
                    'c0-id': 0,
                    'c0-param0': term_id,
                    'c0-param1': video_search.group(1),
                    'c0-param2': 1,
                    'batchId': random.randint(1000000000000, 20000000000000)
                }
                ask_video_url = "http://mooc.study.163.com/dwr/call/plaincall/CourseBean.getLessonUnitPreviewVo.dwr"
                resp = session.post(url=ask_video_url, data=payload).text
                for k in ['mp4ShdUrl', 'mp4HdUrl', 'mp4SdUrl']:  # , 'flvShdUrl', 'flvHdUrl', 'flvSdUrl'
                    video_search_group = re.search(r's\d+.(?P<VideoType>' + str(k) + ')="(?P<dllink>.+?)";', resp)
                    if video_search_group:
                        info_video_link = video_search_group.group("dllink")
                        video_file_name = r"课程简介-{title}.mp4".format(title=course_title)
                        video_file_path = model.generate_path([main_path, video_file_name])
                        print("课程简介视频: {link}".format(link=info_video_link))
                        main_list.append((info_video_link, video_file_path))
                        break
        else:
            print("Not found this course in \"study.163.com\",Check Please")
            return

        # Get course's chapter
        payload = {
            'callCount': 1,
            'scriptSessionId': '${scriptSessionId}' + str(random.randint(0, 200)),
            'httpSessionId': http_session_id,
            'c0-scriptName': 'CourseBean',
            'c0-methodName': 'getLastLearnedMocTermDto',
            'c0-id': 0,
            'c0-param0': term_id,  # 这里是课程的termID
            'batchId': random.randint(1000000000000, 20000000000000)
        }

        cs_url = 'http://mooc.study.163.com/dwr/call/plaincall/CourseBean.getLastLearnedMocTermDto.dwr'
        rdata = session.post(cs_url, data=payload, timeout=None).text
        if re.search(r"var s\d+={}", rdata):
            print("Generate Download information.")

            week_reg = re.compile(r"s\d+.contentId=null;"
                                  r".+s\d+.lessons=(?P<lessons>s\d+)"
                                  r".+s\d+.name=\"(?P<week_name>.+?)\"")
            chapter_reg = re.compile(r"s\d+.chapterId=\d+;"
                                     r".+s\d+.name=\"(?P<chapter_name>.+?)\"")
            lesson_reg = re.compile(r"s\d+.anchorQuestions=(null|s\d+);"
                                    r".+s\d+.contentId=(?P<contentId>\d+)"
                                    r".+s\d+.contentType=(?P<contentType>\d+)"
                                    r".+s\d+.id=(?P<id>\d+)"
                                    r".+s\d+.name=\"(?P<lesson_name>.+?)\"")
            # count_list
            week_list = []
            chapter_list = []
            video_in_chapter_list = []

            for line in rdata.splitlines():
                if re.match(week_reg, line):  # Week
                    week_re = re.search(week_reg, line)
                    week_name = model.clean_filename(model.raw_unicode_escape(week_re.group("week_name")))
                    week_list.append(week_name)
                if re.match(chapter_reg, line):  # Chapter
                    chapter_re = re.search(chapter_reg, line)
                    chapter_name = model.clean_filename(model.raw_unicode_escape(chapter_re.group("chapter_name")))
                    chapter_list.append(chapter_name)
                    print("\n", week_list[-1], chapter_list[-1])
                    video_in_chapter_list.append(0)
                if re.match(lesson_reg, line):
                    lesson_re = re.search(lesson_reg, line)
                    lesson_loc_pattern = model.generate_path([week_list[-1], chapter_list[-1]])

                    lesson_name = model.clean_filename(model.raw_unicode_escape(lesson_re.group("lesson_name")))
                    lesson_content_type = int(lesson_re.group("contentType"))
                    # prepare data and post
                    payload = {
                        'callCount': 1,
                        'scriptSessionId': '${scriptSessionId}' + str(random.randint(0, 200)),
                        'httpSessionId': http_session_id,
                        'c0-scriptName': 'CourseBean',
                        'c0-methodName': 'getLessonUnitLearnVo',
                        'c0-id': 0,
                        'c0-param0': term_id,  # 这里是课程的termID（，和icourse163有些不同）
                        'c0-param1': lesson_re.group("contentId"),
                        'c0-param2': lesson_content_type,
                        'c0-param3': 0,
                        'c0-param4': lesson_re.group("id"),
                        'batchId': random.randint(1000000000000, 20000000000000)
                    }
                    cs_url = 'http://mooc.study.163.com/dwr/call/plaincall/CourseBean.getLessonUnitLearnVo.dwr'

                    rdata = session.post(cs_url, data=payload, timeout=None).text
                    # Sort data depend on it's contentType
                    # 1 -> Video ,2 -> Test ,3 -> Docs ,4 -> Rich text ,5 -> Examination ,6 -> Discussion
                    try:
                        if lesson_content_type == 1:  # Video
                            count = video_in_chapter_list[-1]
                            count_lesson_name = "{0} {lesson}".format(count, lesson=lesson_name)
                            for k in ['mp4ShdUrl', 'mp4HdUrl', 'mp4SdUrl']:  # , 'flvShdUrl', 'flvHdUrl', 'flvSdUrl'
                                if re.search(r's\d+.{0}=".+?";'.format(k), rdata):
                                    k_type = re.search("mp4(.+)Url", k).group(1)
                                    video_file_name = "{0}.mp4".format(count_lesson_name)
                                    if k_type != "Shd":
                                        video_file_name = "{0}_{type}.mp4".format(count_lesson_name, type=k_type)
                                    video_link = re.search(r's\d+.' + str(k) + r'="(.+?\.mp4.+?)";', rdata).group(1)
                                    video_file_path = model.generate_path(
                                        [main_path, lesson_loc_pattern, video_file_name])
                                    main_list.append((video_link, video_file_path))
                                    print("视频: \"{name}\" \"{link}\"".format(name=video_file_name, link=video_link))
                                    break
                            # Subtitle
                            if config.Download_Srt:
                                srt_path = model.generate_path([main_path, "Srt", lesson_loc_pattern])
                                if re.search(r's\d+.name="\\u4E2D\\u6587";s\d+.url="(.+?)"', rdata):  # Chinese
                                    srt_chs_re = re.search(r's\d+.name="\\u4E2D\\u6587";s\d+.url="(?P<url>.+?)"', rdata)
                                    srt_file_name = "{0}.chs.srt".format(count_lesson_name)
                                    srt_file_path = model.generate_path([srt_path, srt_file_name])
                                    srt_chs_link = srt_chs_re.group("url")
                                    print("字幕Chs: \"{name}\" \"{link}\"".format(name=srt_file_name, link=srt_chs_link))
                                    srt_list.append((srt_chs_link, srt_file_path))
                                if re.search(r's\d+.name="\\u82F1\\u6587";s\d+.url="(.+?)"', rdata):  # English
                                    srt_eng_re = re.search(r's\d+.name="\\u82F1\\u6587";s\d+.url="(?P<url>.+?)"', rdata)
                                    srt_file_name = "{0}.eng.srt".format(lesson_name)
                                    srt_file_path = model.generate_path([srt_path, srt_file_name])
                                    srt_eng_link = srt_eng_re.group("url")
                                    print("字幕Eng: \"{name}\" \"{link}\"".format(name=srt_file_name, link=srt_eng_link))
                                    srt_list.append((srt_eng_link, srt_file_path))
                            video_in_chapter_list[-1] += 1

                        if lesson_content_type == 3 and config.Download_Docs:  # Documentation
                            doc_link = str(re.search(r'textOrigUrl:"(.+?)"', rdata).group(1))
                            doc_name = model.clean_filename(re.search(r'download=(.+)', doc_link).group(1))
                            doc_path = model.generate_path([main_path, "Docs", lesson_loc_pattern])
                            doc_file_path = model.generate_path([doc_path, doc_name])
                            doc_list.append((doc_link, doc_file_path))
                            print("文档: \"{name}\" \"{link}\"".format(name=doc_name, link=doc_link))
                    except AttributeError:
                        err_message = model.raw_unicode_escape(re.search(r'message:(.+)\}\)', rdata).group(1))
                        print("Error:{0},Please make sure your \"Session-Cookies\" pair is right.".format(err_message))
                        return

            if config.Download:  # study163的下载均需session认证，不能调用aria2
                model.download_queue(session, srt_list + doc_list + main_list,
                                     queue_length=config.Download_Queue_Length)
        else:
            err_message = re.search(r'message:(.+)\}\)', rdata).group(1)
            print("Error:{0},Please make sure your \"Session-Cookies\" pair is right.".format(err_message))
    else:
        print("No course Id,Please check!")
        return


if __name__ == '__main__':
    course_url = "http://mooc.study.163.com/course/ZJU-1000002011?tid=2001218000#/info"
    main(course_url)
