from .utils import *
from .sortinfo import *

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.87 Safari/537.36',
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    'Accept-Encoding': 'gzip, deflate, sdch',
    'Accept-Language': 'zh-CN,zh;q=0.8',
    'Content-Type': 'text/plain',
    "Connection": "keep-alive",
}


def raw_cookies_to_jar(raw_cookies):
    from http.cookies import SimpleCookie
    # Arrange Cookies from raw
    cookie = SimpleCookie()
    cookie.load(raw_cookies)
    cookies = {}
    for key, morsel in cookie.items():
        cookies[key] = morsel.value
    return cookies


def login_session(site="DEFAULT", conf=None):
    import requests
    session = requests.Session()
    session.headers.update(headers)
    if site == "icourse163":
        # 返回整理好的cookies
        if conf[site]["login_method"] == "Cookies":
            cookies = raw_cookies_to_jar(conf["icourse163"]["cookies"])
            session.cookies.update(cookies)
        elif conf[site]["login_method"] == "Account":
            raise IndexError("Not allow")
    if site == "xuetangx":
        if conf[site]["login_method"] == "Cookies":
            raise IndexError("Not allow")
        elif conf[site]["login_method"] == "Account":
            session.get("http://www.xuetangx.com/csrf_token")
            # csrftoken = session.cookies['csrftoken']
            session.post(url="http://www.xuetangx.com/v2/login_ajax", data={
                "username": conf[site]["username"],
                "password": conf[site]["password"]
            })
    return session
