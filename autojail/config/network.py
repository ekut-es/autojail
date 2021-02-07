from logging import getLogger
from typing import Tuple

from ..model import Board, JailhouseConfig, ShmemConfigNet
from .passes import BasePass


class NetworkConfigPass(BasePass):
    def __init__(self):
        self.logger = getLogger()

    def __call__(
        self, board: Board, config: JailhouseConfig
    ) -> Tuple[Board, JailhouseConfig]:
        if config.shmem:

            for _cell_name, link in config.shmem.items():

                from devtools import debug

                debug(link)

                if not isinstance(link, ShmemConfigNet):
                    continue

        return board, config

    def lower_networks(self, network_config):
        pass
