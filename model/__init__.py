# -*- coding: utf-8 -*-
import re
import errno

from .download import *
from .sortinfo import out_info
from .login import login_session as login


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


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "on", "1")