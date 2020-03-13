from pathlib import Path
from ..model import (
    Board,
    MemoryRegion,
    SHMemoryRegion,
    CellYML,
    BaseInfos,
    DebugConsole,
    HypervisorMemory,
    IRQChips,
    PlatformInfo,
    PCIDevices,
    ShMemNet,
    SHMemoryRegionTest,
)
import yaml


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
            for x in iomem_info:
                start_addr, temp, *rest = x.split("-", 1)
                temp = temp.strip()
                start_addr = start_addr.strip()
                physical_start_addr.append(start_addr)
                end_addr, temp = temp.split(":", 1)

                end_addr = end_addr.split(" ", 1)[0]
                # end_addr_list.append(end_addr)
                size_calculated = int(end_addr, 16) - int(start_addr, 16)
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
                            res2 = any(temp in sublist for sublist in memory_regions)
                            if res2 == 0:
                                memory_regions.append(temp)

                                res = 0
                            else:
                                res = 1
        mem_regs = {}
        for i, name in enumerate(memory_regions):
            memory_region = MemoryRegion(
                physical_start_addr=int(physical_start_addr[i], 16),
                virtual_start_addr=int(physical_start_addr[i], 16),
                size=size[i],
                flags=["MEM_READ"],
            )
            mem_regs[name] = memory_region

        return mem_regs

    def extract(self):
        memory_regions = self.read_iomem(self.data_root / "proc" / "iomem")

        board = Board(name=self.name, board=self.board, memory_regions=memory_regions)
        return board


class BoardConfigurator:
    def writeToFile(self, board, cell):
        f = open("config_rpi4.c", "w+")
        amount_pci_devices = len(cell.pci_devices.__dict__)
        amount_memory_regions = len(board.memory_regions) + len(
            cell.additional_memory_regions
        )
        cpu_set = parseIntSet(cell.cpus)
        cpu_calculated = (len(cpu_set) // 64) + 1  # 64 von rpi4.c  Datentypgröße :__u64
        # jailhouse_flag_part = "JAILHOUSE_"
        # test = sys.getsizeof(0b1111)
        # debug(test)
        f.write("#include <jailhouse/types.h>\n")
        f.write("#include <jailhouse/cell-config.h>\n")

        f.write("struct { \n")
        f.write("\tstruct jailhouse_system header; \n")
        f.write("\t__u64 cpus[" + str(cpu_calculated) + "];\n")
        f.write(
            "\tstruct jailhouse_memory mem_regions["
            + str(amount_memory_regions)
            + "];\n"
        )
        f.write("\tstruct jailhouse_irqchip irqchips[1];\n")  # TODO:
        # f.write("\tstruct jailhouse_pio pio_regions[13];\n") # Unnötig für ARM
        f.write(
            "\tstruct jailhouse_pci_device pci_devices["
            + str(amount_pci_devices)
            + "];\n"
        )
        # f.write("\tstruct jailhouse_pci_capability pci_caps[39];\n")  # TODO:
        f.write("} __attribute__((packed)) config = {\n")
        f.write("\n.header = {")

        f.write("\n\t.platform_info = {")
        f.write(
            "\n\t\t.pci_mmconfig_base = "
            + str(cell.platform_info.pci_mmconfig_base)
            + ","
        )
        f.write(
            "\n\t\t.pci_mmconfig_end_bus = "
            + str(cell.platform_info.pci_mmconfig_end_bus)
            + ","
        )
        f.write(
            "\n\t\t.pci_is_virtual = " + str(cell.platform_info.pci_is_virtual) + ","
        )
        f.write("\n\t\t.pci_domain = " + str(cell.platform_info.pci_domain) + ",")
        f.write("\n\t\t.arm = {")
        arm_values = cell.platform_info.arm.split(",")[:-1]
        for i in range(len(arm_values)):
            f.write("\n\t\t\t." + str(arm_values[i]).strip() + ",")
        f.write("\n\t\t},\n")
        f.write("\n\t},\n")
        f.write("\n\t.debug_console = {")
        f.write("\n\t\t.address = " + hex(cell.debug_console.adress) + ",")
        f.write("\n\t\t.size = " + hex(cell.debug_console.size) + ",")
        f.write("\n\t\t.type = " + "JAILHOUSE_" + cell.debug_console.Type + ",")
        f.write("\n\t\t.size = " + hex(cell.debug_console.size) + ",")
        s = "|"
        jailhouse_flags = ["JAILHOUSE_" + flag for flag in cell.debug_console.flags]
        f.write("\n\t\t.flags = " + str(s.join(jailhouse_flags)) + ",")
        f.write("\n\t},\n")

        f.write("\n\t.hypervisor_memory = {")
        f.write(
            "\n\t\t.phys_start = "
            + hex(cell.hypervisor_memory.physical_start_addr)
            + ","
        )
        f.write("\n\t\t.size = " + cell.hypervisor_memory.size + ",")
        f.write("\n\t},\n")

        cell_type_temp = cell.base_infos.Type
        if cell_type_temp == "root":
            f.write("\n\t.root_cell = {")
        else:
            f.write("\n\t.guest_cell = {")
        f.write("\n\t\t.name =" + " \"" + cell.base_infos.name + "\" " + ",")
        f.write("\n\t\t.vpci_irq_base = " + str(cell.base_infos.vpci_irq_base) + ",")
        s = "|"
        jailhouse_flags = ["JAILHOUSE_" + flag for flag in cell.base_infos.flags]
        f.write("\n\t\t.flags = " + str(s.join(jailhouse_flags)) + ",")
        f.write("\n\t\t.num_memory_regions = " + str(amount_memory_regions) + ",")
        f.write("\n\t\t.num_pci_devices = " + str(amount_pci_devices) + ",")
        f.write(
            "\n\t\t.cpu_set_size = " + str(cpu_calculated) + ","
        )  # lookatthis later
        f.write("\n\t\t.num_irqchips = " + str(1) + ",")
        # f.write("\n\t\t//.num_pci_caps !!//TODO: = " + ",")
        f.write("\n\t},")
        f.write("\n\t},")

        f.write("\n\t.cpus = ")
        cpu_set_tmp = "0b" + "0" * (max(cpu_set)+1)
        s = list(cpu_set_tmp)
        for e in cpu_set:
            s[(max(cpu_set)+2)-e] = str(1)
        s = "".join(s)
        f.write(s + ",")
        f.write("\n\t")
        f.write("\n\t.mem_regions = {\n")
        for k, v in board.memory_regions.items():
            f.write(
                "\t/*"
                + k
                + " "
                + hex(v.physical_start_addr)
                + "-"
                + hex(v.physical_start_addr + v.size)
                + "*/\n"
            )
            f.write("\t{")
            f.write("\n\t\t.phys_start = " + hex(v.physical_start_addr) + ",")
            f.write("\n\t\t.virt_start = " + hex(v.virtual_start_addr) + ",")
            f.write("\n\t\t.size = " + hex(v.size) + ",")
            s = "|"
            jailhouse_flags = ["JAILHOUSE_" + flag for flag in v.flags]
            f.write("\n\t\t.flags = " + str(s.join(jailhouse_flags)) + ",")
            f.write("\n\t},\n")

        for k, v in cell.additional_memory_regions.items():
            f.write(
                "\t/*"
                + k
                + " "
                + hex(v.physical_start_addr)
                + "-"
                + hex(v.physical_start_addr + v.size)
                + "*/\n"
            )
            f.write("\t{")
            f.write("\n\t\t.phys_start = " + hex(v.physical_start_addr) + ",")
            f.write("\n\t\t.virt_start = " + hex(v.virtual_start_addr) + ",")
            f.write("\n\t\t.size = " + hex(v.size) + ",")
            s = "|"
            jailhouse_flags = ["JAILHOUSE_" + flag for flag in v.flags]
            f.write("\n\t\t.flags = " + str(s.join(jailhouse_flags)) + ",")
            f.write("\n\t},\n")
        f.write("\t},")
        f.write("\n\t.irqchips = {")
        for i in range(len(cell.irqchips.pin_base)):
            f.write("\n\t\t{")
            f.write("\n\t\t\t.address = " + hex(cell.irqchips.adress) + ",")
            hex_bitmap = "".join(["0x%x, " % b for b in cell.irqchips.pin_bitmap[i]])
            f.write("\n\t\t\t.pin_base = " + str(cell.irqchips.pin_base[i]) + ",")
            # f.write("\n\t\t\t.interrupts = " + str(cell.irqchips.interrupts) + ",") TODO:
            f.write("\n\t\t\t.pin_bitmap = " + hex_bitmap.rstrip(','))
            f.write("\n\t\t},")
        # interrupt_set = parseIntSet(cell.irqchips.interrupts)
        # f.write("\n\t.interrupt_set = " + str(interrupt_set) + ",")
        f.write("\n\t},\n")

        f.write("\n\t.pci_devices = {")
        device_keys = list(cell.pci_devices.__dict__.keys())
        device_values = list(cell.pci_devices.__dict__.values())
        for i in range(len(cell.pci_devices.__dict__.keys())):
            f.write("\n\t\t/*" + device_keys[i] + "*/")
            f.write("\n\t\t{")
            device_values_temp = device_values[i].split(",")[:-1]
            for j in range(len(device_values_temp)):
                f.write("\n\t\t\t." + str(device_values_temp[j]).strip() + ",")
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

    def read_Cell_YML(self, board):
        with open("../projects/rpi4_test1/cells.yml", "r") as stream:
            try:
                yaml_info = yaml.safe_load(stream)
                base_infos = BaseInfos()
                base_infos.Type = recursive_lookup("type", yaml_info)
                base_infos.name = recursive_lookup("name", yaml_info)
                base_infos.vpci_irq_base = recursive_lookup("vpci_irq_base", yaml_info)
                base_infos.flags = recursive_lookup("flags", yaml_info)
                pci_devices = PCIDevices()
                pci_devices_yml = recursive_lookup("pci_devices", yaml_info)
                pci_devices.demo = recursive_lookup("demo", pci_devices_yml)
                pci_devices.networking = recursive_lookup("networking", pci_devices_yml)
                irqChips = IRQChips()
                irqChips_yml = recursive_lookup("irqchips", yaml_info)
                irqChips.adress = recursive_lookup("address", irqChips_yml)
                irqChips.pin_base = recursive_lookup("pin_base", irqChips_yml)
                irqChips.interrupts = recursive_lookup("interrupts", irqChips_yml)
                irqChips.pin_bitmap = recursive_lookup("pin_bitmap", irqChips_yml)
                hypMem = HypervisorMemory()
                hypMem_yml = recursive_lookup("hypervisor_memory", yaml_info)
                hypMem.physical_start_addr = recursive_lookup("phys_start", hypMem_yml)
                hypMem.size = recursive_lookup("size", hypMem_yml)

                memory_regions_yml = recursive_lookup("mem_regions", yaml_info)
                shmem_net = ShMemNet()
                shmem_net_base_yml = recursive_lookup("shmem_net", memory_regions_yml)
                shmem_net.start_addr = recursive_lookup("start", shmem_net_base_yml)
                shmem_net.device_id = recursive_lookup("dev_id", shmem_net_base_yml)
                test_region_names = memory_regions_yml.keys()
                keylist = []
                keylist.extend(iter(test_region_names))
                len_loop = len(keylist) - 1
                mem_regs = {}
                for i, name in enumerate(memory_regions_yml):
                    if i < len_loop:
                        phys = recursive_lookup(
                            "physical_start_addr", memory_regions_yml
                        )
                        virt = recursive_lookup(
                            "virtual_start_addr", memory_regions_yml
                        )
                        siz = recursive_lookup("size", memory_regions_yml)
                        flag = recursive_lookup("flags", memory_regions_yml)
                    else:
                        break

                    memory_region = SHMemoryRegionTest()
                    memory_region.physical_start_addr = phys
                    memory_region.virtual_start_addr = virt
                    memory_region.size = siz
                    memory_region.flags = flag
                    mem_regs[name] = memory_region
                debug_console = recursive_lookup("debug_console", yaml_info)
                platInfo = PlatformInfo()
                platform_info_yml = recursive_lookup("platform_info", yaml_info)
                platInfo.pci_mmconfig_base = recursive_lookup(
                    "pci_mmconfig_base", platform_info_yml
                )
                platInfo.pci_mmconfig_end_bus = recursive_lookup(
                    "pci_mmconfig_end_bus", platform_info_yml
                )
                platInfo.pci_is_virtual = recursive_lookup(
                    "pci_is_virtual", platform_info_yml
                )
                platInfo.pci_domain = recursive_lookup("pci_domain", platform_info_yml)
                platInfo.arm = recursive_lookup("arm", platform_info_yml)

                debCon = DebugConsole()
                debCon.adress = recursive_lookup("address", debug_console)
                debCon.size = recursive_lookup("size", debug_console)
                debCon.Type = recursive_lookup("type", debug_console)
                debCon.flags = recursive_lookup("flags", debug_console)
                cellYML = CellYML()
                cellYML.base_infos = base_infos
                cellYML.hypervisor_memory = hypMem
                cellYML.debug_console = debCon
                cellYML.platform_info = platInfo
                cellYML.additional_memory_regions = mem_regs
                cellYML.cpus = recursive_lookup("cpus", yaml_info)
                cellYML.sh_mem_net = shmem_net
                cellYML.irqchips = irqChips
                cellYML.pci_devices = pci_devices
                return cellYML

            except yaml.YAMLError as exc:
                return exc


def recursive_lookup(k, d):
    if k in d:
        return d[k]
    for v in d.values():
        if isinstance(v, dict):
            a = recursive_lookup(k, v)
            if a is not None:
                return a
    return None


def parseIntSet(nputstr=""):
    selection = set()
    invalid = set()
    # tokens are comma seperated values
    tokens = [x.strip() for x in nputstr.split(",")]
    for i in tokens:
        if len(i) > 0:
            if i[:1] == "<":
                i = "1-%s" % (i[1:])
        try:
            # typically tokens are plain old integers
            selection.add(int(i))
        except:
            # if not, then it might be a range
            try:
                token = [int(k.strip()) for k in i.split("-")]
                if len(token) > 1:
                    token.sort()
                    # we have items seperated by a dash
                    # try to build a valid range
                    first = token[0]
                    last = token[len(token) - 1]
                    for x in range(first, last + 1):
                        selection.add(x)
            except:
                # not an int and not a range...
                invalid.add(i)
    return selection


if __name__ == "__main__":
    import sys

    extractor = BoardInfoExtractor(sys.argv[1], sys.argv[2], sys.argv[3])
    board_info = extractor.extract()
    testwriter = BoardConfigurator()
    read_cell = testwriter.read_Cell_YML(board_info)
    test = testwriter.writeToFile(board_info, read_cell)
