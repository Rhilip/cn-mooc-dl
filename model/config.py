# -*- coding: utf-8 -*-
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
        self.Download_Path = setting["Download_Path"]
        self.Download_Docs = str2bool(setting["Download_Docs"])
        self.Download_Srt = str2bool(setting["Download_Srt"])


def sort_config(config_file, site):
    config = configparser.ConfigParser()
    config.read(config_file, encoding="utf-8-sig")
    return Config(config[site])
