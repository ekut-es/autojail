import os
from typing import List, Optional

import ruamel.yaml

from ..model import (
    Board,
    DebugConsole,
    JailhouseConfig,
    MemoryRegion,
    PlatformInfoArm,
    ShMemNetRegion,
)
from .board_info import TransferBoardInfoPass
from .devices import LowerDevicesPass
from .irq import PrepareIRQChipsPass
from .memory import AllocateMemoryPass, PrepareMemoryRegionsPass
from .shmem import ConfigSHMemRegionsPass, LowerSHMemPass  # type: ignore


class JailhouseConfigurator:
    def __init__(self, board: Board) -> None:
        self.board = board
        self.config: Optional[JailhouseConfig] = None
        self.passes = [
            TransferBoardInfoPass(),
            LowerDevicesPass(),
            LowerSHMemPass(),
            PrepareIRQChipsPass(),
            PrepareMemoryRegionsPass(),
            AllocateMemoryPass(),
            ConfigSHMemRegionsPass(),
        ]

    def write_config(self, output_path: str) -> None:
        """Write configuration data to file"""
        assert self.config is not None

        for cell in self.config.cells.values():

            assert cell.pci_devices is not None
            assert cell.memory_regions is not None
            assert cell.irqchips is not None
            assert cell.cpus is not None

            output_name = str(cell.name).lower().replace(" ", "-")
            output_name += ".c"

            print("Writing cell config", output_name)

            output_file = os.path.join(output_path, output_name)

            f = open(output_file, "w+")
            amount_pci_devices = len(cell.pci_devices)
            amount_memory_regions = len(cell.memory_regions)
            amount_irqchips = len(cell.irqchips)
            cpu_set = cell.cpus

            cpu_calculated = max(list(cpu_set)) // 64 + 1

            f.write("#include <jailhouse/types.h>\n")
            f.write("#include <jailhouse/cell-config.h>\n")

            f.write("struct { \n")

            if cell.type == "root":
                f.write("\tstruct jailhouse_system header; \n")
            else:
                f.write("\tstruct jailhouse_cell_desc cell; \n")

            f.write("\t__u64 cpus[" + str(cpu_calculated) + "];\n")
            f.write(
                "\tstruct jailhouse_memory mem_regions["
                + str(amount_memory_regions)
                + "];\n"
            )
            f.write(
                f"\tstruct jailhouse_irqchip irqchips[{amount_irqchips}];\n"
            )
            f.write(
                "\tstruct jailhouse_pci_device pci_devices["
                + str(amount_pci_devices)
                + "];\n"
            )
            # f.write("\tstruct jailhouse_pci_capability pci_caps[39];\n")  # TODO:
            f.write("} __attribute__((packed)) config = {\n")

            prefix = ""
            if cell.type == "root":
                f.write("\n.header = {")
                f.write("\n\t.signature = JAILHOUSE_SYSTEM_SIGNATURE,")
                prefix = "JAILHOUSE"
            else:
                f.write("\n.cell = {")
                f.write("\n\t.signature = JAILHOUSE_CELL_DESC_SIGNATURE,")
                prefix = "JAILHOUSE_CELL"

            f.write("\n\t.revision = JAILHOUSE_CONFIG_REVISION,")

            cell_flags = " | ".join(
                list(map(lambda x: f"{prefix}_{x}", cell.flags))
            )
            f.write(f"\n\t.flags = {cell_flags},")

            if cell.type == "root":
                assert cell.hypervisor_memory is not None
                assert cell.hypervisor_memory.physical_start_addr is not None

                f.write("\n\t.hypervisor_memory = {")
                f.write(
                    "\n\t\t.phys_start = "
                    + hex(cell.hypervisor_memory.physical_start_addr)
                    + ","
                )
                f.write(
                    "\n\t\t.size = " + hex(cell.hypervisor_memory.size) + ","
                )
                f.write("\n\t},\n")

            if cell.type == "root":
                f.write("\n\t.debug_console = {")
            else:
                f.write("\n\t.console = {")

            assert isinstance(cell.debug_console, DebugConsole)

            f.write("\n\t\t.address = " + hex(cell.debug_console.address) + ",")
            f.write("\n\t\t.size = " + hex(cell.debug_console.size) + ",")
            f.write(
                "\n\t\t.type = " + "JAILHOUSE_" + cell.debug_console.type + ","
            )
            s = " | "
            jailhouse_flags = [
                "JAILHOUSE_" + flag for flag in cell.debug_console.flags
            ]
            f.write("\n\t\t.flags = " + str(s.join(jailhouse_flags)) + ",")
            f.write("\n\t},\n")

            if cell.type == "root":
                assert cell.platform_info is not None
                f.write("\n\t.platform_info = {")
                if cell.platform_info.pci_mmconfig_base:
                    f.write(
                        "\n\t\t.pci_mmconfig_base = "
                        + hex(cell.platform_info.pci_mmconfig_base)
                        + ","
                    )
                f.write(
                    "\n\t\t.pci_mmconfig_end_bus = "
                    + str(cell.platform_info.pci_mmconfig_end_bus)
                    + ","
                )
                f.write(
                    "\n\t\t.pci_is_virtual = "
                    + ("1" if cell.platform_info.pci_is_virtual else "0")
                    + ","
                )
                f.write(
                    "\n\t\t.pci_domain = "
                    + str(cell.platform_info.pci_domain)
                    + ","
                )
                f.write("\n\t\t.arm = {")
                arm_values = cell.platform_info.arch

                assert isinstance(arm_values, PlatformInfoArm)
                assert arm_values is not None

                for name, val in arm_values.dict().items():
                    if name == "iommu_units":
                        continue
                    if "_base" in name:
                        val = hex(val)
                    else:
                        val = str(val)

                    f.write("\n\t\t\t." + str(name) + " = " + val + ",")

                f.write("\n\t\t},\n")
                f.write("\n\t},\n")

            cell_type_temp = cell.type
            if cell_type_temp == "root":
                f.write("\n\t.root_cell = {")

            f.write("\n\t\t.name =" + ' "' + cell.name + '" ' + ",")
            f.write("\n\t\t.vpci_irq_base = " + str(cell.vpci_irq_base) + ",")
            f.write(
                "\n\t\t.num_memory_regions = ARRAY_SIZE(config.mem_regions)"
                + ","
            )
            f.write(
                "\n\t\t.num_pci_devices = ARRAY_SIZE(config.pci_devices)" + ","
            )
            f.write(
                "\n\t\t.cpu_set_size = sizeof(config.cpus)" + ","
            )  # lookatthis later
            f.write("\n\t\t.num_irqchips = ARRAY_SIZE(config.irqchips)" + ",")
            # f.write("\n\t\t//.num_pci_caps !!//TODO: = " + ",")

            if cell.type == "root":
                f.write("\n\t},")

            f.write("\n\t},")

            f.write("\n\t.cpus = {")
            cpu_set_tmp = "0b" + "0" * (max(cpu_set) + 1)
            cpu_list: List[str] = list(cpu_set_tmp)
            for e in cpu_set:
                cpu_list[(max(cpu_set) + 2) - e] = str(1)
            cpu_res = "".join(cpu_list)
            f.write(cpu_res + "},")
            f.write("\n\t")
            f.write("\n\t.mem_regions = {\n")
            for k, v in cell.memory_regions.items():
                assert isinstance(v, MemoryRegion) or isinstance(
                    v, ShMemNetRegion
                )
                if v.size == 0:
                    f.write("\t/* empty optional region */\n\t{ 0 },\n")
                    continue

                if isinstance(v, MemoryRegion):
                    assert v.virtual_start_addr is not None
                    assert v.physical_start_addr is not None
                    assert v.size is not None

                    f.write("\t/*" + k)

                    f.write(
                        " "
                        + hex(v.physical_start_addr)
                        + "-"
                        + hex(v.physical_start_addr + v.size)
                    )

                    f.write("*/\n\t{")

                    f.write(
                        "\n\t\t.phys_start = "
                        + hex(v.physical_start_addr)
                        + ","
                    )

                    f.write(
                        "\n\t\t.virt_start = " + hex(v.virtual_start_addr) + ","
                    )
                    tmp_size = hex(v.size)

                    f.write("\n\t\t.size = " + tmp_size + ",")
                    s = "|"
                    jailhouse_flags = [
                        f"JAILHOUSE_{flag}" if "JAILHOUSE" not in flag else flag
                        for flag in v.flags
                    ]
                    f.write(
                        "\n\t\t.flags = " + str(s.join(jailhouse_flags)) + ","
                    )
                    f.write("\n\t},\n")
                elif isinstance(v, ShMemNetRegion):
                    f.write(
                        f"JAILHOUSE_SHMEM_NET_REGIONS({v.start_addr}, {v.device_id}),"
                    )

            f.write("\t},")
            f.write("\n\t.irqchips = {")
            for chip in cell.irqchips.values():
                f.write("\n\t\t{")
                f.write("\n\t\t\t.address = " + hex(chip.address) + ",")
                f.write("\n\t\t\t.pin_base = " + str(chip.pin_base) + ",")

                bitmap_temp = ", ".join(
                    ["\n\t\t\t\t%s" % b for b in chip.pin_bitmap]
                )
                bitmap_temp = bitmap_temp + "\n\t\t\t" + "},"

                f.write("\n\t\t\t.pin_bitmap = {" + bitmap_temp)
                f.write("\n\t\t},")
            f.write("\n\t},\n")

            f.write("\n\t.pci_devices = {")
            for name, device in cell.pci_devices.items():
                f.write("\n\t\t/*" + name + "*/")
                f.write("\n\t\t{")

                f.write(f"\n\t\t\t.type = JAILHOUSE_{device.type},")
                f.write(f"\n\t\t\t.domain = {device.domain},")
                f.write(f"\n\t\t\t.bar_mask = JAILHOUSE_{device.bar_mask},")
                f.write(f"\n\t\t\t.bdf = {device.bdf} << 3,")

                if device.shmem_regions_start is not None:
                    f.write(
                        f"\n\t\t\t.shmem_regions_start = {device.shmem_regions_start},"
                    )
                if device.shmem_dev_id is not None:
                    f.write(f"\n\t\t\t.shmem_dev_id = {device.shmem_dev_id},")
                if device.shmem_peers is not None:
                    f.write(f"\n\t\t\t.shmem_peers = {device.shmem_peers},")
                if device.shmem_protocol is not None:
                    f.write(
                        f"\n\t\t\t.shmem_protocol = JAILHOUSE_{device.shmem_protocol},"
                    )

                f.write("\n\t\t},")
            f.write("\n\t},\n")
            f.write("\n};")

    def prepare(self) -> None:
        if self.config is None:
            raise Exception(
                "A configuration without cells_yml is not supported at the moment"
            )

        for pass_instance in self.passes:
            pass_instance(self.board, self.config)

    def read_cell_yml(self, cells_yml: str) -> None:
        print("Reading cell configuration", str(cells_yml))
        with open(cells_yml, "r") as stream:
            yaml = ruamel.yaml.YAML()
            yaml_info = yaml.load(stream)
            config = JailhouseConfig(**yaml_info)
            self.config = config
