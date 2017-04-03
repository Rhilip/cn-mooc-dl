# -*- coding: utf-8 -*-
"""
This module help you to load config from settings.conf
by Rhilip , v20170324
"""
import configparser


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "on", "1")


class Config:
    def __init__(self, setting):
        # Login method
        self.login_method = setting["login_method"]
        if self.login_method == "Cookies":
            self.cookies = setting["cookies"]
        elif self.login_method == "Account":
            self.username = setting["username"]
            self.password = setting["password"]

        # Download Setting
        self.Download = str2bool(setting["Download"])
        self.Download_Method = setting["Download_Method"]

        self.Download_Path = setting["Download_Path"]
        self.Download_Docs = str2bool(setting["Download_Docs"])
        self.Download_Srt = str2bool(setting["Download_Srt"])

        self.Download_Queue_Length = int(setting["Download_Queue_Length"])


def load_config(config_file, site):
    config = configparser.RawConfigParser()
    config.read(config_file, encoding="utf-8-sig")
    return Config(config[site])
