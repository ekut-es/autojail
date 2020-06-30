import subprocess
from pathlib import Path
from typing import List, Union
from tempfile import mktemp

import fdt


class RangeEntry:
    start: int
    size: int


class WalkerState:
    node: fdt.Node
    address_cells: int
    size_cells: int
    current_ranges: List[RangeEntry]


class DeviceTreeExtractor:
    def __init__(self, dt: Union[str, Path]) -> None:
        dt_path = Path(dt)
        if dt_path.is_dir():
            temp_file = mktemp(suffix=".dtb")
            try:
                subprocess.run(
                    f"dtc -I fs -O dtb -o {temp_file} {str(dt_path)}".split()
                )

                with open(temp_file, "rb") as f:
                    self.fdt = fdt.parse_dtb(f.read())
            finally:
                print(temp_file)
                # Path(temp_file[1]).unlink()
        else:
            with dt_path.open("rb") as f:
                self.fdt = fdt.parse_dtb(f.read())

        self.aliases = {}
        self.handles = {}

    def _extract_aliases(self):
        if self.fdt.exist_node("/aliases"):
            aliases_node = self.fdt.get_node("/aliases")
            for prop in aliases_node.props:
                self.aliases[prop.name] = prop.value

    def _walk_tree(self):

        self.worklist

    def run(self):
        self._extract_aliases()
        self._walk_tree()
