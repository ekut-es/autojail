from logging import getLogger
from typing import List, Tuple

from ..model import Board, JailhouseConfig, ShmemConfigNet
from .passes import BasePass


class NetworkConfigPass(BasePass):
    def __init__(self):
        self.logger = getLogger()

    def __call__(
        self, board: Board, config: JailhouseConfig
    ) -> Tuple[Board, JailhouseConfig]:
        if config.shmem:

            link_configs: List[ShmemConfigNet] = []
            for _cell_name, link in config.shmem.items():
                if not isinstance(link, ShmemConfigNet):
                    continue

                link_configs.append(link)

        return board, config

    def autoconf_networks(self, network_config):
        pass

    def lower_networks(self, network_config):
        pass
