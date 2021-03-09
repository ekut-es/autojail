import os
import re
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
from ..model.parameters import GenerateConfig, GenerateParameters
from ..utils.report import Report, Section, Table
from ..utils.save_config import save_jailhouse_config
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
from .network import NetworkConfigPass
from .root_shared import InferRootSharedPass
from .shmem import ConfigSHMemRegionsPass, LowerSHMemPass  # type: ignore
from .startup import GenerateStartupPass


class JailhouseConfigurator:
    def __init__(
        self,
        board: Board,
        autojail_config: AutojailConfig,
        print_after_all: bool = False,
        context=None,
        set_params: Optional[GenerateConfig] = None,
        gen_params: Optional[GenerateParameters] = None,
    ) -> None:
        self.board = board
        self.autojail_config = autojail_config
        self.print_after_all = print_after_all
        self.config: Optional[JailhouseConfig] = None
        self.context = context
        self.set_params: Optional[GenerateConfig] = set_params
        self.gen_params: Optional[GenerateParameters] = gen_params

        self.passes = [
            TransferBoardInfoPass(),
            LowerDevicesPass(),
            LowerSHMemPass(),
            PrepareIRQChipsPass(),
            PrepareMemoryRegionsPass(),
            MergeIoRegionsPass(self.set_params, self.gen_params),
            AllocateMemoryPass(),
            CPUAllocatorPass(self.set_params, self.gen_params),
            ConfigSHMemRegionsPass(),
            InferRootSharedPass(),
            GenerateDeviceTreePass(self.autojail_config),
            NetworkConfigPass(self.autojail_config),
            GenerateStartupPass(self.autojail_config),
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
            return 0

        if not shutil.which(objcopy):
            self.logger.critical(
                f"Could not find {objcopy} so no binary cell file will be generated"
            )
            return 0

        jailhouse_dir = self.autojail_config.jailhouse_dir

        syscfg = None
        cellcfgs: List[str] = []

        for cell in self.config.cells.values():
            output_name = str(cell.name).lower().replace(" ", "-")
            c_name = output_name + ".c"
            object_name = output_name + ".o"
            cell_name = output_name + ".cell"

            if cell.type == "root":
                syscfg = os.path.join(output_path, cell_name)
            else:
                cellcfgs.append(os.path.join(output_path, cell_name))

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

        if ret:
            self.logger.critical(
                "Found critical errors in generated jailhouse config"
            )

        return ret

    def deploy(
        self,
        output_path: Union[str, Path],
        deploy_path: Union[str, Path],
        target: bool = False,
    ) -> int:
        """
        Install to deploy_path/prefix and build a file deploy.tar.gz for installation on the target system

        Parameters:
            output_path (Union[str, Path]): Path to generated builds 
            deploy_path (Union[str, Path]): Path to install the generated rootfs overlay
            target (bool): If true copy to target board and extract deploy tarball

        Returns: 
            int: 0 on success 1 on error 
        """
        assert self.autojail_config is not None
        assert self.config is not None

        output_path = Path(output_path)
        deploy_path = Path(deploy_path)

        kernel_path = Path(self.autojail_config.kernel_dir)
        if not kernel_path.exists():
            self.logger.info("Skipping deploy: kernel directory missing")
            return 0

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
            f"KDIR={kernel_path.absolute()}",
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

        prefix = Path(self.autojail_config.prefix)
        assert prefix.is_absolute()
        jailhouse_path = Path(self.autojail_config.jailhouse_dir)
        deploy_path_prefix = (
            deploy_path.absolute() / self.autojail_config.prefix[1:]
        )
        pyjailhouse_path = (
            deploy_path_prefix / "share" / "jailhouse" / "pyjailhouse"
        )
        pyjailhouse_path.parent.mkdir(exist_ok=True, parents=True)
        if pyjailhouse_path.exists():
            shutil.rmtree(pyjailhouse_path)
        shutil.copytree(
            jailhouse_path / "pyjailhouse",
            pyjailhouse_path,
            ignore=lambda path, names: ["__pycache__"],
        )

        jailhouse_tools = [
            (
                "jailhouse-cell-linux",
                lambda x: x.replace(
                    "libexecdir = None",
                    f"libexecdir = \"{str(prefix / 'libexec')}\"",
                ),
            ),
            ("jailhouse-cell-stats", None),
        ]

        for tool, fixup in jailhouse_tools:
            tool_path = jailhouse_path / "tools" / tool
            tool_deploy_path = deploy_path_prefix / "sbin" / tool
            with tool_path.open() as tool_file:
                with tool_deploy_path.open("w") as tool_deploy_file:
                    for line in tool_file.readlines():
                        if fixup:
                            line = fixup(line)

                        line = re.sub(
                            r"^sys.path\[0\] = .*",
                            f'sys.path[0] = "{prefix / "share" / "jailhouse"}"',
                            line,
                        )
                        tool_deploy_file.write(line)
                os.chmod(tool_deploy_path, 0o755)

        # deploy dtbs
        if (
            Path(self.autojail_config.deploy_dir) / "etc" / "jailhouse" / "dts"
        ).exists():
            shutil.rmtree(
                Path(self.autojail_config.deploy_dir)
                / "etc"
                / "jailhouse"
                / "dts"
            )

        shutil.copytree(
            Path(self.autojail_config.build_dir) / "dts",
            Path(self.autojail_config.deploy_dir) / "etc" / "jailhouse" / "dts",
            ignore=lambda path, names: [
                name for name in names if not name.endswith(".dtb")
            ],
        )

        # Create deploy bundle
        deploy_files = os.listdir(deploy_path)
        deploy_bundle_command = [
            "tar",
            "czf",
            "deploy.tar.gz",
            "-C",
            f"{deploy_path}",
        ] + deploy_files

        self.logger.debug(" ".join(deploy_bundle_command))
        subprocess.run(deploy_bundle_command, check=True)

        if target:
            utils.start_board(self.autojail_config)
            connection = utils.connect(self.autojail_config, self.context)
            utils.deploy_target(connection, Path("deploy.tar.gz"))
            utils.stop_board(self.autojail_config)

        return 0

    def write_config(self, output_path: str) -> int:
        """Write configuration data to file

        Parameters:
            output_path (str): Path to output path

        Returns:
            int: nonzero value on error 
        """
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

            def mem_region_size(region):
                if isinstance(region, GroupedMemoryRegion):
                    return len(region.regions)
                elif isinstance(region, ShMemNetRegion):
                    return 4
                else:
                    return 1

            f = open(output_file, "w+")
            amount_pci_devices = len(cell.pci_devices)
            amount_memory_regions = sum(
                map(mem_region_size, cell.memory_regions.values(),)
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
            print(cell.flags)
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
            f.write("\n\t\t.cpu_set_size = sizeof(config.cpus)" + ",")
            f.write("\n\t\t.num_irqchips = ARRAY_SIZE(config.irqchips)" + ",")

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
            self.board, self.config = pass_instance(self.board, self.config)
            if self.print_after_all:
                print(f"Config after {pass_instance.name}")
                from devtools import debug

                debug(self.config)

            report_path = Path(self.autojail_config.build_dir) / "report"
            report_path.mkdir(exist_ok=True, parents=True)
            generated_cells_yml = report_path / "generated_cells.yml"
            save_jailhouse_config(generated_cells_yml, self.config)

    def read_cell_yml(self, cells_yml: str) -> None:
        self.logger.info("Reading cell configuration %s", str(cells_yml))
        with open(cells_yml, "r") as stream:
            yaml = ruamel.yaml.YAML()
            yaml_info = yaml.load(stream)
            config = JailhouseConfig(**yaml_info)
            self.config = config

    def report(self, show=True):
        self.logger.info("Generating reports")

        report = Report("Jailhouse Config")

        for cell_id, cell in self.config.cells.items():
            cell_section = Section(cell.name)
            report.add(cell_section)
            cell_info_table = Table(headers=["Attribute", "Value"])
            cell_info_table.content.append(["ID", cell_id])
            cell_info_table.content.append(["Type", cell.type])
            cell_info_table.content.append(["Flags", " | ".join(cell.flags)])
            cell_info_table.append(
                ["CPUs", ", ".join((str(c) for c in cell.cpus))]
            )
            cell_section.add(cell_info_table)

            if cell.pci_devices:
                shmem_section = Section("Virtual PCI Devices")
                report.add(shmem_section)
                pci_table = Table(
                    [
                        "Name",
                        "Domain",
                        "BDF",
                        "Interrupt",
                        "Protocol",
                        "Virtual Memory",
                        "Physical Memory",
                    ]
                )
                shmem_section.add(pci_table)
                pci_device_count = 0
                for shmem_device_name, shmem_device in cell.pci_devices.items():
                    if shmem_device_name not in cell.memory_regions:
                        continue
                    device_memory_region = cell.memory_regions[
                        shmem_device_name
                    ]
                    pci_table.append(
                        [
                            shmem_device_name,
                            str(shmem_device.domain),
                            f"{shmem_device.bus}:{shmem_device.device}.{shmem_device.function}",
                            str(cell.vpci_irq_base + pci_device_count),
                            shmem_device.shmem_protocol,
                            hex(device_memory_region.virtual_start_addr),
                            hex(device_memory_region.physical_start_addr),
                        ]
                    )
                    pci_device_count += 1

            if self.config.shmem:
                network_section = Section("Network Configuration")
                report.add(network_section)
                network_interface_table = Table(
                    ["Name", "Interface", "Address"]
                )

                for shmem_device_name, shmem_device in cell.pci_devices.items():
                    if shmem_device.shmem_protocol != "SHMEM_PROTO_VETH":
                        continue

                    interface_name = "unknown"
                    addresses = ["unknown"]
                    if shmem_device_name in self.config.shmem:
                        if not hasattr(
                            self.config.shmem[shmem_device_name], "network"
                        ):
                            continue
                        if (
                            cell_id
                            in self.config.shmem[shmem_device_name].network
                        ):
                            shmem_addresses = (
                                self.config.shmem[shmem_device_name]
                                .network[cell_id]
                                .addresses
                            )

                            addresses = (
                                shmem_addresses
                                if shmem_addresses
                                else addresses
                            )

                            network_interface_name = (
                                self.config.shmem[shmem_device_name]
                                .network[cell_id]
                                .interface
                            )

                            interface_name = (
                                network_interface_name
                                if network_interface_name
                                else interface_name
                            )

                    for address in addresses:
                        network_interface_table.append(
                            [shmem_device_name, interface_name, str(address)]
                        )

                if network_interface_table.content:
                    report.add(network_interface_table)
                else:
                    report.add("No network interfaces configured")

            memory_section = Section("Memory Map")
            report.add(memory_section)

            memory_table = Table(
                headers=["Name", "Virtual", "Phys", "Size", "Flags"]
            )
            for region_name, region in sorted(
                cell.memory_regions.items(),
                key=lambda x: x[1].virtual_start_addr,
            ):
                region_size = (
                    region.size.human_readable()
                    if hasattr(region.size, "human_readable")
                    else region.size
                )
                memory_table.append(
                    [
                        region_name,
                        hex(region.virtual_start_addr),
                        hex(region.physical_start_addr),
                        str(region_size),
                        " | ".join(region.flags),
                    ]
                )
            memory_section.add(memory_table)

        # Save report
        build_path = Path(self.autojail_config.build_dir) / "report"
        build_path.mkdir(parents=True, exist_ok=True)

        report_path = build_path / "generate.md"
        with report_path.open("w") as report_file:
            report_file.write(str(report))

        # Render to console
        if show:
            from rich.console import Console

            console = Console()
            console.print(report)
