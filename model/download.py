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

from html import unescape
from urllib.parse import unquote
from queue import Queue
from threading import Thread


def link_check(hostname: str, href: str) -> str:
    href = href.strip()
    if href.find("http") == -1:  # TODO 看下这么判断是否是相对链接是否合适
        href = "{0}{1}".format(hostname, href)
    return href


def generate_path(path_list: list) -> str:
    return_path = ""
    for path in path_list:
        return_path = os.path.join(return_path, path)
    return return_path


def clean_filename(string: str) -> str:
    """
    Sanitize a string to be used as a filename.

    If minimal_change is set to true, then we only strip the bare minimum of
    characters that are problematic for filesystems (namely, ':', '/' and '\x00', '\n').
    """
    string = unescape(string)
    string = unquote(string)
    string = re.sub(r'<(?P<tag>.+?)>(?P<in>.+?)<(/(?P=tag))>', "\g<in>", string)

    string = string.replace(':', '_').replace('/', '_').replace('\x00', '_')

    string = re.sub('[\n\\\*><?\"|\t]', '', string)
    string = string.strip()

    return string


def raw_unicode_escape(string: str) -> str:
    return string.encode('utf-8').decode('unicode_escape').encode('gbk', 'ignore').decode('gbk', 'ignore')


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


# Direct
class DownloadQueue(Thread):
    queue = Queue()

    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            # Get the work from the queue and expand the tuple
            session, url, filename = self.queue.get()
            direct_download(session, url, filename)
            self.queue.task_done()


def direct_download(session: requests.Session(), url: str, file: str, resume=True, retry=4):
    name = os.path.split(file)[1]
    mkdir_p(os.path.split(file)[0])
    if resume and os.path.exists(file):
        resume_len = os.path.getsize(file)
        file_mode = 'ab'
    else:
        resume_len = 0
        file_mode = 'wb'

    attempts_count = 0
    while attempts_count < retry:
        wait_interval = min(2 ** (attempts_count + 1), 60)  # Exponential concession，Max 60s
        try:
            pre_response = session.get(url, stream=True)

            # 已下载完成检查
            total_length = int(pre_response.headers['content-length'])
            if resume_len != 0:
                # 将文件总长度并与本地文件对比
                if total_length is None or resume_len == total_length:
                    print('{0} is Already downloaded.'.format(name))
                    break

            # 创建标记文件
            open("{file}.temp".format(file=file), "w+").close()

            # TODO 多线程下载
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
                    print(error_msg + "local file:\"{0}\" may wrong,Stop resume.".format(name))
                    raise ValueError(error_msg)
                if attempts_count < retry:
                    print('Error to download \"{0}\", will retry in {1}s.'.format(name, wait_interval))
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

            # 下载完成，移除标记文件，退出
            os.remove("{file}.temp".format(file=file))  # 完成下载 -> 移除标记文件
            return
        except ValueError:
            resume_len = 0
            file_mode = 'wb'
            continue
        except requests.exceptions.ConnectionError:
            print('Error to download \"{0}\",time: {1},will retry in {2}s'.format(name, attempts_count, wait_interval))
            attempts_count += 1
            continue


def download_queue(session, download_list, queue_length=1):  # 多线程下载模块
    if download_list:
        print("Begin Download~")
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
    return


# Aria2
class Aria2JsonRpc(object):
    """
    Rewrite from https://github.com/imn5100/python_test/blob/master/src/downloadUtil/Aria2Rpc.py ,thx
    """

    def __init__(self, rpc_url="http://localhost:6800/jsonrpc"):
        self.rpc_url = rpc_url

        if not self.isAlive():
            raise ConnectionError("The aria2c may not start,Please check.")

    def execuetJsonRpcCmd(self, method, param=None):
        payload = {"jsonrpc": "2.0", "method": method, "id": 1, "params": param}
        payloads = [payload]
        r = requests.post(self.rpc_url, None, payloads)
        if r.status_code == 200:  # 添加成功
            # print(r.text)  # [{"id":1,"jsonrpc":"2.0","result":"437f9aeec42e79e9"}]
            result = re.search(r"\"result\":\"(.+?)\"", r.text).group(1)
            return result

    def isAlive(self):
        payload = {"jsonrpc": "2.0", "method": "aria2.tellActive", "id": 1}
        try:
            r = requests.get(self.rpc_url, payload)
            return r.status_code == 200
        except Exception:
            return False

    def addUris(self, urls, dir=None, out=None):
        params = []
        download_config = {}
        if dir:
            download_config["dir"] = dir
        if out:
            download_config["out"] = out
        params.append(urls)
        params.append(download_config)
        # 添加下载任务
        added_result = self.execuetJsonRpcCmd("aria2.addUri", params)
        print("result:{0} for \"{1}\" ,which link:\"{2}\"".format(added_result, out, urls[0]))


def aira2_download(download_list):
    print("Use Aria2 to Download~")
    aria2_rpc = Aria2JsonRpc("http://localhost:6800/jsonrpc")
    for link_tuple in download_list:
        link, file = link_tuple
        loc, name = os.path.split(file)
        aria2_rpc.addUris(urls=[link], dir=loc, out=name)
    print("Add download list to Aria2 OK~")
