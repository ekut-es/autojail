from typing import Tuple

from ..model import (
    Board,
    HexInt,
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
                self.logger.warning("Platform info has not been defined")
                self.logger.warning("Assuming:")
                self.logger.warning("  pci_mmconfig_end_bus=0")
                self.logger.warning("  pci_is_virtual=1")
                self.logger.warning("  pci_domain=1")
                cell.platform_info = PlatformInfo(
                    pci_mmconfig_end_bus=0, pci_is_virtual=1, pci_domain=1,
                )

    def _create_arm_info(self, board: Board, config: JailhouseConfig) -> None:
        for cell in config.cells.values():
            if cell.type != "root":
                continue

            assert cell.platform_info is not None

            if cell.platform_info.arch is not None:
                return

            gic = board.interrupt_controllers[0]

            if gic.gicc_base == 0:
                gic.gicc_base = HexInt.validate(gic.gicd_base + 0x10000)
                self.logger.critical(
                    "gicc has not been defined assuming: %d", gic.gicc_base
                )

            if gic.gich_base == 0:
                gic.gich_base = HexInt.validate(gic.gicc_base + 0x20000)
                self.logger.critical(
                    "gicc has not been defined assuming: %d", gic.gich_base
                )

            if gic.gicv_base == 0:
                gic.gicv_base = HexInt.validate(gic.gich_base + 0x10000)
                self.logger.critical(
                    "gicb has not been defined assuming: %d", gic.gicv_base
                )

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
