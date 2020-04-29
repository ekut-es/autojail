import os

from typing import Optional
from pathlib import Path

import ruamel.yaml
import copy

from ..model import (
    Board,
    MemoryRegion,
    ShMemNetRegion,
    JailhouseConfig,
    IRQChip,
    PCIDevice
)


class BoardInfoExtractor:
    def __init__(self, name, board, data_root):
        self.name = name
        self.board = board
        self.data_root = Path(data_root)

    def read_iomem(self, filename):
        with open(filename, "r") as iomem_info:
            start_addr = 0
            end_addr = 0
            size_calculated = 0
            temp = 0
            compare_count = 2
            physical_start_addr = []

            size = []
            memory_regions = []
            res = 1
            res2 = 1
            mem_flags = "JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64"
            ram_flags = "JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_EXECUTE"
            for x in iomem_info:
                start_addr, temp, *rest = x.split("-", 1)
                temp = temp.strip()
                start_addr = start_addr.strip()
                physical_start_addr.append(start_addr)
                end_addr, temp = temp.split(":", 1)

                end_addr = end_addr.split(" ", 1)[0]
                size_calculated = int(end_addr, 16) - int(start_addr, 16) + 1
                size.append(size_calculated)
                temp = temp.strip()
                res = any(temp in sublist for sublist in memory_regions)
                compare_count = 1
                if res == 0:
                    memory_regions.append(temp)
                else:
                    while res != 0:
                        if res != 0:
                            compare_count += 1
                            if (
                                temp[-1].isdigit() == 1
                                or temp[-2].isdigit() == 1
                                and temp[-2] == "_"
                                or temp[-3] == "_"
                            ):
                                temp = temp.rsplit("_", 1)[0]
                                temp = temp.strip() + "_" + str(compare_count)
                            else:
                                temp = temp.strip() + "_" + str(compare_count)
                            res2 = any(
                                temp in sublist for sublist in memory_regions
                            )
                            if res2 == 0:
                                memory_regions.append(temp)

                                res = 0
                            else:
                                res = 1
        mem_regs = {}

        for i, name in enumerate(memory_regions):
            if (
                ("System RAM" in name)
                or ("Kernel Code" in name)
                or ("reserved" in name)
            ):
                flags = (ram_flags,)
            else:
                flags = (mem_flags,)

            allocatable = False
            if "System RAM" in name:
                allocatable = True

            memory_region = MemoryRegion(
                physical_start_addr=int(physical_start_addr[i], 16),
                virtual_start_addr=int(physical_start_addr[i], 16),
                size=size[i],
                flags=flags,
                allocatable=allocatable,
            )
            mem_regs[name] = memory_region

        # FIXME: it would be better to check if some regions are part of an outer region and merge accordingly
        to_delete = []
        for k in mem_regs:
            if k.startswith("reserved") or k.startswith("Kernel"):
                to_delete.append(k)

        for k in to_delete:
            del mem_regs[k]

        return mem_regs

    def read_getconf_out(self, getconf_path: Path):
        # Return values
        pagesize = 4096

        if getconf_path.exists():
            with getconf_path.open() as getconf_data:
                for line in getconf_data.readlines():
                    line = line.strip()
                    splitted_line = line.split()
                    if len(splitted_line) == 2:
                        name, value = splitted_line
                        if name == "PAGESIZE" or name == "PAGE_SIZE":
                            pagesize = int(value)
        return pagesize

    def extract(self):
        memory_regions = self.read_iomem(self.data_root / "proc" / "iomem")
        pagesize = self.read_getconf_out(self.data_root / "getconf.out")

        board = Board(
            name=self.name,
            board=self.board,
            memory_regions=memory_regions,
            pagesize=pagesize,
        )
        return board


class BoardConfigurator:
    def __init__(self, board: Board):
        self.board = board
        self.config: Optional[JailhouseConfig] = None

    def write_config(self, output_path):
        """Write configuration data to file"""

        for cell_id, cell in self.config.cells.items():
            output_name = str(cell.name).lower().replace(" ", "-")
            output_name += ".c"

            print("Writing cell config", output_name)

            output_file = os.path.join(output_path, output_name)

            f = open(output_file, "w+")
            amount_pci_devices = len(cell.pci_devices)
            amount_memory_regions = len(cell.memory_regions)
            amount_irqchips = len(cell.irqchips)
            cpu_set = cell.cpus

            # 64 von rpi4.c  size of datatype __u64
            # FIXME: check if feasible for higher number of cpu sets
            #        should probably be maximum over all cpu sets
            cpu_calculated = max(*cpu_set) // 64 + 1

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
            )  # TODO:
            f.write(
                "\tstruct jailhouse_pci_device pci_devices["
                + str(amount_pci_devices)
                + "];\n"
            )
            # f.write("\tstruct jailhouse_pci_capability pci_caps[39];\n")  # TODO:
            f.write("} __attribute__((packed)) config = {\n")

            if cell.type == "root":
                f.write("\n.header = {")
            else:
                f.write("\n.cell = {")

            f.write("\n\t.signature = JAILHOUSE_SYSTEM_SIGNATURE,")
            f.write("\n\t.revision = JAILHOUSE_CONFIG_REVISION,")
            f.write("\n\t.flags = JAILHOUSE_SYS_VIRTUAL_DEBUG_CONSOLE,")

            if cell.type == "root":
                f.write("\n\t.hypervisor_memory = {")
                f.write(
                    "\n\t\t.phys_start = "
                    + hex(cell.hypervisor_memory.physical_start_addr)
                    + ","
                )
                f.write("\n\t\t.size = " + hex(cell.hypervisor_memory.size) + ",")
                f.write("\n\t},\n")

            f.write("\n\t.debug_console = {")
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
                f.write("\n\t.platform_info = {")
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
                    + str(cell.platform_info.pci_is_virtual)
                    + ","
                )
                f.write(
                    "\n\t\t.pci_domain = "
                    + str(cell.platform_info.pci_domain)
                    + ","
                )
                f.write("\n\t\t.arm = {")
                arm_values = cell.platform_info.arm
                for i in range(len(arm_values)):
                    f.write("\n\t\t\t." + str(arm_values[i]).strip() + ",")
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
            s = list(cpu_set_tmp)
            for e in cpu_set:
                s[(max(cpu_set) + 2) - e] = str(1)
            s = "".join(s)
            f.write(s + "},")
            f.write("\n\t")
            f.write("\n\t.mem_regions = {\n")
            for k, v in cell.memory_regions.items():
                if isinstance(v, MemoryRegion):
                    f.write(
                        "\t/*"
                        + k)

                    if v.physical_start_addr:
                        f.write(" "
                            + hex(v.physical_start_addr)
                            + "-"
                            + hex(v.physical_start_addr + v.size)
                        )

                    f.write("*/\t{")

                    if v.physical_start_addr:
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
                    # jailhouse_flags = ["JAILHOUSE_" + flag for flag in v.flags]
                    jailhouse_flags = [f"JAILHOUSE_{flag}" for flag in v.flags]
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
            for name, chip in cell.irqchips.items():
                f.write("\n\t\t{")
                f.write("\n\t\t\t.address = " + hex(chip.address) + ",")
                hex_bitmap = ", ".join(["0x%x" % b for b in chip.pin_bitmap])
                f.write("\n\t\t\t.pin_base = " + str(chip.pin_base) + ",")
                bitmap_temp = hex_bitmap + "},"
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
                f.write(f"\n\t\t\t.bdf = {device.bdf},")

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

            # TODO:not defined in struct jailhouse_system
            # f.write("\n\t.shmem_net = {")
            # f.write("\n\t\t.start_addr = " + hex(cell.sh_mem_net.start_addr) + ",")
            # dev_id = cell.sh_mem_net.device_id
            # if dev_id == 1:
            #     dev_id_offset = 0x80000
            # else:
            #     dev_id_offset = 0x1000
            # f.write("\n\t\t.device_id = " + hex(dev_id_offset) + ",")
            # # interrupt_set = parseIntSet(cell.irqchips.interrupts)
            # # f.write("\n\t.interrupt_set = " + str(interrupt_set) + ",")
            # f.write("\n\t},\n")

            f.write("\n};")

    def _prepare_irqchips(self, cell):
        "Splits irqchips that handle more interrupts than are possible in one autojail config entry"

        split_factor = 32 * 4  # One entry can handle only  4*32 interrupts
        new_irqchips = {}
        for name, irqchip in cell.irqchips.items():
            count = 0
            new_name = name
            new_chip = IRQChip(
                address=irqchip.address,
                pin_base=irqchip.pin_base,
                interrupts=[],
            )

            current_base = 0
            for irq in irqchip.interrupts:
                while irq >= current_base + split_factor:
                    new_irqchips[new_name] = new_chip

                    current_base += split_factor
                    new_chip = IRQChip(
                        address=irqchip.address,
                        pin_base=irqchip.pin_base + current_base,
                        interrupts=[],
                    )

                    count += 1
                    new_name = name + "_" + str(count)

                new_chip.interrupts.append(irq - current_base)

            new_irqchips[new_name] = new_chip

        cell.irqchips = new_irqchips

    def _prepare_memory_regions(self, cell):
        for name, memory_region in self.board.memory_regions.items():
            p_start = memory_region.physical_start_addr
            v_start = memory_region.virtual_start_addr
            p_end = memory_region.physical_start_addr
            v_end = memory_region.virtual_start_addr

            skip = False
            for cell_name, cell_region in cell.memory_regions.items():
                if not isinstance(cell_region, MemoryRegion):
                    continue

                # TODO correct?
                if cell_region.physical_start_addr:
                    if (
                        p_start >= cell_region.physical_start_addr
                        and p_start
                        < cell_region.physical_start_addr + cell_region.size
                    ):
                        skip = True

                    if (
                        p_end >= cell_region.physical_start_addr
                        and p_end
                        < cell_region.physical_start_addr + cell_region.size
                    ):
                        skip = True

                if cell_region.virtual_start_addr:
                    if (
                        v_start >= cell_region.virtual_start_addr
                        and v_start
                        < cell_region.virtual_start_addr + cell_region.size
                    ):
                        skip = True

                    if (
                        v_end >= cell_region.virtual_start_addr
                        and v_end
                        < cell_region.virtual_start_addr + cell_region.size
                    ):
                        skip = True

            if skip is True:
                continue

            cell.memory_regions[name] = memory_region

    def _lower_shmem_config(self):
        if not self.config.shmem:
            return

        root_cell = None
        for name, cell_config in self.config.cells.items():
            if cell_config.type == "root":
                root_cell = cell_config
                break

        if not root_cell:
            raise Exception(
                "A configuration without a root cell is not supported at the moment"
            )

        if len(self.config.shmem) > 4:
            raise Exception(
                "Configuring more than 4 shmem devices is not supported at the moment"
            )

        current_bdf = 0
        pci_domain = root_cell.platform_info.pci_domain

        for name, shmem_config in self.config.shmem.items():
            if shmem_config.protocol == "SHMEM_PROTO_VETH":
                if len(shmem_config.peers) != 2:
                    raise Exception(
                        "shmem-net devices must have exactly 2 peers"
                    )

            # create mem regions
            common_output_region_size = shmem_config.common_output_region_size
            per_device_region_size = shmem_config.per_device_region_size

            if not common_output_region_size:
                common_output_region_size = 0

            if not per_device_region_size:
                per_device_region_size = 0

            mem_regions = list()
            mem_regions_index = 0

            if shmem_config.protocol == "SHMEM_PROTO_VETH":
                common_output_region_size = 0
                per_device_region_size = self.board.pagesize

            table_region = MemoryRegion(size=0x1000,
                physical_start_addr=0,
                virtual_start_addr=0,
                allocatable=False,
                flags=[
                    "MEM_READ",
                    "MEM_ROOTSHARED"
                ],
                next_region=f"{name}_{mem_regions_index+1}"
            )
            mem_regions.append((f"{name}_{mem_regions_index}", table_region))
            mem_regions_index += 1

            common_output_region = MemoryRegion(size=common_output_region_size,
                allocatable=False,
                physical_start_addr=0,
                virtual_start_addr=0,
                flags=[
                    "MEM_READ",
                    "MEM_WRITE",
                    "MEM_ROOTSHARED"
                ],
                next_region=f"{name}_{mem_regions_index+1}"
            )
            mem_regions.append((f"{name}_{mem_regions_index}", common_output_region))
            mem_regions_index += 1

            for cell_name in shmem_config.peers:
                mem_region = MemoryRegion(size=per_device_region_size,
                    allocatable=False,
                    physical_start_addr=0,
                    virtual_start_addr=0,
                    flags=[
                        "MEM_READ",
                        "MEM_ROOTSHARED"
                    ],
                    next_region=f"{name}_{mem_regions_index+1}"
                )
                mem_regions.append((f"{name}_{mem_regions_index}", mem_region))
                mem_regions_index += 1

            mem_regions[-1][1].next_region = None

            # add PCI device to each affected cell
            root_added = False
            current_device_id = 0

            for cell_name in shmem_config.peers:
                cell = self.config.cells[cell_name]
                if cell.type == "root":
                    root_added = True

                pci_dev = PCIDevice(type="PCI_TYPE_IVSHMEM",
                    domain=pci_domain,
                    bdf=current_bdf << 3,
                    bar_mask="IVSHMEM_BAR_MASK_INTX",
                    shmem_regions_start=-1,
                    shmem_dev_id=current_device_id,
                    shmem_peers=len(shmem_config.peers),
                    shmem_protocol=shmem_config.protocol
                )
                pci_dev.memory_regions = mem_regions

                cell.pci_devices[name] = pci_dev
                cell.memory_regions.update(mem_regions)

                # set interrupt pins
                intx_pin = (current_bdf & 0x3)
                intx_pin += cell.vpci_irq_base + 32

                root_irq_chip = None
                for name, chip in root_cell.irqchips.items():
                    if intx_pin in chip.interrupts:
                        root_irq_chip = chip
                        break

                if not root_irq_chip:
                    raise Exception(
                        f"No IRQ chip availbe for interrupt: {intx_pin}"
                    )

                irq_chip = None
                for name, chip in cell.irqchips.items():
                    if intx_pin in chip.interrupts:
                        irq_chip = chip
                        break

                if not irq_chip:
                    irq_chip = IRQChip(address=root_irq_chip.address,
                        pin_base = root_irq_chip.pin_base,
                        interrupts = []
                    )

                    cell.irqchips[f"{name}_{len(cell.irqchips) + 1}"] = irq_chip

                irq_chip.interrupts.append(intx_pin)
                irq_chip.interrupts.sort()

                root_irq_chip.interrupts.append(intx_pin)
                root_irq_chip.interrupts.sort()

                current_device_id += 1

            if not root_added:
                root_cell.mem_regions.update(mem_regions)

            current_bdf += 1

    def _regions_shmem_config(self):
        """ set MEM_WRITE flags accordingly """
        if not self.config.shmem:
            return

        for name, shmem_config in self.config.shmem.items():
            for cell_name in shmem_config.peers:
                cell = self.config.cells[cell_name]

                # offset 2, since mem_regions always
                # start with table_region and common_output_region
                dev_id = cell.pci_devices[name].shmem_dev_id
                mem_region_name = f"{name}_{dev_id + 2}"
                cell_output_region = cell.memory_regions[mem_region_name]

                new_cell_output_region = copy.copy(cell_output_region)
                new_cell_output_region.flags = copy.copy(cell_output_region.flags)
                new_cell_output_region.flags.append("MEM_WRITE")

                cell.memory_regions[mem_region_name] = new_cell_output_region

    def _allocate_memory(self):
        pass

    def prepare(self):
        if self.config is None:
            raise Exception(
                "A configuration without cells_yml is not supported at the moment"
            )

        print("Preparing cell config")

        self._lower_shmem_config()
        for cell_name, cell in self.config.cells.items():
            self._prepare_irqchips(cell)
            self._prepare_memory_regions(cell)
        self._allocate_memory()
        self._regions_shmem_config

    def read_cell_yml(self, cells_yml):
        print("Reading cell configuration", str(cells_yml))
        with open(cells_yml, "r") as stream:
            yaml = ruamel.yaml.YAML()
            yaml_info = yaml.load(stream)
            config = JailhouseConfig(**yaml_info)
            self.config = config


if __name__ == "__main__":
    import sys

    extractor = BoardInfoExtractor(sys.argv[1], sys.argv[2], sys.argv[3])
    board_info = extractor.extract()
    testwriter = BoardConfigurator(board_info)
    testwriter.read_cell_yml(sys.argv[4])
    testwriter.prepare()
    testwriter.write_config(sys.argv[5])
