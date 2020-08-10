import io
import socket
from typing import Union
from urllib.parse import urlparse

import serial


def open_serial(
    url: str, encoding: str = "utf-8"
) -> Union[io.RawIOBase, serial.Serial]:
    parsed_url = urlparse(url)
    if parsed_url.scheme == "unix":
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(parsed_url.path)
        return sock.makefile("rw", encoding=encoding)
    else:
        return serial.serial_for_url(url, encoding=encoding)
