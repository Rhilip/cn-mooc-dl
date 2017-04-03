# -*- coding: utf-8 -*-
import random
import re

import model


# -*- Main
def main(course_url, config):
    # handle the course_url links to Get right courseId and termId
    if not re.search(r'([A-Za-z]*-\d*)', course_url):
        print("No course Id,Please check!")
        return
    else:
        session = model.login(site="icourse163", conf=config)
        httpSessionId = session.cookies["NTESSTUDYSI"]

        info = model.out_info(url=course_url, download_path=config.Download_Path)
        main_path = model.generate_path([config.Download_Path, info.folder])

        # Get course's chapter
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

        if re.search(r'var s\d+=\{\}', rdata):
            print("Generate Download information.")
            # 下载信息缓存列表
            info_list = []
            video_list = []
            srt_list = []
            doc_list = []

            # info中提取的img_link,video_link
            if info.img_link:
                img_file_name = r"课程封面图-{title}.png".format(title=info.title)
                img_file_path = model.generate_path([main_path, img_file_name])
                print("课程封面图: {link}".format(link=info.img_link))
                info_list.append((info.img_link, img_file_path))
            if info.video_link:
                video_file_name = r"课程简介-{title}.mp4".format(title=info.title)
                video_file_path = model.generate_path([main_path, video_file_name])
                print("课程简介视频: {link}".format(link=info.video_link))
                info_list.append((info.video_link, video_file_path))

            # Data cleaning Reg
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
                        'httpSessionId': httpSessionId,
                        'c0-scriptName': 'CourseBean',
                        'c0-methodName': 'getLessonUnitLearnVo',
                        'c0-id': 1,
                        'c0-param0': lesson_re.group("contentId"),
                        'c0-param1': lesson_content_type,
                        'c0-param2': 0,
                        'c0-param3': lesson_re.group("id"),
                        'batchId': random.randint(1000000000000, 20000000000000)
                    }
                    cs_url = 'http://www.icourse163.org/dwr/call/plaincall/CourseBean.getLessonUnitLearnVo.dwr'

                    rdata = session.post(cs_url, data=payload, timeout=None).text
                    # Sort data depend on it's contentType
                    # 1 -> Video ,2 -> Test ,3 -> Docs ,4 -> Rich text ,5 -> Examination ,6 -> Discussion
                    if lesson_content_type == 1:  # Video
                        count = video_in_chapter_list[-1]
                        count_lesson_name = "{0} {lesson}".format(count, lesson=lesson_name)
                        for k in ['mp4ShdUrl', 'mp4HdUrl', 'mp4SdUrl']:  # , 'flvShdUrl', 'flvHdUrl', 'flvSdUrl'
                            if re.search(r's\d+.{0}=".+?";'.format(k), rdata):
                                k_type = re.search("mp4(.+)Url", k).group(1)
                                video_file_name = "{0}.mp4".format(count_lesson_name)
                                if k_type != "Shd":
                                    video_file_name = "{0}_{type}.mp4".format(count_lesson_name, type=k_type)
                                video_link = re.search(r's\d+.' + str(k) + r'="(.+?\.mp4).+?";', rdata).group(1)
                                video_file_path = model.generate_path([main_path, lesson_loc_pattern, video_file_name])
                                video_list.append((video_link, video_file_path))
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
                        doc_name = "{0}.pdf".format(lesson_name)
                        doc_path = model.generate_path([main_path, "Docs", lesson_loc_pattern])
                        doc_file_path = model.generate_path([doc_path, doc_name])
                        doc_list.append((doc_link, doc_file_path))
                        print("文档: \"{name}\" \"{link}\"".format(name=doc_name, link=doc_link))

            if config.Download:
                if config.Download_Method == "Aria2":  # 这里是调用aria2的下载
                    model.aira2_download(info_list + video_list)
                    # 需要session或者有时间期限的，仍然使用自建下载
                    model.download_queue(session, srt_list + doc_list, queue_length=config.Download_Queue_Length)
                else:  # 默认调用自建下载
                    model.download_queue(session, info_list + video_list + srt_list + doc_list,
                                         queue_length=config.Download_Queue_Length)
        else:
            err_message = re.search(r'message:(.+)\}\)', rdata).group(1)
            print("Error:{0},Please make sure you login by 163-email "
                  "and your \"Session-Cookies\" pair is right.".format(err_message))


if __name__ == '__main__':
    course_url = ""
    config = model.config("settings.conf", "icourse163")
    main(course_url, config=config)
