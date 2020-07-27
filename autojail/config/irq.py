from .passes import BasePass

from ..model import IRQChip


class PrepareIRQChipsPass(BasePass):
    def __init__(self):
        self.board = None
        self.config = None

    def __call__(self, board, config):
        self.board = board
        self.config = config

        for cell in self.config.cells.values():
            self._prepare_irqchips(cell)

        return self.board, self.config

    def _prepare_irqchips(self, cell):
        "Splits irqchips that handle more interrupts than are possible in one autojail config entry"

        split_factor = 32 * 4
        new_irqchips = {}

        for name, irqchip in cell.irqchips.items():
            count = 0
            new_name = name
            new_chip = IRQChip(
                address=irqchip.address,
                pin_base=irqchip.pin_base,
                interrupts=[],
            )

            # first GIC has pin_base 0 and only handles SGIs
            # and PPIs, which have ID0-ID31
            current_base = irqchip.pin_base

            for irq in sorted(irqchip.interrupts):
                assert irq >= current_base and "Invalid state detected"

                while irq >= current_base + split_factor:
                    new_irqchips[new_name] = new_chip
                    current_base += split_factor

                    new_chip = IRQChip(
                        address=irqchip.address,
                        pin_base=current_base,
                        interrupts=[],
                    )

                    count += 1
                    new_name = name + "_" + str(count)

                # each chip has four bases: 0 <= i <= 3: current_base + (i*32)
                # since each chip has a bitmap of 4*32 bit integers
                new_chip.interrupts.append(irq)

            new_irqchips[new_name] = new_chip

        cell.irqchips = {}
        for name, chip in new_irqchips.items():
            if len(chip.interrupts) > 0:
                cell.irqchips[name] = chip
