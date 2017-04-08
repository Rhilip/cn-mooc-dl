import re
import requests
from bs4 import BeautifulSoup

course_url = 'http://ocw.nctu.edu.tw/course_detail_1.php?bgid=6&gid=0&nid=523'

nid = re.search(r'nid=(\d*)',course_url).group(1)
open("课程说明.txt","a").write("課程地址：http://ocw.nctu.edu.tw/course_detail.php?bgid=6&gid=0&nid=" + nid + "\n\n課程資料下載鏈接\n\n")

bs_3 = BeautifulSoup(requests.get("http://ocw.nctu.edu.tw/course_detail_3.php?bgid=6&gid=0&nid="+nid).text,"lxml")
for i in bs_3.find_all('a',href=re.compile(r"mp4")):
    lesson_name = i.parent.parent.previous_sibling.previous_sibling.get_text(strip=True)
    lesson_link = i['href']
    print(lesson_name, lesson_link)
    open("课程说明.txt", "a").write(lesson_name + lesson_link + "\n")

bs_4 = BeautifulSoup(requests.get("http://ocw.nctu.edu.tw/course_detail_4.php?bgid=6&gid=0&nid="+nid).text,"lxml")
for i in bs_4.find_all('a',href=re.compile(r"pdf")):
    docs_name = i.parent.parent.previous_sibling.previous_sibling.get_text(strip=True)
    docs_link = i['href']
    print(docs_name, docs_link)
    open("课程说明.txt", "a").write(docs_name + docs_link + "\n")