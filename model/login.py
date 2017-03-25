# -*- coding: utf-8 -*-
"""
This model help you to login the site,And the main function : login_session() will return a requests.session to do next.
"""
import requests
from http.cookies import SimpleCookie


def cookies_raw2jar(raw: str) -> dict:
    """
    Arrange Cookies from raw using SimpleCookies
    """
    cookie = SimpleCookie(raw)
    cookies = {}
    for key, morsel in cookie.items():
        cookies[key] = morsel.value
    return cookies


def login_session(site="DEFAULT", conf=None) -> requests.session():
    login_session = requests.Session()
    login_session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.87 Safari/537.36',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    })

    # 各个站点的方法
    if site == "icourse163":
        # 返回整理好的cookies
        if conf.login_method == "Cookies":
            cookies = cookies_raw2jar(conf.cookies)
            login_session.cookies.update(cookies)
        elif conf.login_method == "Account":
            raise IndexError("Not allow")
    if site == "xuetangx":
        if conf.login_method == "Cookies":
            raise IndexError("Not allow")
        elif conf.login_method == "Account":
            login_session.get("http://www.xuetangx.com/csrf_token")
            # csrftoken = session.cookies['csrftoken']
            login_session.post(url="http://www.xuetangx.com/v2/login_ajax", data={
                "username": conf.username,
                "password": conf.password
            })
    return login_session
