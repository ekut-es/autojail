import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, MutableMapping, Optional, Tuple

# import fuzzywuzzy.process
from dataclasses import dataclass
from mako.template import Template

from autojail.model.jailhouse import CellConfig

from ..model import (
    AutojailConfig,
    Board,
    DeviceMemoryRegion,
    GroupedMemoryRegion,
    JailhouseConfig,
)
from .passes import BasePass


def format_range(val, cells):
    chunks = [hex((val >> i * 32) & 0xFFFFFFFF) for i in range(0, cells)]
    chunks.reverse()

    return " ".join(chunks)


_dts_template = Template(
    r"""
#include <dt-bindings/interrupt-controller/arm-gic.h>

/dts-v1/;

/ {
	model = "Jailhouse cell: ${cell.name}";

	#address-cells = <${address_cells}>;
	#size-cells = <${size_cells}>;

	interrupt-parent = < &gic>;

	hypervisor {
		compatible = "jailhouse,cell";
	};

	cpus {
		#address-cells = <1>;
		#size-cells = <0>;
% for cpu in cpus:
		${cpu.name} {
			device_type = "cpu";
			compatible = "${cpu.compatible}";
			reg = <${cpu.num}>;
			enable-method = "${cpu.enable_method}";
		};
% endfor
	};

	psci {
		compatible = "arm,psci-0.2";
		method = "smc";
	};
    
    %if timer:
    timer {
        compatible = "${timer.compatible[0]}";
        interrupts = 
          %for interrupt in timer.interrupts:
              <${interrupt.type} ${interrupt.num} ${interrupt.flags}>${";" if loop.last else ","}
          %endfor

    };
    %endif

	gic: interrupt-controller@${hex(gic.gicd_base)} {
		compatible = ${",".join((f'"{c}"' for c in gic.compatible))};
		reg = <${format_range(gic.gicd_base, address_cells)} ${format_range(0x1000, size_cells)}>,
		      <${format_range(gic.gicc_base, address_cells)} ${format_range(0x2000, size_cells)}>;
		interrupt-controller;
		#interrupt-cells = <3>;
	};

% for clock in clocks:
	${clock.label_name}: ${clock.name}{
		compatible = "fixed-clock";
		#clock-cells = <0>;
		clock-frequency = <${clock.rate}>;
	};
% endfor

% for name, memory_region in device_regions.items():
    ${name} {
        compatible = ${",".join((f'"{c}"' for c in memory_region.compatible))};
        reg = <${format_range(memory_region.virtual_start_addr, address_cells)} ${format_range(memory_region.size, size_cells)}>;
    % if memory_region.interrupts:
        interrupts = <
	  %for interrupt in memory_region.interrupts:
                        ${interrupt.type} ${interrupt.num} ${interrupt.flags}
      %endfor
                      >;
    % endif
    % if memory_region.name in clock_mapping:             
        clocks = < 
        %for clock in clock_mapping[memory_region.name]:
            %if clock is not None:
                 &${clock.label_name}
            %endif
        %endfor
                 >;
    %endif
    %if memory_region.clock_names:
        clock-names = ${", ".join('"' + cn + '"' for cn in memory_region.clock_names)};
    %endif     
        status = "okay";
	};

% endfor    

% if pci_interrupts:
    pci@${hex(pci_mmconfig_base)} {
        compatible = "pci-host-ecam-generic";
        device_type = "pci";
        #address-cells = <3>;
        #size-cells = <2>;
        #interrupt-cells = <1>;
        interrupt-map-mask = <0 0 0 7>;
        interrupt-map =  
        %for interrupt in pci_interrupts:
            <0 0 0 ${interrupt.device + 1} &${interrupt.controller} GIC_SPI ${interrupt.interrupt - 32} IRQ_TYPE_EDGE_RISING>${',' if loop.index < len(pci_interrupts) - 1 else ';'}
        %endfor
        reg = <0x0 ${hex(pci_mmconfig_base)} 0x0 0x100000>;
        ranges =
             <0x02000000 0x00 0x10000000 0x0 0x10000000 0x00 0x10000>;
	};
% endif
	
};
"""
)


@dataclass
class PCIInterruptData:
    bus: int
    device: int
    function: int
    controller: str
    interrupt: int


@dataclass
class DTClock:
    name: str
    label_name: str
    rate: int


class GenerateDeviceTreePass(BasePass):
    """Generate a device tree for inmates"""

    def __init__(self, config: AutojailConfig):
        self.autojail_config = config
        super(GenerateDeviceTreePass, self).__init__()

    def _prepare_device_regions(self, memory_regions):
        worklist = [(name, region) for name, region in memory_regions.items()]
        device_regions = {}

        while worklist:
            name, region = worklist.pop()
            if isinstance(region, GroupedMemoryRegion):
                for num, sub_region in enumerate(region.regions):
                    worklist.append((name + "." + str(num), sub_region))
            else:
                if isinstance(region, DeviceMemoryRegion):
                    device_regions[name] = region

        return device_regions

    def _find_timer(self):
        timer_compatibles = ["arm,armv8-timer", "arm,armv7-timer"]
        for device in self.board.devices.values():
            for compatible in timer_compatibles:
                if compatible in device.compatible:
                    return device

        return None

    def _build_clock_dict(self):
        clocks = {}
        worklist = list(self.board.clock_tree.items())
        while worklist:
            path, clock = worklist.pop()
            clocks[path] = clock

            for name, derived_clock in clock.derived_clocks.items():
                worklist.append((name, derived_clock))

        return clocks

    def _find_clock_parent(self, handle):
        print("Searching for parent", handle)
        for name, device in self.board.devices.items():
            if device.phandle == handle:
                print("Found parent", name, "handle is", handle)
                return name, device

    def _extract_clock_paths(self, device):
        device_clocks = list(reversed(device.clocks))
        paths = []

        print("Device clocks: ", ",".join(device_clocks))
        while device_clocks:
            clock_parent_handle = int(device_clocks.pop())
            parent_name, parent = self._find_clock_parent(clock_parent_handle)

            if parent.clock_cells == 0:
                clock_num = 0
            elif parent.clock_cells == 1:
                clock_num = int(device_clocks.pop())
            else:
                raise Exception(
                    "Unhandled number of clock_cells: %d", parent.clock_cells
                )

            for compatible in device.compatible:
                if parent.clock_output_names:
                    parent_path = (parent.clock_output_names[clock_num],)
                    paths.append((compatible,) + parent_path)
                else:
                    parent_paths = self._extract_clock_paths(parent)
                    print("Searching for clock", clock_num)
                    for parent_path in parent_paths:
                        paths.append((compatible,) + parent_path)

        return paths

    def _find_clock_rate(self, clock_name):
        worklist = list(self.board.clock_tree.values())

        while worklist:
            current_clock = worklist.pop()

            print(current_clock.name, clock_name)
            if current_clock.name == clock_name:
                return current_clock.rate

            worklist.extend(current_clock.derived_clocks.values())

        return -1

    def _find_clocks(self, device_regions: Dict[str, DeviceMemoryRegion]):

        # clock_paths_dict = self._build_clock_dict()

        dt_clocks: List[DTClock] = []
        clock_mapping_dict: MutableMapping[
            str, List[Optional[DTClock]]
        ] = defaultdict(list)
        for name, device in device_regions.items():
            if isinstance(device, DeviceMemoryRegion):
                if not device.clocks:
                    continue

                self.logger.info("Searching clock input for %s", name)

                clock_input_names: List[str] = []
                if name in self.board.clock_mapping:
                    mapped_clocks = self.board.clock_mapping[name]
                    clock_input_names = [
                        mapped_clock.parent_name
                        for mapped_clock in mapped_clocks
                        if mapped_clock.parent_name
                    ]
                else:
                    self.logger.warning(
                        "Could not find clock input names for: %s", name
                    )
                    self.logger.warning("Trying fuzzy match")
                    # FIXME: TODO

                for clock_name in clock_input_names:
                    clock_rate = self._find_clock_rate(clock_name)
                    selected_clock = None
                    if clock_rate > 0:
                        for dt_clock in dt_clocks:
                            if dt_clock.rate == clock_rate:
                                selected_clock = dt_clock
                                break
                        if selected_clock is None:
                            selected_clock = DTClock(
                                name=f"fixed_{clock_rate}Hz",
                                rate=clock_rate,
                                label_name=f"fixed{len(dt_clocks)}",
                            )
                            dt_clocks.append(selected_clock)

                    assert device.name
                    clock_mapping_dict[device.name].append(selected_clock)

        return clock_mapping_dict, dt_clocks

    def __build_pciconfig(self, config):

        pci_mmconfig_base = None
        pci_mmconfig_end_bus = None
        for _cell_name, cell in config.cells.items():
            if cell.type == "root":
                if cell.platform_info is not None:
                    pci_mmconfig_base = cell.platform_info.pci_mmconfig_base
                    pci_mmconfig_end_bus = (
                        cell.platform_info.pci_mmconfig_end_bus
                    )
                    break

        return pci_mmconfig_base, pci_mmconfig_end_bus

    def _build_cpus(self, cell: CellConfig, board: Board):
        cpus = []
        assert cell.cpus is not None
        for cpu in cell.cpus:
            board_cpus = list(board.cpuinfo.values())
            cpus.append(board_cpus[cpu])
        return cpus

    def __call__(
        self, board: Board, config: JailhouseConfig
    ) -> Tuple[Board, JailhouseConfig]:

        self.logger.info("Generating inmate device trees")

        # FIXME: use build dir
        dts_path = Path(self.autojail_config.build_dir) / "dts"
        dts_path.mkdir(exist_ok=True, parents=True)
        dts_names = []

        self.board = board

        pci_mmconfig_base, pci_mmconfig_end_bus = self.__build_pciconfig(config)

        for _cell_name, cell in config.cells.items():
            if cell.type == "root":
                continue
            pci_interrupts = []
            vpci_irq_base = cell.vpci_irq_base
            if cell.pci_devices is not None:
                for _name, pci_device in cell.pci_devices.items():

                    bus = pci_device.bus
                    device = pci_device.device
                    function = pci_device.function
                    interrupt = (
                        int(pci_device.device) if pci_device is not None else 0
                    )
                    controller = "gic"

                    assert function is not None
                    assert bus is not None
                    assert device is not None
                    assert interrupt is not None
                    assert vpci_irq_base is not None

                    interrupt_data = PCIInterruptData(
                        bus=bus,
                        device=device,
                        function=function,
                        interrupt=interrupt + vpci_irq_base,
                        controller=controller,
                    )
                    pci_interrupts.append(interrupt_data)

            cpus = self._build_cpus(cell, board)
            device_regions = self._prepare_device_regions(cell.memory_regions)
            clock_mapping, clocks = self._find_clocks(device_regions)

            timer = self._find_timer()

            dts_data = _dts_template.render(
                address_cells=2,
                size_cells=2,
                cell=cell,
                device_regions=device_regions,
                gic=board.interrupt_controllers[0],
                pci_mmconfig_base=pci_mmconfig_base,
                pci_mmconfig_end_bus=pci_mmconfig_end_bus,
                pci_interrupts=pci_interrupts,
                cpus=cpus,
                format_range=format_range,
                timer=timer,
                clocks=clocks,
                clock_mapping=clock_mapping,
            )

            dts_name = cell.name.lower()
            dts_name = dts_name.replace(" ", "-")
            dts_name += ".dts"
            dts_names.append(dts_name)

            dts_file_path = dts_path / dts_name

            self.logger.info("Writing %s", dts_file_path)
            with dts_file_path.open("w") as dts_file:
                dts_file.write(dts_data)

        if dts_names:
            makefile_path = dts_path / "Makefile"
            with makefile_path.open("w") as makefile:
                for name in dts_names:
                    dtb_name = name.replace(".dts", ".dtb")
                    makefile.write(f"dtb-y += {dtb_name}\n")
            build_dts_command = [
                "make",
                "-C",
                f"{Path(self.autojail_config.kernel_dir).absolute()}",
                f"ARCH={self.autojail_config.arch.lower()}",
                f"CROSS_COMPILE={self.autojail_config.cross_compile}",
                f"M={dts_path.absolute()}",
            ]
            print(" ".join(build_dts_command))
            subprocess.run(build_dts_command, check=True)

        return board, config


# FIXME: make dts template external file
# flake8: noqa
