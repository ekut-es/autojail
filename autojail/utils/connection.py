import getpass
from typing import TYPE_CHECKING

from fabric import Connection

from paramiko.ssh_exception import (
    AuthenticationException,
    PasswordRequiredException,
)

if TYPE_CHECKING:
    from ..model import AutojailConfig


def connect(config: "AutojailConfig", context, passwd_retries=5):
    login = config.login
    connection = None
    if login.is_ssh:
        try:
            connection = Connection(login.host, user=login.user)
        except (AuthenticationException, PasswordRequiredException):
            for _retry in range(passwd_retries):

                password = getpass.getpass(
                    prompt="Password for {}@{}: ".format(login.user, login.host)
                )
                try:
                    connection = Connection(
                        user=login.user,
                        host=login.host,
                        connect_kwargs={"password": password},
                    )
                    connection.open()
                except (AuthenticationException, PasswordRequiredException):
                    continue

    else:
        assert context is not None
        connection = context.board(login.host).connect()
    return connection
