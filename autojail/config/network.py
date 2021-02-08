import itertools
from ipaddress import IPv4Network, IPv6Network, ip_interface, ip_network
from logging import getLogger
from typing import List, Tuple

from ..model import Board, JailhouseConfig, ShmemConfigNet
from ..model.jailhouse import InterfaceConfig
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

            self._lower_networks(link_configs)
            self._autoconf_networks(link_configs, board.ip_info)

            from devtools import debug

            debug(config.shmem)

        return board, config

    def _autoconf_networks(
        self, network_configs: List[ShmemConfigNet], ip_info
    ):
        unconfigured_networks = []
        used_v4: List[IPv4Network] = []
        used_v6: List[IPv6Network] = []
        for config in network_configs:
            if not config.network:
                unconfigured_networks.append(config)
            else:
                assert isinstance(config.network, dict)
                for _cell_name, interface_config in config.network.items():
                    for address in interface_config.addresses:
                        network = ip_network(address)
                        if isinstance(network, IPv6Network):
                            used_v6.append(network)
                        elif isinstance(network, IPv4Network):
                            used_v4.append(network)

        for interface in ip_info:
            if "LOOPBACK" in interface["flags"]:
                continue
            for addr_info in interface["addr_info"]:
                network = ip_network(
                    f"{addr_info['local']}/{addr_info['prefixlen']}",
                    strict=False,
                )
                if isinstance(network, IPv6Network):
                    used_v6.append(network)
                elif isinstance(network, IPv4Network):
                    used_v4.append(network)

        v4_candidates = [ip_network("10.0.0.0/8"), ip_network("192.168.0.0/16")]
        v6_candidates = [ip_network("fd00::/8")]

        def exclude_used(candidates, used):
            for exclude in used:
                old_candidates = candidates
                candidates = []
                for candidate in old_candidates:
                    if candidate.overlaps(exclude):
                        candidates.extend(candidate.address_exclude(exclude))
                    else:
                        candidates.append(candidate)
            return candidates

        v4_candidates = exclude_used(v4_candidates, used_v4)
        v6_candidates = exclude_used(v6_candidates, used_v6)

        v4_generator = itertools.chain.from_iterable(
            (
                net.subnets(new_prefix=24)
                for net in v4_candidates
                if net.prefixlen <= 24
            )
        )
        v6_generator = itertools.chain.from_iterable(
            (
                net.subnets(new_prefix=64)
                for net in v6_candidates
                if net.prefixlen <= 64
            )
        )

        print(v4_generator)
        print(v6_generator)

        for network, v4, v6 in zip(
            unconfigured_networks, v4_generator, v6_generator
        ):
            network.network = [v4, v6]

        self._lower_networks(unconfigured_networks)

    def _lower_networks(self, network_configs: List[ShmemConfigNet]):
        for config in network_configs:
            if isinstance(config.network, list):
                new_networks = {}
                for num, peer in enumerate(config.peers):
                    interfaces = []
                    for network in config.network:
                        address = next(itertools.islice(network, num, None))
                        interface = ip_interface(
                            f"{address}/{network.prefixlen}"
                        )
                        interfaces.append(interface)
                    new_networks[peer] = InterfaceConfig(addresses=interfaces)
                config.network = new_networks
