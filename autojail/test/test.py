""" Definition of standard tests """

from collections import defaultdict
from typing import Any, Dict

from ..model import AutojailConfig, Board, CellConfig, JailhouseConfig
from ..model.test import TestEntry


class TestProvider:
    def __init__(
        self,
        autojail_config: AutojailConfig,
        config: JailhouseConfig,
        board: Board,
    ) -> None:
        self.autojail_config = autojail_config
        self.board = board
        self.config = config

    def cell_name_dash(self, cell: CellConfig) -> str:
        return cell.name.lower().replace(" ", "-")

    def cell_name_underscore(self, cell: CellConfig) -> str:
        return cell.name.lower().replace(" ", "_")

    def _get_start_cell(self, cell: CellConfig):
        script = []
        assertions: Any = defaultdict(list)

        cell_name = self.cell_name_underscore(cell)
        script.append(f"sudo /etc/jailhouse/enable.sh start_{cell_name}")

        root_flags = self.config.root_cell.flags
        if "SYS_VIRTUAL_DEBUG_CONSOLE" in root_flags:

            script.append("sudo jailhouse console > /tmp/debug_console.out")
            if cell.type == "root":
                assertions["debug_console"].append("Initializing processor")
                assert cell.cpus is not None
                for cpu in cell.cpus:
                    assertions["debug_console"].append(f" CPU {cpu}... OK")
                assertions["debug_console"].append("Activating hypervisor")
            else:
                assertions["debug_console"].append(
                    f'Created cell "{cell.name}"'
                )
                assertions["debug_console"].append(
                    f'Cell "{cell.name}" can be loaded'
                )
                assertions["debug_console"].append(
                    f'Started cell "{cell.name}"'
                )

    def tests(self):
        tests: Dict[str, TestEntry] = {}

        for cell in self.config.cells.values():
            tests[
                f"start_{self.cell_name_underscore(cell)}"
            ] = self._get_start_cell(cell)

        return tests
