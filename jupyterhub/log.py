"""logging utilities"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import traceback

from tornado.log import LogFormatter

def coroutine_traceback(typ, value, tb):
    """Scrub coroutine frames from a traceback
    
    Coroutine tracebacks have a bunch of identical uninformative frames at each yield point.
    This removes those extra frames, so tracebacks should be easier to read.
    This might be a horrible idea.
    
    Returns a list of strings (like traceback.format_tb)
    """
    all_frames = traceback.extract_tb(tb)
    useful_frames = []
    for frame in all_frames:
        if frame[0] == '<string>' and frame[2] == 'raise_exc_info':
            continue
        # start out conservative with filename + function matching
        # maybe just filename matching would be sufficient
        elif frame[0].endswith('tornado/gen.py') and frame[2] in {'run', 'wrapper'}:
            continue
        elif frame[0].endswith('tornado/concurrent.py') and frame[2] == 'result':
            continue
        useful_frames.append(frame)
    tb_list = ['Traceback (most recent call last):\n']
    tb_list.extend(traceback.format_list(useful_frames))
    tb_list.extend(traceback.format_exception_only(typ, value))
    return tb_list


class CoroutineLogFormatter(LogFormatter):
    """Log formatter that scrubs coroutine frames"""
    def formatException(self, exc_info):
        return ''.join(coroutine_traceback(*exc_info))

