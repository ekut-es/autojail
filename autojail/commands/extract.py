import tempfile
import os
import subprocess

from pathlib import Path
from shutil import rmtree

import ruamel.yaml

from .base import BaseCommand
from ..utils import connect
from ..extract import BoardInfoExtractor
from ..model import (
    ExpressionInt,
    HexInt,
    ByteSize,
    IntegerList,
    JailhouseFlagList,
)


class ExtractCommand(BaseCommand):
    """ Extracts hardware specific information from target board

    extract
        {--b|base-folder= : base folder containing relevant /proc/ and /sys/ entries of target board}
    """

    def handle(self):
        base_folder = self.option("base-folder")
        tmp_folder = False
        connection = None
        try:
            if not base_folder or not Path(base_folder).exists():
                self.line(
                    f"Extracting target data from board {self.autojail_config.login}"
                )
                connection = connect(
                    self.autojail_config, self.automate_context
                )
                if not base_folder:
                    base_folder = tempfile.mkdtemp(prefix="aj-extract")
                    tmp_folder = True
                self._sync(connection, base_folder)
            else:
                self.line(f"Extracting target data from folder {base_folder}")

            extractor = BoardInfoExtractor(
                self.autojail_config.name,
                self.autojail_config.board,
                base_folder,
            )
            board_data = extractor.extract()

            with (Path.cwd() / self.BOARD_CONFIG_NAME).open("w") as f:
                yaml = ruamel.yaml.YAML()
                yaml.register_class(HexInt)
                yaml.register_class(ByteSize)
                yaml.register_class(IntegerList)
                yaml.register_class(JailhouseFlagList)
                yaml.register_class(ExpressionInt)
                yaml.dump(board_data.dict(), f)
        finally:
            if connection:
                connection.close()

            if tmp_folder:
                rmtree(base_folder, ignore_errors=True)

    def _sync(self, connection, base_folder):
        base_folder = Path(base_folder)
        if not base_folder.exists():
            base_folder.mkdir(exists_ok=True, recursive=True)

        res = connection.run("mktemp -d", warn=True, hide="both")
        target_tmpdir = res.stdout.strip()

        with connection.cd(target_tmpdir):
            for file_name in self.files:
                connection.run(
                    f"sudo cp --parents -r {file_name} .",
                    warn=True,
                    hide="both",
                )

            res = connection.run(f"getconf -a > {target_tmpdir}/getconf.out")

            connection.run("sudo tar czf extract.tar.gz *")
            connection.get(
                f"{target_tmpdir}/extract.tar.gz",
                local=f"{base_folder}/extract.tar.gz",
            )
            connection.run(f"sudo rm -rf {target_tmpdir}")

        subprocess.run("tar xzf extract.tar.gz".split(), cwd=base_folder)

        os.unlink(f"{base_folder}/extract.tar.gz")

    files = [
        "/sys/bus/pci/devices/*/config",
        "/sys/bus/pci/devices/*/resource",
        "/sys/devices/system/cpu/cpu*/uevent",
        "/sys/firmware/devicetree",
        "/proc/iomem",
        "/proc/cpuinfo",
        "/proc/cmdline",
        "/proc/ioports",
    ]
