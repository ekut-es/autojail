import getpass
import time
from typing import TYPE_CHECKING, Any

from fabric.connection import Connection
from paramiko.ssh_exception import (
    AuthenticationException,
    PasswordRequiredException,
    SSHException,
)

if TYPE_CHECKING:
    from ..model import AutojailConfig

global_context = None


def connect(
    config: "AutojailConfig",
    context: Any,
    passwd_retries: int = 5,
    timeout_retries=10,
) -> Connection:
    login = config.login
    connection = None
    if login.is_ssh:
        try:
            for _timeout_retry in range(timeout_retries):
                try:
                    connect_kwargs = None
                    if config.password is not None:
                        connect_kwargs = {"password": config.password}
                    connection = Connection(
                        login.host,
                        user=login.user,
                        port=login.port,
                        connect_kwargs=connect_kwargs,
                    )
                    connection.open()
                except SSHException as e:
                    if _timeout_retry == timeout_retries - 1:
                        raise e

                    if isinstance(e, AuthenticationException):
                        if config.password is not None:
                            time.sleep(5)
                            continue
                        else:
                            raise e
                    time.sleep(5)
                    continue
                except EOFError as e:
                    if _timeout_retry == timeout_retries - 1:
                        raise e
                    time.sleep(5)
                    continue
                break

        except (
            AuthenticationException,
            PasswordRequiredException,
            SSHException,
            EOFError,
        ) as e:
            if config.password is not None:
                raise e
            for _retry in range(passwd_retries):

                password = getpass.getpass(
                    prompt="Password for {}@{}:{}: ".format(
                        login.user, login.host, login.port
                    )
                )
                try:
                    for _timeout_retry in range(timeout_retries):
                        try:
                            connection = Connection(
                                user=login.user,
                                host=login.host,
                                port=login.port,
                                connect_kwargs={"password": password},
                            )
                            connection.open()
                        except SSHException as e:
                            if isinstance(e, AuthenticationException):
                                raise e
                            time.sleep(5)
                            continue
                        except EOFError:
                            time.sleep(5)
                            continue
                        break
                except (
                    AuthenticationException,
                    PasswordRequiredException,
                    SSHException,
                ):
                    continue

                break

    else:
        assert context is not None
        connection = context.board(login.host).connect()
    return connection
