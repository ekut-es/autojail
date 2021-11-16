""" Definition of standard tests """

from collections import defaultdict
from typing import Any, Dict, Optional

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
        script.append("sleep 10")
        root_flags = self.config.root_cell.flags
        if "SYS_VIRTUAL_DEBUG_CONSOLE" in root_flags:
            script.append("sudo jailhouse console > /tmp/debug_console.out")
            if cell.type == "root":
                assertions["/tmp/debug_console.out"].append(
                    "Initializing processor"
                )
                assert cell.cpus is not None
                for cpu in cell.cpus:
                    assertions["/tmp/debug_console.out"].append(
                        f" CPU {cpu}... OK"
                    )
                assertions["/tmp/debug_console.out"].append(
                    "Activating hypervisor"
                )
            else:
                assertions["/tmp/debug_console.out"].append(
                    f'Created cell "{cell.name}"'
                )
                assertions["/tmp/debug_console.out"].append(
                    f'Cell "{cell.name}" can be loaded'
                )
                assertions["/tmp/debug_console.out"].append(
                    f'Started cell "{cell.name}"'
                )
        script.append("sudo /etc/jailhouse/enable.sh stop")
        return TestEntry(script=script, check=dict(assertions))

    def _get_start_all(self):
        script = []
        script.append("sudo /etc/jailhouse/enable.sh start")
        script.append("sleep 10")
        script.append("sudo /etc/jailhouse/enable.sh stop")
        return TestEntry(script=script)

    def _get_cell_ip(self, name) -> Optional[str]:
        ip = None
        if self.config.shmem is None:
            return None
        for shmem in self.config.shmem.values():
            if shmem.protocol != "SHMEM_PROTO_VETH":
                continue

            assert hasattr(shmem, "network")
            for cell_name, network in shmem.network.items():  # type: ignore
                if cell_name == name:
                    ip = network.addresses[0].ip  # type: ignore

        return ip

    def _get_cyclictest(self):
        script = []
        script.append("sudo /etc/jailhouse/enable.sh start")
        script.append("sleep 10")
        assertions = {}
        timeout = 30
        for name, cell in self.config.cells.items():
            if cell.type == "linux":
                cell_ip = self._get_cell_ip(name)
                if cell_ip is not None:
                    output_name = f"/tmp/cyclictest_{name}.txt"
                    script.append(
                        f'ssh root@{cell_ip} "cyclictest  -D {timeout}s -m -q -a -t 4 -p 70 --priospread" > {output_name} &'
                    )
                    assertion = r"T:\W*(?P<thread_num>[0-9]+)\W*\(\W*(?P<thread_id>[0-9]+)\)\W*P:\W*(?P<priority>[0-9]+)\W*I:\W*(?P<intervall>[0-9]+)\W+C:\W*(?P<cycles>[0-9]+)\W*Min:\W*(?P<min_latency>[0-9]+)\W*Act:\W*([0-9]+)\W*Avg:\W*(?P<avg_latency>[0-9]+)\W+Max:\W*(?P<max_latency>[0-9]+)"
                    assertions[output_name] = [assertion]

            elif cell.type == "root":
                script.append(
                    f"stress --cpu 8 --io 4 --vm 2 --vm-bytes 128M --timeout {timeout}s &"
                )
        script.append("wait")

        script.append("sudo /etc/jailhouse/enable.sh stop")

        return TestEntry(script=script, log=assertions)

    def tests(self):
        tests: Dict[str, TestEntry] = {}

        for cell in self.config.cells.values():
            tests[
                f"start_{self.cell_name_underscore(cell)}"
            ] = self._get_start_cell(cell)
        tests["start_all"] = self._get_start_all()
        tests["cyclictest_all"] = self._get_cyclictest()

        return tests
