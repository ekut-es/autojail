import shlex
import subprocess


def start_board(autojail_config, cwd=None):
    if autojail_config.start_command:
        for command in autojail_config.start_command:
            subprocess.run(shlex.split(command), cwd=cwd)


def stop_board(autojail_config, cwd=None):
    if autojail_config.stop_command:
        for command in autojail_config.stop_command:
            subprocess.run(shlex.split(command), cwd=cwd)
