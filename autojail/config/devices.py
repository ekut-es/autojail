from collections import namedtuple
from copy import deepcopy
from typing import Optional, Tuple

from autojail.model.board import Board, DeviceMemoryRegion
from autojail.model.jailhouse import JailhouseConfig

from ..model import DebugConsole
from .passes import BasePass

ConsoleSettings = namedtuple("ConsoleSettings", ["type", "flags"])

console_sentinels = {
    "brcm,bcm2835-aux-uart": ConsoleSettings(
        "CON_TYPE_8250", ["CON_ACCESS_MMIO", "CON_REGDIST_4"]
    ),
    "xlnx,xuartps": ConsoleSettings(
        "CON_TYPE_XUARTPS", ["CON_ACCESS_MMIO", "CON_REGDIST_4"]
    ),
}


class LowerDevicesPass(BasePass):
    def _find_device(
        self, board: Board, name: str
    ) -> Tuple[Optional[str], Optional[DeviceMemoryRegion]]:
        for device_name, device in board.memory_regions.items():
            if isinstance(device, DeviceMemoryRegion):
                if name in device.aliases or device.path == name:
                    return device_name, device

        return None, None

    def _lower_console(self, board: Board, config: JailhouseConfig) -> None:
        for cell in config.cells.values():
            if isinstance(cell.debug_console, str):
                console_name, console_region = self._find_device(
                    board, cell.debug_console
                )

                if console_region is None:
                    raise Exception(
                        f"Could not find console devices with name: {cell.debug_console}"
                    )

                sentinel = None
                for compatible in console_region.compatible:
                    if compatible in console_sentinels:
                        sentinel = console_sentinels[compatible]
                        break

                if sentinel is None:
                    self.logger.warn(
                        "Could not infer console type assuming: CON_TYPE_8250, CON_REGDIST_4"
                    )
                    con_type, con_flags = (
                        "CON_TYPE_8250",
                        ["CON_ACCESS_MMIO", "CON_REGDIST_4"],
                    )
                else:
                    con_type, con_flags = sentinel

                cell.debug_console = DebugConsole(
                    address=console_region.virtual_start_addr,
                    size=console_region.size,
                    type=con_type,
                    flags=con_flags,
                )
                assert cell.memory_regions is not None
                assert console_name is not None
                cell.memory_regions[console_name] = deepcopy(console_region)

    def _lower_devices(self, board: Board, config: JailhouseConfig) -> None:
        for cell in config.cells.values():
            assert cell.memory_regions is not None
            for region_name, memory_region in cell.memory_regions.items():
                if isinstance(memory_region, str):
                    _, device_region = self._find_device(board, memory_region)
                    if device_region is None:
                        raise Exception(
                            f"Could not find device named {memory_region}"
                        )

                    cell.memory_regions[region_name] = deepcopy(device_region)

    def _lower_interrupts(self, board: Board, config: JailhouseConfig) -> None:
        for cell in config.cells.values():
            assert cell.irqchips is not None
            assert cell.memory_regions is not None

            irqchip = list(cell.irqchips.values())[0]
            for memory_region in cell.memory_regions.values():
                if isinstance(memory_region, DeviceMemoryRegion):
                    for interrupt in memory_region.interrupts:
                        irqchip.interrupts.append(interrupt.to_jailhouse())
            irqchip.interrupts.sort()

    def __call__(
        self, board: Board, config: JailhouseConfig
    ) -> Tuple[Board, JailhouseConfig]:
        self._lower_console(board, config)
        self._lower_devices(board, config)
        self._lower_interrupts(board, config)

        return board, config
