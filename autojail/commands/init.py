from pathlib import Path

import ruamel.yaml

from .base import BaseCommand
from ..model import AutojailConfig, AutojailArch, AutojailLogin


class InitCommand(BaseCommand):
    """ Initializes an autojail project

    init
       {--f|force : if set overwrites existing autojail.yml}
       {--name= : name of the project}
       {--arch= : architecture of the project}
       {--cross-compile= : cross-compiler prefix eg. CROSS_COMPILE argument for jailhouse and kernel builds}
       {--jailhouse= : directory containing the jailhouse sources}
       {--kernel= : directory containing the kernel build}
       {--host= : hostname or ip address of target board}
       {--user= : username on target board}
       {--uart= : device node of local uart connected to target board}
       {--board= : if automate is installed the automate board id (if given selects automate backend)}
       {--a|automate : use automate as backend}
    """

    def handle(self):
        """ Initialize the project """
        if self.config_path.exists():
            if not self.option("force"):
                self.line(
                    "<error>This directory already contains an <comment>autojail.yml</comment> use -f to overwrite</error>"
                )
                return -1

        self.line("")
        self.line(
            "This command will guide you through the initialization of an autojail project"
        )
        self.line("")

        if self.option("board"):
            config = self._init_automate()
        elif self.option("host"):
            config = self._init_ssh()
        else:
            if self.automate_context:
                choices = ["ssh", "automate"]
                backend = self.choice(
                    "Which backend should be used to connect to the board",
                    choices,
                    attempts=3,
                    default=0,
                )

                # FIXME: should be fixed in updated clikit
                if isinstance(backend, int):
                    backend = choices[backend]

                if backend == "ssh":
                    config = self._init_ssh()
                else:
                    config = self._init_automate()

            else:
                config = self._init_ssh()

        with self.config_path.open("w") as config_file:
            yaml = ruamel.yaml.YAML()

            def represent_str(representer, data: str):
                return representer.represent_scalar(
                    "tag:yaml.org,2002:str", data
                )

            yaml.representer.add_representer(AutojailArch, represent_str)
            yaml.representer.add_representer(AutojailLogin, represent_str)
            config_dict = config.dict()
            yaml.dump(config_dict, config_file)

    def _init_automate(self) -> AutojailConfig:
        "Initialize the backend with test rack"

        name = self.option("name")
        if not name:
            name = Path.cwd().name.lower()

            question = self.create_question(
                f"Project name [<comment>{name}</comment>]", default=name
            )
            name = self.ask(question)

        board = self.option("board")
        if not board:
            choices = [b.name for b in self.automate_context.boards()]
            board = self.choice(
                "Which target board should be used:",
                choices,
                attempts=3,
                default=0,
            )

        automate_board = self.automate_context.board(board)

        os = automate_board.os
        arch = "ARM64" if os.triple.machine.name == "aarch64" else "ARM"
        compiler = automate_board.compiler(toolchain="gcc")
        cross_compile = str(compiler.bin_path / compiler.prefix)
        kernel_dir = "kernel"
        jailhouse_dir = "jailhouse"
        uart = None

        config = AutojailConfig(
            login=f"automate:{board}",
            arch=arch,
            cross_compile=cross_compile,
            kernel_dir=kernel_dir,
            jailhouse_dir=jailhouse_dir,
            uart=uart,
        )

        return config

    def _init_ssh(self) -> AutojailConfig:
        "Initialize the project with direct ssh connection"
        name = self.option("name")
        if not name:
            name = Path.cwd().name.lower()

            question = self.create_question(
                f"Project name [<comment>{name}</comment>]", default=name
            )
            name = self.ask(question)

        arch = self.option("arch")
        if not arch:
            arch = "ARM64"
            choices = ["ARM64", "ARM"]
            arch = self.choice(
                "What is the base architecture of the board?",
                choices,
                attempts=3,
                default=0,
            )

            # FIXME: in non interactive mode clikit return default number instead of value
            if isinstance(arch, int):
                arch = choices[arch]

        cross_compile = self.option("cross-compile")
        if not cross_compile:
            defaults = {
                "ARM64": "aarch64-linux-gnu-",
                "ARM": "arm-linux-gnueabihf-",
            }

            cross_compile = defaults[arch]

            question = self.create_question(
                f"Cross compiler prefix [<comment>{cross_compile}</comment>]",
                default=cross_compile,
            )
            cross_compile = self.ask(question)

        host = self.option("host")
        if not host:
            host = "10.42.0.100"  # This is the default IP-Address when using Network Manager connection sharing
            question = self.create_question(
                f"Hostname or IP of target board [<comment>{host}</comment>]",
                default=host,
            )
            host = self.ask(question)

        user = self.option("user")
        if not user:
            user = "root"
            question = self.create_question(
                f"Username on the target board [<comment>{user}</comment>]",
                default=user,
            )
            user = self.ask(question)

        uart = self.option("uart")
        if not uart:
            uart = "/dev/ttyUSB0"
            if not Path(uart).exists():
                uart = ""

            question = self.create_question(
                f"Serial interface connected to board: [<comment>{uart}</comment>]",
                default=uart,
            )
            uart = self.ask(question)

        kernel_dir = self.option("kernel")
        if not kernel_dir:
            kernel_dir = "./kernel"
            question = self.create_question(
                f"Directory containing the kernel build [<comment>{kernel_dir}</comment>]",
                default=kernel_dir,
            )
            kernel_dir = self.ask(question)

        jailhouse_dir = self.option("jailhouse")
        if not jailhouse_dir:
            jailhouse_dir = "./jailhouse"
            question = self.create_question(
                f"Directory containing the jailhouse sources [<comment>{jailhouse_dir}</comment>]",
                default=jailhouse_dir,
            )
            jailhouse_dir = self.ask(question)

        # TODO: ask for baud rate and rest of uart config
        config = AutojailConfig(
            login=f"ssh:{user}@{host}",
            arch=arch,
            cross_compile=cross_compile,
            kernel_dir=kernel_dir,
            jailhouse_dir=jailhouse_dir,
            uart=uart,
        )

        return config
