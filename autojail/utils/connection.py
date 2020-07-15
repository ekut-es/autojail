from fabric import Connection

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..model import AutojailConfig


def connect(config: "AutojailConfig", context):
    login = config.login
    connection = None
    if login.is_ssh:
        connection = Connection(login.host, user=login.user)
    else:
        assert context is not None
        connection = context.board(login.host).connect()
    return connection
