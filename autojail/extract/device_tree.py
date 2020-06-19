import fdt


class DeviceTreeExtractor:
    def __init__(self, dtb_file):
        self.fdt = fdt.parse_dtb(dtb_file)
