"""Miscellaneous utilities"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import socket
import time
from subprocess import check_call, CalledProcessError, STDOUT, PIPE

from IPython.html.utils import url_path_join

def random_port():
    """get a single random port"""
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def wait_for_server(ip, port, timeout=10):
    """wait for a server to show up at ip:port"""
    tic = time.time()
    while time.time() - tic < timeout:
        try:
            socket.create_connection((ip, port))
        except socket.error:
            time.sleep(0.1)
        else:
            break
