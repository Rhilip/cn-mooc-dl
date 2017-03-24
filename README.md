# cn-mooc-dl
Since most Scripts in [renever/cn_mooc_dl](https://github.com/renever/cn_mooc_dl) and it's networks are not able to work,
I wrote another repository to download those MOOC Courses.

## Remember
* Some codes are from [renever/cn_mooc_dl](https://github.com/renever/cn_mooc_dl), Thanks.
* ~~I use cookies,but not account with password to entry the website.~~
* ~~I use Download tools to download main video,and a script(ren.bat) to rename it.~~

## How it work
### 1) Prerequisites
The following dependencies are required and must be installed separately.
* [Python3](https://www.python.org/downloads/),and install it into PATH.
* Model [Request](http://docs.python-requests.org/zh_CN/latest/user/install.html#install) and [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/index.zh.html#id5),You can use this command:
```
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple requests beautifulsoup4 html5lib progressbar2
```
* Also don't forget download this packet or one of this scripts ......

### 2) Supported Sites

| File | Site | URL | Videos?  | Documents? | Subtitle?|
|:-------------:|:------------------:|:---:|:---:|:---:|:---:|
| icourse163-dl.py | 中国大学MOOC | <http://www.icourse163.org/> | ✓ | ✓ | ✓ |
| xuetangx-dl.py | 学堂在线 | <http://www.xuetangx.com/> | ✓ | ?| ? |

### 3) Instruction manual
See [Wiki](wiki) please.

## Test Environment
* Python :`v3.5.2`
* OS : `Windows 10` and `Chrome 55`
* IDE : `IntelliJ IDEA 2016.3.4`
* Download tools :`IDM`

## Met Problem
* Issues Please~