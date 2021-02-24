import itertools
from collections import defaultdict
from ipaddress import (
    IPv4Interface,
    IPv4Network,
    IPv6Network,
    ip_interface,
    ip_network,
)
from logging import getLogger
from pathlib import Path
from typing import Any, Dict, List, Tuple

from autojail.model.config import AutojailConfig

from ..model import Board, JailhouseConfig, ShmemConfigNet
from ..model.jailhouse import InterfaceConfig
from .passes import BasePass


class NetworkConfigPass(BasePass):
    def __init__(self, config: AutojailConfig):
        self.logger = getLogger()
        self.autojail_config = config

    def __call__(
        self, board: Board, config: JailhouseConfig
    ) -> Tuple[Board, JailhouseConfig]:
        """Generate network configuration for all cells

        Args:
            board (Board): Parsed board info file
            config (JailhouseConfig): Parsed Jailhouse configuration

        Returns:
            Tuple[Board, JailhouseConfig]: Modified Board and Jailhouse configuration after autoconfiguration and lowering
        """

        root_cell_id = ""
        for cell_id, cell in config.cells.items():
            if cell.type == "root":
                root_cell_id = cell_id

        if config.shmem:

            link_configs: List[ShmemConfigNet] = []
            for _cell_name, link in config.shmem.items():
                if not isinstance(link, ShmemConfigNet):
                    continue

                link_configs.append(link)

            self._lower_networks(link_configs)
            self._autoconf_networks(link_configs, board.ip_info)
            self._generate_interface_names(
                link_configs, board.ip_info, root_cell_id
            )
            interface_configs = self._generate_interfaces(link_configs)

            self._write_interface_file(interface_configs, config)

        return board, config

    def _write_interface_file(self, interface_configs, config):
        deploy_path = Path(self.autojail_config.deploy_dir)
        build_path = Path(self.autojail_config.build_dir)

        for cell_id, interface_d in interface_configs.items():
            cell = config.cells[cell_id]
            if cell.type == "root":
                interfaces_path = (
                    deploy_path / "etc" / "network" / "interfaces.d"
                )
            else:
                cell_name = cell.name.lower().replace(" ", "-")
                interfaces_path = (
                    build_path
                    / "rootfs"
                    / cell_name
                    / "etc"
                    / "network"
                    / "interfaces.d"
                )
            interfaces_path.mkdir(exist_ok=True, parents=True)

            output_path = interfaces_path / "jailhouse"
            with output_path.open("w") as output_file:
                output_file.write(interface_d)

    def _generate_interface_names(
        self,
        network_configs: List[ShmemConfigNet],
        ip_info: List[Dict[str, Any]],
        root_cell_id: str,
    ):
        interfaces = defaultdict(list)

        if root_cell_id:
            for interface_info in ip_info:
                interfaces[root_cell_id].append(interface_info["ifname"])

        for config in network_configs:
            assert isinstance(config.network, dict)
            for cell_id, _network in config.network.items():
                num = 0
                ifname = f"eth{num}"
                while ifname in interfaces[cell_id]:
                    num += 1
                    ifname = f"eth{num}"
                config.network[cell_id].interface = ifname
                interfaces[cell_id].append(ifname)

    def _generate_interfaces(
        self, network_configs: List[ShmemConfigNet],
    ) -> Dict[str, str]:
        """Generate network configs in /etc/network/interfaces format.

        Args:
            network_configs (List[ShmemConfigNet]): List of network configs to generate the configuration for

        Returns:
            Dict[str, str]: Mapping from cell id to network configuration
        """

        configs: Dict[str, str] = defaultdict(str)
        for shmem_config in network_configs:
            assert isinstance(shmem_config.network, dict)
            for cell_id, interface_config in shmem_config.network.items():
                ifname = interface_config.interface
                config = ""
                config += f"auto {ifname}\n"
                config += f"allow-hotplug {ifname}\n"
                config += "\n"
                for address in interface_config.addresses:
                    protocol = (
                        "inet"
                        if isinstance(address, IPv4Interface)
                        else "inet6"
                    )
                    config += f"iface {ifname} {protocol} static\n"
                    config += f"    address {address}\n\n"

                configs[cell_id] += config
        return configs

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
                        network = ip_network(address, strict=False)
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
                        address = next(itertools.islice(network, num + 1, None))
                        interface = ip_interface(
                            f"{address}/{network.prefixlen}"
                        )
                        interfaces.append(interface)
                    new_networks[peer] = InterfaceConfig(addresses=interfaces)
                config.network = new_networks
