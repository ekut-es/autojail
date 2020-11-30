from typing import Tuple

from dataclasses import dataclass
from mako.template import Template

from autojail.model.board import GroupedMemoryRegion

from ..model import Board, JailhouseConfig
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

	timer {
		compatible = "arm,armv8-timer";
		interrupts = <GIC_PPI 13 IRQ_TYPE_LEVEL_HIGH>,
			     <GIC_PPI 14 IRQ_TYPE_LEVEL_HIGH>,
			     <GIC_PPI 11 IRQ_TYPE_LEVEL_HIGH>,
			     <GIC_PPI 10 IRQ_TYPE_LEVEL_HIGH>;
	};

	gic: interrupt-controller@${hex(gic.gicd_base)} {
		compatible = ${",".join((f'"{c}"' for c in gic.compatible))};
		reg = <${format_range(gic.gicd_base, address_cells)} ${format_range(0x1000, size_cells)}>,
		      <${format_range(gic.gicc_base, address_cells)} ${format_range(0x2000, size_cells)}>;
		interrupt-controller;
		#interrupt-cells = <3>;
	};

	fixed: clk500mhz {
		compatible = "fixed-clock";
		#clock-cells = <0>;
		clock-frequency = <500000000>;
		clock-output-names = "clk500mhz";
	};

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
                if region.compatible:
                    device_regions[name] = region

        return device_regions

    def __call__(
        self, board: Board, config: JailhouseConfig
    ) -> Tuple[Board, JailhouseConfig]:

        self.logger.info("Generating inmate device trees")

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
            from devtools import debug

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
