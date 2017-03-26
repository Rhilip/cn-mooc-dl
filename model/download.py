# -*- coding: utf-8 -*-
"""
This module contains a set of functions to download files from site.
Some of them are ripped from https://github.com/renever/cn_mooc_dl/blob/master/utils.py
Rewrite by Rhilip , v20170324
Diffident Point:
1. Use Package progressbar to show download progress
2. Merge resume_download_file(session, url, filename, overwrite=False) to download_file(session, url, filename)
3. Use Thread to Download multiple files at the same time
"""
import os
import time
import re
import errno

import progressbar
import requests

from queue import Queue
from threading import Thread


class DownloadQueue(Thread):
    queue = Queue()

    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            # Get the work from the queue and expand the tuple
            # 从队列中获取任务并扩展tuple
            session, url, filename = self.queue.get()
            download_file(session, url, filename)
            self.queue.task_done()


def clean_filename(string: str) -> str:
    """
    Sanitize a string to be used as a filename.

    If minimal_change is set to true, then we only strip the bare minimum of
    characters that are problematic for filesystems (namely, ':', '/' and
    '\x00', '\n').
    """

    string = string.replace(':', '_') \
        .replace('/', '_') \
        .replace('\x00', '_')

    string = re.sub('[\n\\\*><?\"|\t]', '', string)
    string = re.sub(' +$', '', string)
    string = re.sub('^ +', '', string)

    return string


def mkdir_p(path, mode=0o777):
    """
    Create subdirectory hierarchy given in the paths argument.
    Ripped from https://github.com/coursera-dl/
    """
    try:
        os.makedirs(path, mode)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def download_file(session: requests.Session(), url: str, file: str, resume=True, retry=4):
    # TODO 多进程下载
    name = clean_filename(file.split("\\")[-1])
    mkdir_p(file[:file.find(name)])
    if resume and os.path.exists(file):
        resume_len = os.path.getsize(file)
        file_mode = 'ab'
    else:
        resume_len = 0
        file_mode = 'wb'

    try:
        attempts_count = 0
        while attempts_count < retry:
            pre_response = session.get(url, stream=True)
            # 已下载完成检查
            total_length = int(pre_response.headers['content-length'])
            if resume_len != 0:
                # 将文件总长度并与本地文件对比
                if total_length is None or resume_len == total_length:
                    print('{0} is Already downloaded.'.format(name))
                    break

            # 构造下载请求
            session.headers['Range'] = 'bytes={:d}-'.format(resume_len)
            response = session.get(url, stream=True)

            # 响应流异常处理
            if response.status_code != 200 and response.status_code != 206:
                # 构建异常报文
                error_msg = "HTTP Error,Code:{0} ".format(response.status_code)
                if response.reason:
                    error_msg += ",Reason:\"{0}\"".format(response.reason)

                # 异常类型判断
                if response.status_code == 416:  # 检查416（客户端请求字节范围无法满足） -> 禁止resume
                    # TODO 该步的必要性还值得讨论，直接禁止resume是否过于暴力
                    print("local file:\"{0}\" may wrong,Stop resume.".format(name))
                    raise ValueError(error_msg)
                if attempts_count < retry:
                    wait_interval = min(2 ** (attempts_count + 1), 60)  # Exponential concession，Max 60s
                    print('Error to download \"{0}\", will retry in {1} seconds ...'.format(name, wait_interval))
                    time.sleep(wait_interval)
                    attempts_count += 1
                    continue
                else:
                    raise ConnectionError(error_msg)

            # 写入工作流
            with open(file, file_mode) as f:
                chunk_size = 4 * (1024 * 1024)
                widgets = [name, " ", progressbar.Bar(marker=">", left="[", right="]"), " ",
                           progressbar.Percentage(), " ", " ", progressbar.ETA(), " ", progressbar.FileTransferSpeed()]
                pbar = progressbar.ProgressBar(widgets=widgets, maxval=total_length).start()
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        pbar.update(os.path.getsize(file))
                pbar.finish()

            break
    except ValueError:
        download_file(session, url, file, resume=False)
    except ConnectionError as err:
        print(err.args)
        download_file(session, url, file)
    return


def download_queue(session, download_list, queue_length=8):  # 多线程下载模块
    queue = Queue()
    for x in range(queue_length):
        worker = DownloadQueue(queue)
        worker.daemon = True
        worker.start()
    for link_tuple in download_list:
        link, file_name = link_tuple
        queue.put((session, link, file_name))
    queue.join()
    print("The download task completed.")
