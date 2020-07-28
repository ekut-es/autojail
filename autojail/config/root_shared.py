from typing import Tuple

from ..model import Board, JailhouseConfig
from .passes import BasePass


class InferRootSharedPass(BasePass):
    def __call__(
        self, board: Board, config: JailhouseConfig
    ) -> Tuple[Board, JailhouseConfig]:
        root_cell = None
        for cell in config.cells.values():
            if cell.type == "root":
                root_cell = cell
                break

        if root_cell is None:
            self.logger.warning("Could not find root cell")
            return board, config

        return board, config
