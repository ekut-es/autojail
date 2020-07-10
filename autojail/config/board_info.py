from .passes import BasePass
from ..model import IRQChip, PlatformInfoArm


class TransferBoardInfoPass(BasePass):
    def __init__(self):
        pass

    def _create_irqchips(self, board, config):
        for cell in config.cells.values():
            if cell.irqchips:
                continue

            gic = board.interrupt_controllers[0]

            interrupts = []
            if cell.type == "root":
                interrupts = gic.interrupts

            cell.irqchips["gic"] = IRQChip(
                address=gic.gicd_base, pin_base=32, interrupts=interrupts
            )

    def _create_arm_info(self, board, config):
        for cell in config.cells.values():
            if cell.type != "root":
                continue

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

    # FIXME: should be moved to shmem
    def _create_vpci_base(self, board, config):
        num_interrupts = 5
        used_interrupts = set()

        for cell in config.cells.values():
            for irqchip in cell.irqchips.values():
                for irq in irqchip.interrupts:
                    used_interrupts.add(irq)

        for cell in config.cells.values():
            if cell.vpci_irq_base:
                for i in range(
                    cell.vpci_irq_base, cell.vpci_irq_base + num_interrupts
                ):
                    used_interrupts.add(i)

        for cell in config.cells.values():
            if cell.vpci_irq_base is None:
                for i in range(0, max(used_interrupts) + 2):
                    sentinel = set(range(i, i + num_interrupts))

                    if not (used_interrupts & sentinel):
                        used_interrupts |= sentinel
                        cell.vpci_irq_base = i
                        continue

        for cell in config.cells.values():
            if cell.type == "root":
                for irqchip in cell.irqchips.values():
                    for irq in used_interrupts:
                        if irq not in irqchip.interrupts:
                            irqchip.interrupts.append(irq)

        for name, cell in config.cells.items():
            print(name, cell.vpci_irq_base)

    def __call__(self, board, config):
        self._create_irqchips(board, config)
        self._create_arm_info(board, config)
        self._create_vpci_base(board, config)
