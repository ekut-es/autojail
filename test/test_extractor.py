import os.path
from autojail.extract import BoardInfoExtractor
from devtools import debug

test_data_folder = os.path.join(os.path.dirname(__file__), "test_data")


def test_parse_jetsonagx():
    iomem_name = os.path.join(test_data_folder, "iomem_jetsonagx")
    extractor = BoardInfoExtractor("", "", "")
    regions = extractor.read_iomem(iomem_name)

    debug(regions)

    assert "System RAM" in regions
    assert "tegra210-i2s.0" in regions
    assert "padctl" in regions
    assert "/xhci@3610000" in regions

    assert regions["System RAM"].physical_start_addr == 0x80000000
    assert regions["System RAM"].size == 0xAAFFFFFF - 0x80000000


def test_parse_iomem():
    iomem_name = os.path.join(test_data_folder, "iomem_jetsontx2")
    extractor = BoardInfoExtractor("", "", "")
    regions = extractor.read_iomem(iomem_name)

    assert "System RAM" in regions
    assert regions["System RAM"].physical_start_addr == 0x80000000
    assert regions["System RAM"].size == 0x6FFFFFFF  # 0x80000000-0xefffffff


def test_parse_raspberrypi2b():
    iomem_name = os.path.join(test_data_folder, "iomem_raspberrypi2b")
    extractor = BoardInfoExtractor("", "", "")
    regions = extractor.read_iomem(iomem_name)

    assert "System RAM" in regions


def test_parse_raspberrypi4b():
    iomem_name = os.path.join(test_data_folder, "iomem_raspberrypi4b")
    extractor = BoardInfoExtractor("", "", "")
    regions = extractor.read_iomem(iomem_name)

    assert "System RAM" in regions
