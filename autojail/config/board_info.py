from typing import Tuple

from ..model import (
    Board,
    IntegerList,
    IRQChip,
    JailhouseConfig,
    PlatformInfo,
    PlatformInfoArm,
)
from ..utils.logging import getLogger
from .passes import BasePass


class TransferBoardInfoPass(BasePass):
    def __init__(self) -> None:
        self.logger = getLogger()

    def _create_irqchips(self, board: Board, config: JailhouseConfig) -> None:
        for cell in config.cells.values():
            if cell.irqchips:
                continue

            gic = board.interrupt_controllers[0]

            interrupts = IntegerList.validate([])
            if cell.type == "root":
                interrupts = gic.interrupts

            assert cell.irqchips is not None
            cell.irqchips["gic"] = IRQChip(
                address=gic.gicd_base, pin_base=32, interrupts=interrupts
            )

    def _create_platform_info(
        self, board: Board, config: JailhouseConfig
    ) -> None:
        for cell in config.cells.values():
            if cell.type != "root":
                continue

            if cell.platform_info is None:
                self.logger.warn("Platform info has not been defined")
                self.logger.warn("Assuming:")
                self.logger.warn("  pci_mmconfig_end_bus=0x800000000")
                self.logger.warn("  pci_is_virtual=1")
                self.logger.warn("  pci_domain=1")
                cell.platform_info = PlatformInfo(
                    pci_mmconfig_end_bus=0x800000000,
                    pci_is_virtual=1,
                    pci_domain=1,
                )

    def _create_arm_info(self, board: Board, config: JailhouseConfig) -> None:
        for cell in config.cells.values():
            if cell.type != "root":
                continue

            assert cell.platform_info is not None

            if cell.platform_info.arch is not None:
                return

            gic = board.interrupt_controllers[0]

            cell.platform_info.arch = PlatformInfoArm(
                maintenance_irq=gic.maintenance_irq,
                gic_version=gic.gic_version,
                gicd_base=gic.gicd_base,
                gicc_base=gic.gicc_base,
                gich_base=gic.gich_base,
                gicv_base=gic.gicv_base,
                gicr_base=gic.gicr_base,
            )

    def __call__(
        self, board: Board, config: JailhouseConfig
    ) -> Tuple[Board, JailhouseConfig]:
        self.logger.info("Lowering board info")
        self._create_platform_info(board, config)
        self._create_irqchips(board, config)
        self._create_arm_info(board, config)

        return board, config
