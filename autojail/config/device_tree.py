from dataclasses import dataclass
from typing import Tuple

from mako.template import Template

from ..model import Board, JailhouseConfig
from .passes import BasePass

_dts_template = Template(
    r"""
/dts-v1/;

/ {
	model = "Jailhouse cell on Raspberry Pi 4";

	#address-cells = <2>;
	#size-cells = <2>;

	interrupt-parent = <&gic>;

	hypervisor {
		compatible = "jailhouse,cell";
	};

	cpus {
		#address-cells = <1>;
		#size-cells = <0>;

		cpu2: cpu@2 {
			device_type = "cpu";
			compatible = "arm,cortex-a72";
			reg = <2>;
			enable-method = "psci";
		};

		cpu3: cpu@3 {
			device_type = "cpu";
			compatible = "arm,cortex-a72";
			reg = <3>;
			enable-method = "psci";
		};
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

	gic: interrupt-controller@ff841000 {
		compatible = "arm,gic-400";
		reg = <0x0 0xff841000 0x0 0x1000>,
		      <0x0 0xff842000 0x0 0x2000>;
		interrupt-controller;
		#interrupt-cells = <3>;
	};

	fixed: clk500mhz {
		compatible = "fixed-clock";
		#clock-cells = <0>;
		clock-frequency = <500000000>;
		clock-output-names = "clk500mhz";
	};

	uart1: serial@fe215040 {
		compatible = "brcm,bcm2835-aux-uart";
		reg = <0x0 0xfe215040 0x0 0x40>;
		interrupts = <GIC_SPI 93 IRQ_TYPE_LEVEL_HIGH>;
		clocks = <&fixed>;
		status = "okay";
	};

% if pci_interrupts:
	pci@${hex(pci_mmconfig_base)} {
		compatible = "pci-host-ecam-generic";
		device_type = "pci";
		bus-range = <0 ${pci_mmconfig_end_bus}>;
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

    def __call__(
        self, board: Board, config: JailhouseConfig
    ) -> Tuple[Board, JailhouseConfig]:

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

                    interrupt_data = PCIInterruptData(
                        bus=bus,
                        device=device,
                        function=function,
                        interrupt=interrupt + vpci_irq_base,
                        controller=controller,
                    )
                    pci_interrupts.append(interrupt_data)

            print(
                _dts_template.render(
                    pci_mmconfig_base=pci_mmconfig_base,
                    pci_mmconfig_end_bus=pci_mmconfig_end_bus,
                    pci_interrupts=pci_interrupts,
                )
            )

        return board, config


# flake8: noqa
