import logging
import subprocess
from pathlib import Path

from ..model import AutojailConfig

MODULE_DIR = Path(__file__).parent.absolute() / "clocks"


class ClockInfoExtractor:
    def __init__(self, config: AutojailConfig):
        self.config = config

        self.logger = logging.getLogger()

    def prepare(self):
        self.logger.info("Building Kernel Module for target")

        clean_command = [
            "make",
            "-C",
            f"{MODULE_DIR}",
            f"ARCH={self.config.arch.lower()}",
            f"CROSS_COMPILE={self.config.cross_compile}",
            f"KDIR={Path(self.config.kernel_dir).absolute()}",
        ]

        ret = subprocess.run(clean_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if ret.returncode:
            self.logger.warning("Could not clean kernel module")
            self.logger.info(ret.stdout)
            self.logger.info(ret.stderr)

        compile_command = [
            "make",
            "-C",
            f"{MODULE_DIR}",
            f"ARCH={self.config.arch.lower()}",
            f"CROSS_COMPILE={self.config.cross_compile}",
            f"KDIR={Path(self.config.kernel_dir).absolute()}",
        ]

        ret = subprocess.run(compile_command)
        if ret.returncode:
            self.logger.warning("Could not build kernel module")
            self.logger.info(ret.stdout)
            self.logger.info(ret.stderr)

    def start(self, connection):
        module_local = MODULE_DIR / "extract-clocks.ko"
        if not module_local.exists():
            self.logger.warning("Kernel module does not exist")

        connection.put(str(module_local), remote="/tmp/")
        connection.run(
            "sudo /sbin/insmod /tmp/extract-clocks.ko",
            shell=True,
            warn=True,
            in_stream=False,
        )

    def stop(self, connection):
        connection.run(
            "sudo /sbin/rmmod extract-clocks.ko",
            shell=True,
            warn=True,
            in_stream=False,
        )
