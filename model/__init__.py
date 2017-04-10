# -*- coding: utf-8 -*-
from .download import *
from .login import login_session as login
from .config import load_config as config


def sort_teacher(teacher_list: list) -> str:
    teacher_name = []
    for i in teacher_list:
        teacher_name.append(i.string)
        if len(teacher_name) >= 3:
            teacher_name[2] += '等'
            break
    return '、'.join(teacher_name)
