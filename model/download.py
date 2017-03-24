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

import progressbar
import requests

from threading import Thread

# TODO Use Thread to Download multiple files at the same time
class DownloadQueue(Thread):
    from queue import Queue
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


def download_file(session: requests.Session(), url: str, file: str, resume=True, retry=4):
    name = file.split("\\")[-1]
    if resume and os.path.exists(file):
        resume_len = os.path.getsize(file)
        file_mode = 'ab'
    else:
        resume_len = 0
        file_mode = 'wb'
    #
    attempts_count = 0
    while attempts_count < retry:
        response = session.get(url, stream=True)
        # 检查响应流状况
        if response.status_code != 200 and response.status_code != 206:
            if response.reason:
                error_msg = response.reason + ' ' + str(response.status_code)
            else:
                error_msg = 'HTTP Error ' + str(response.status_code)

            if attempts_count + 1 < retry:
                wait_interval = 2 ** (attempts_count + 1)  # 指数退让
                msg = 'Error downloading, will retry in {0} seconds ...'
                print(msg.format(wait_interval))
                time.sleep(wait_interval)
                attempts_count += 1
                continue
            else:
                raise ConnectionError(error_msg)

        # 获取文件总长度
        total_length = int(response.headers['content-length'])

        if resume_len != 0:
            if total_length is None or resume_len == total_length:
                print('{0} is Already downloaded.'.format(name))
                break

        session.headers['Range'] = 'bytes=%d-' % resume_len
        response = session.get(url, stream=True)

        # 写入工作流
        with open(file, file_mode) as f:
            chunk_size = 1048576
            widgets = ["Progress: ", progressbar.Percentage(), " ",
                       progressbar.Bar(marker=">", left="[", right="]"),
                       " ", progressbar.ETA(), " ", progressbar.FileTransferSpeed()]
            pbar = progressbar.ProgressBar(widgets=widgets, maxval=total_length).start()
            length = 0
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    # f.flush()     # 文件先下载至缓存区，只有当文件全部下载完成才写入
                length += len(chunk)
                pbar.update(os.path.getsize(file))
            pbar.finish()
