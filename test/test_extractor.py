import os.path
import shutil
import tarfile
from pathlib import Path

import pytest
from cleo import CommandTester
from devtools import debug

from autojail.extract import BoardInfoExtractor, DeviceTreeExtractor
from autojail.main import AutojailApp

test_data_folder = os.path.join(os.path.dirname(__file__), "test_data")


@pytest.fixture()
def test_project(tmpdir_factory):
    source_path = os.path.join(test_data_folder, "test_project")
    target_path = os.path.join(
        tmpdir_factory.mktemp("test_project"), "test_project"
    )
    shutil.copytree(source_path, target_path)
    return target_path


def test_parse_jetsonagx():
    iomem_name = os.path.join(test_data_folder, "iomem_jetsonagx")
    extractor = BoardInfoExtractor("jetsonagx", "jetsonagx", "")
    regions = extractor.read_iomem(iomem_name)

    debug(regions)

    assert "System RAM" in regions
    assert "tegra210-i2s.0" in regions
    assert "padctl" in regions
    assert "/xhci@3610000" in regions

    assert regions["System RAM"].physical_start_addr == 0x80000000
    assert regions["System RAM"].size == 0xAAFFFFFF - 0x80000000 + 1


def test_parse_iomem():
    iomem_name = os.path.join(test_data_folder, "iomem_jetsontx2")
    extractor = BoardInfoExtractor("jetsontx2", "jetsontx2", "")
    regions = extractor.read_iomem(iomem_name)

    assert "System RAM" in regions
    assert regions["System RAM"].physical_start_addr == 0x80000000
    assert regions["System RAM"].size == 0x70000000  # 0x80000000-0xefffffff


def test_parse_raspberrypi2b():
    iomem_name = os.path.join(test_data_folder, "iomem_raspberrypi2b")
    extractor = BoardInfoExtractor("rpi2b", "rpi2b", "")
    regions = extractor.read_iomem(iomem_name)

    assert "System RAM" in regions


def test_parse_raspberrypi4b():
    iomem_name = os.path.join(test_data_folder, "iomem_raspberrypi4b")
    extractor = BoardInfoExtractor("rpi4b", "rpi4b", "")
    regions = extractor.read_iomem(iomem_name)

    assert "System RAM" in regions


def test_parse_getconf():
    getconf_name = Path(os.path.join(test_data_folder, "getconf_x86"))
    extractor = BoardInfoExtractor("x86", "x6", "")
    pagesize = extractor.read_getconf_out(getconf_name)
    assert pagesize == 4096


def test_device_tree(tmpdir):
    devicetree_name = Path(os.path.join(test_data_folder, "device-tree.tar.gz"))

    with tarfile.open(devicetree_name) as tar_file:
        tar_file.extractall(tmpdir)

    extractor = DeviceTreeExtractor(os.path.join(tmpdir, "device-tree"))

    extractor.run()

    alias_pairs = [
        ("uart0", "/soc/serial@7e201000"),
        ("mailbox", "/soc/mailbox@7e00b880"),
    ]

    for alias, path in alias_pairs:
        assert extractor.aliases[alias] == path

    assert extractor.stdout_path == "serial0"


def test_extract_command(test_project):
    os.chdir(test_project)
    application = AutojailApp()
    command = application.find("extract")
    tester = CommandTester(command)

    tester.execute("-b board_data")
