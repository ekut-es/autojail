from typing import Dict, List, Tuple

import fuzzywuzzy.process
from dataclasses import dataclass
from mako.template import Template

from ..model import (
    Board,
    DeviceMemoryRegion,
    GroupedMemoryRegion,
    JailhouseConfig,
)
from .passes import BasePass


def format_range(val, cells):
    print(hex(val), cells)
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
		${cpu.name}: ${cpu.name} {
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
	${clock.name}: {
		compatible = "fixed-clock";
		#clock-cells = <0>;
		clock-frequency = <${clock.frequency}>;
		clock-output-names = "${",".join(clock.clock_output_names)}";
	};
% endfor

% for name, memory_region in device_regions.items():
    ${name}: {
        compatible = ${",".join((f'"{c}"' for c in memory_region.compatible))};
        reg = <${format_range(memory_region.virtual_start_addr, address_cells)} ${format_range(memory_region.size, size_cells)}>;
    % if memory_region.interrupts:
        interrupts = <
	  %for interrupt in memory_region.interrupts:
                        ${interrupt.type} ${interrupt.num} ${interrupt.flags}
      %endfor
                      >;
    % endif
    % if memory_region.clocks:             
        clocks = < &fixed>;
    %endif
    %if memory_region.clock_names:
        clock-names = <${" ".join('"' + cn + '"' for cn in memory_region.clock_names)}>
    %endif     
        status = "okay";
	};

% endfor    

% if pci_interrupts:
    pci@${hex(pci_mmconfig_base)} {
        compatible = "pci-host-ecam-generic";
        device_type = "pci";
        bus-range = <${format_range(pci_mmconfig_end_bus, address_cells)}>;
        #address-cells = <3>;
        #size-cells = <2>;
        #interrupt-cells = <1>;
        interrupt-map-mask = <0 0 0 7>;
        interrupt-map =  
        %for interrupt in pci_interrupts:
            <0 0 0 ${interrupt.device + 1} &${interrupt.controller} GIC_SPI ${interrupt.interrupt} IRQ_TYPE_EDGE_RISING>${',' if loop.index < len(pci_interrupts) - 1 else ';'}
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
    frequency: int
    clock_output_names: List[str]


class GenerateDeviceTreePass(BasePass):
    """Generate a device tree for inmates"""

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

    def _find_clocks(self, device_regions: Dict[str, DeviceMemoryRegion]):
        clock_paths_dict = self._build_clock_dict()

        for name, device in device_regions.items():
            print("clock device:", name)

            if isinstance(device, DeviceMemoryRegion):
                self.logger.info("Searching clock input for %s", name)

                # clock_paths_dt = self._extract_clock_paths(device)
                # clock_path_strings = []
                # for clock_path in clock_paths_dt:
                #     clock_path = "/".join(reversed(clock_path))
                #     clock_path_strings.append(clock_path)

                # print(clock_path_strings)

                matches: List[str] = []
                for compatible in device.compatible:
                    fuzzy_result = fuzzywuzzy.process.extract(
                        compatible, list(clock_paths_dict.keys()), limit=10,
                    )
                    matches.extend(fuzzy_result)

                matches.sort(key=lambda x: x[1])

                print(matches)

    def __call__(
        self, board: Board, config: JailhouseConfig
    ) -> Tuple[Board, JailhouseConfig]:

        self.logger.info("Generating inmate device trees")

        self.board = board

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

            cpus = []
            assert cell.cpus is not None
            for cpu in cell.cpus:
                board_cpus = list(board.cpuinfo.values())
                cpus.append(board_cpus[cpu])

            device_regions = self._prepare_device_regions(cell.memory_regions)
            clocks = self._find_clocks(device_regions)
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
            )

            dts_name = cell.name.lower()
            dts_name = dts_name.replace(" ", "-")
            dts_name += ".dts"

            self.logger.info("Writing %s", dts_name)
            with open(dts_name, "w") as dts_file:
                dts_file.write(dts_data)

        return board, config


# FIXME: make dts template external file
# flake8: noqa
