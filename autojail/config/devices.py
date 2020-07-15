from collections import namedtuple

from .passes import BasePass
from ..model import DebugConsole

ConsoleSettings = namedtuple("ConsoleSettings", ["type", "flags"])

console_sentinels = {
    "brcm,bcm2835-aux-uart": ConsoleSettings(
        "CON_TYPE_8250", ["CON_ACCESS_MMIO", "CON_REGDIST_4"]
    )
}


class LowerDevicesPass(BasePass):
    def _find_device(self, board, name):
        for device_name, device in board.memory_regions.items():
            if name in device.aliases or device.path == name:
                return device_name, device

        return None, None

    def _lower_console(self, board, config):
        for cell in config.cells.values():
            if isinstance(cell.debug_console, str):
                console_name, console_region = self._find_device(
                    board, cell.debug_console
                )

                sentinel = None
                for compatible in console_region.compatible:
                    if compatible in console_sentinels:
                        sentinel = console_sentinels[compatible]
                        break

                if sentinel is None:
                    self.logger.warn("Could not infer console type")
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
                cell.memory_regions[console_name] = console_region

    def _lower_devices(self, board, config):
        for cell in config.cells.values():
            for region_name, memory_region in cell.memory_regions.items():
                if isinstance(memory_region, str):
                    _, device_region = self._find_device(board, memory_region)
                    cell.memory_regions[region_name] = device_region

    def _lower_interrupts(self, board, config):
        for cell in config.cells.values():
            irqchip = list(cell.irqchips.values())[0]
            for memory_region in cell.memory_regions.values():
                for interrupt in memory_region.interrupts:
                    irqchip.interrupts.append(interrupt)
            irqchip.interrupts.sort()

    def __call__(self, board, config):
        self._lower_console(board, config)
        self._lower_devices(board, config)
        self._lower_interrupts(board, config)
