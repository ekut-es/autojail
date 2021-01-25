import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Union

import ruamel.yaml

from .. import utils
from ..model import (
    AutojailConfig,
    Board,
    DebugConsole,
    GroupedMemoryRegion,
    JailhouseConfig,
    MemoryRegionData,
    PlatformInfoArm,
    ShMemNetRegion,
)
from .board_info import TransferBoardInfoPass
from .cpu import CPUAllocatorPass
from .devices import LowerDevicesPass
from .devicetree import GenerateDeviceTreePass
from .irq import PrepareIRQChipsPass
from .memory import (
    AllocateMemoryPass,
    MergeIoRegionsPass,
    PrepareMemoryRegionsPass,
)
from .root_shared import InferRootSharedPass
from .shmem import ConfigSHMemRegionsPass, LowerSHMemPass  # type: ignore


class JailhouseConfigurator:
    def __init__(
        self,
        board: Board,
        autojail_config: AutojailConfig,
        print_after_all: bool = False,
    ) -> None:
        self.board = board
        self.autojail_config = autojail_config
        self.print_after_all = print_after_all
        self.config: Optional[JailhouseConfig] = None
        self.passes = [
            TransferBoardInfoPass(),
            LowerDevicesPass(),
            LowerSHMemPass(),
            PrepareIRQChipsPass(),
            PrepareMemoryRegionsPass(),
            MergeIoRegionsPass(),
            AllocateMemoryPass(),
            CPUAllocatorPass(),
            ConfigSHMemRegionsPass(),
            InferRootSharedPass(),
            GenerateDeviceTreePass(),
        ]

        self.logger = utils.logging.getLogger()

    def build_config(self, output_path: str, skip_check: bool = False) -> int:
        assert self.config is not None
        assert self.autojail_config is not None

        cc = self.autojail_config.cross_compile + "gcc"
        objcopy = self.autojail_config.cross_compile + "objcopy"

        if not shutil.which(cc):
            self.logger.critical(
                f"Could not find {cc} so no binary .cell file will be generated"
            )
            return 1

        if not shutil.which(objcopy):
            self.logger.critical(
                f"Could not find {objcopy} so no binary cell file will be generated"
            )
            return 1

        jailhouse_dir = self.autojail_config.jailhouse_dir

        syscfg = None
        cellcfgs: List[str] = []

        for cell in self.config.cells.values():
            output_name = str(cell.name).lower().replace(" ", "-")
            c_name = output_name + ".c"
            object_name = output_name + ".o"
            cell_name = output_name + ".cell"

            if cell.type == "root":
                syscfg = cell_name
            else:
                cellcfgs.append(cell_name)

            c_file = os.path.join(output_path, c_name)
            object_file = os.path.join(output_path, object_name)
            cell_file = os.path.join(output_path, cell_name)

            # -isystem /usr/lib/gcc-cross/aarch64-linux-gnu/9/include
            # f"-include {jailhouse_dir}/include/linux/compiler_types.h",
            compile_command = [
                f"{cc}",
                "-nostdinc",
                f"-I{jailhouse_dir}/hypervisor/arch/arm64/include",
                f"-I{jailhouse_dir}/hypervisor/include",
                f"-I{jailhouse_dir}/include",
                "-D__KERNEL",
                "-mlittle-endian",
                "-DKASAN_SHADOW_SCALE_SHIFT=3",
                "-Werror",
                "-Wall",
                "-Wextra",
                "-D__LINUX_COMPILER_TYPES_H",
                "-c",
                "-o",
                f"{object_file}",
                f"{c_file}",
            ]
            subprocess.run(compile_command, check=True)

            objcopy_command = [
                f"{objcopy}",
                "-O",
                "binary",
                "--remove-section=.note.gnu.property",
                f"{object_file}",
                f"{cell_file}",
            ]
            subprocess.run(objcopy_command, check=True)

        # Run jailhouse config check on generated cells
        if syscfg is None:
            self.logger.critical("No root cell configuration generated")
            return 1

        if skip_check:
            return 0

        ret = 0
        try:
            sys.path = [str(jailhouse_dir)] + sys.path
            import pyjailhouse.check as check

            arch = self.autojail_config.arch.lower()
            syscfg_file = open(syscfg, "rb")
            cellcfg_files = [open(f, "rb") for f in cellcfgs]

            ret = check.run_checks(
                arch=arch, syscfg=syscfg_file, cellcfgs=cellcfg_files
            )
        except ModuleNotFoundError:
            self.logger.warning("Could not import jailhouse config checker")
            self.logger.warning("Trying command line tool instead")

            config_check_command = (
                [
                    f"{self.autojail_config.jailhouse_dir}/tools/jailhouse-config-check"
                ]
                + [f"--arch={self.autojail_config.arch.lower()}"]
                + [syscfg]
                + cellcfgs
            )
            return_val = subprocess.run(config_check_command)
            ret = return_val.returncode

        if ret != 0:
            self.logger.critical(
                "Found critical errors in generated jailhouse config"
            )

        return ret

    def deploy(
        self, output_path: Union[str, Path], deploy_path: Union[str, Path]
    ):
        "Install to deploy_path/prefix and build a file deploy.tar.gz for installation on the target system"
        assert self.autojail_config is not None
        assert self.config is not None

        output_path = Path(output_path)
        deploy_path = Path(deploy_path)

        jailhouse_config_dir = deploy_path / "etc" / "jailhouse"
        jailhouse_config_dir.mkdir(exist_ok=True, parents=True)

        for cell in self.config.cells.values():
            output_name = str(cell.name).lower().replace(" ", "-") + ".cell"
            cell_file = output_path / output_name

            if not cell_file.exists():
                self.logger.warning("%s does not exist", str(cell_file))
            else:
                shutil.copy(cell_file, jailhouse_config_dir / output_name)

        jailhouse_install_command = [
            "make",
            "install",
            f"ARCH={self.autojail_config.arch.lower()}",
            f"CROSS_COMPILE={self.autojail_config.cross_compile}",
            f"KDIR={Path(self.autojail_config.kernel_dir).absolute()}",
            f"DESTDIR={deploy_path.absolute()}",
            f"prefix={self.autojail_config.prefix}",
            "PYTHON_PIP_USABLE=no",
        ]
        print(" ".join(jailhouse_install_command))
        return_val = subprocess.run(
            jailhouse_install_command, cwd=self.autojail_config.jailhouse_dir
        )
        if return_val.returncode:
            return return_val.returncode

        jailhouse_sdist_command = [
            "python",
            "setup.py",
            "sdist",
            "-d",
            f"{deploy_path.absolute()}",
        ]
        return_val = subprocess.run(
            jailhouse_sdist_command, cwd=self.autojail_config.jailhouse_dir
        )
        if return_val.returncode:
            return return_val.returncode

    def write_config(self, output_path: str) -> int:
        """Write configuration data to file"""
        assert self.config is not None

        for cell in self.config.cells.values():

            assert cell.pci_devices is not None
            assert cell.memory_regions is not None
            assert cell.irqchips is not None
            assert cell.cpus is not None

            output_name = str(cell.name).lower().replace(" ", "-")
            output_name += ".c"

            output_file = os.path.join(output_path, output_name)

            self.logger.info("Writing cell config %s", output_name)

            f = open(output_file, "w+")
            amount_pci_devices = len(cell.pci_devices)
            amount_memory_regions = sum(
                map(
                    lambda r: len(r.regions)
                    if isinstance(r, GroupedMemoryRegion)
                    else 1,
                    cell.memory_regions.values(),
                )
            )
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

            if cell.flags:
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
            vpci_irq_base = cell.vpci_irq_base
            if vpci_irq_base is not None:
                f.write(
                    "\n\t\t.vpci_irq_base = "
                    + str(vpci_irq_base)
                    + "- 32"
                    + ","
                )

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
                assert isinstance(v, MemoryRegionData) or isinstance(
                    v, ShMemNetRegion
                )

                def write_mem_region(v):
                    if v.size == 0:
                        f.write("\t/* empty optional region */\n\t{ 0 },\n")
                        return

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

                if isinstance(v, GroupedMemoryRegion):
                    for region in v.regions:
                        write_mem_region(region)
                elif isinstance(v, MemoryRegionData):
                    write_mem_region(v)
                elif isinstance(v, ShMemNetRegion):
                    f.write(f"\t/* {k} */\n")
                    f.write(
                        f"\tJAILHOUSE_SHMEM_NET_REGIONS(0x{v.start_addr:x}, {v.device_id}),\n"
                    )

            f.write("\t},")
            f.write("\n\t.irqchips = {")
            for chip in cell.irqchips.values():
                f.write("\n\t\t{")
                f.write("\n\t\t\t.address = " + hex(chip.address) + ",")
                f.write("\n\t\t\t.pin_base = " + str(chip.pin_base) + ",")

                # print(chip.pin_bitmap)

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
                f.write(
                    f"\n\t\t\t.bdf = {device.bus} << 8 | {device.device} << 3 | {device.function},"
                )

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

        return 0

    def prepare(self) -> None:
        if self.config is None:
            raise Exception(
                "A configuration without cells_yml is not supported at the moment"
            )

        for pass_instance in self.passes:
            pass_instance(self.board, self.config)
            if self.print_after_all:
                print(json.dumps(self.config.dict(), indent=2))
                print(json.dumps(self.board.dict(), indent=2))

    def read_cell_yml(self, cells_yml: str) -> None:
        self.logger.info("Reading cell configuration %s", str(cells_yml))
        with open(cells_yml, "r") as stream:
            yaml = ruamel.yaml.YAML()
            yaml_info = yaml.load(stream)
            config = JailhouseConfig(**yaml_info)
            self.config = config
