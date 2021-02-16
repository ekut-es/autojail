import filecmp
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
from cleo import CommandTester
from ruamel.yaml import YAML

from autojail.main import AutojailApp

project_folder = os.path.join(os.path.dirname(__file__), "test_data")
autojail_root_folder = Path(__file__).parent.parent
qemu_scripts_folder = (autojail_root_folder / "scripts").resolve()
qemu_download_folder = (autojail_root_folder / "downloads" / "qemu").resolve()


def test_init(tmpdir):
    os.chdir(tmpdir)
    application = AutojailApp()
    command = application.find("init")
    tester = CommandTester(command)

    yaml = YAML()

    assert tester.execute(interactive=False) == 0
    assert os.path.exists(os.path.join(tmpdir, "autojail.yml"))
    with open("autojail.yml") as f:
        data1 = yaml.load(f)

    assert tester.execute(["-f"], interactive=False) == 0
    assert os.path.exists(os.path.join(tmpdir, "autojail.yml"))
    with open("autojail.yml") as f:
        data2 = yaml.load(f)

    assert (
        tester.execute(["-f"], interactive=True, inputs="\n\n\n\n\n\n\n\n\n")
        == 0
    )
    assert os.path.exists(os.path.join(tmpdir, "autojail.yml"))
    with open("autojail.yml") as f:
        data3 = yaml.load(f)

    assert data1["name"] == data2["name"] == data3["name"]
    assert data1["arch"] == data2["arch"] == data3["arch"]
    assert (
        data1["jailhouse_dir"]
        == data2["jailhouse_dir"]
        == data3["jailhouse_dir"]
    )
    assert (
        data1["cross_compile"]
        == data2["cross_compile"]
        == data3["cross_compile"]
    )

    assert (
        tester.execute(
            "-f --arch arm --name jailhouse_test --uart /dev/ttyUSB0",
            interactive=False,
        )
        == 0
    )
    assert os.path.exists(os.path.join(tmpdir, "autojail.yml"))
    with open("autojail.yml") as f:
        data_test = yaml.load(f)

    assert data_test["name"] == "jailhouse_test"
    assert data_test["arch"] == "ARM"
    assert data_test["uart"] == "/dev/ttyUSB0"

    try:
        import automate  # noqa

        assert tester.execute("-f -a", interactive=False) == 0
        assert os.path.exists(os.path.join(tmpdir, "autojail.yml"))
    except ModuleNotFoundError:
        pass


@pytest.mark.xfail
def test_simple(tmpdir):
    """tests a simple generation from cells.yml only"""
    os.chdir(tmpdir)
    application = AutojailApp()
    command = application.find("init")
    tester = CommandTester(command)
    assert tester.execute(interactive=False) == 0

    cells_path = Path(project_folder) / "test_cells.yml"
    shutil.copy(cells_path, Path(tmpdir) / "cells.yml")

    application = AutojailApp()
    command = application.find("generate")
    tester = CommandTester(command)
    assert tester.execute(interactive=False, args="--generate-only") == 0


def test_config_rpi4_net(tmpdir):
    """ Tests that rpi4_net creates the expected configuration for rpi4_net"""

    os.chdir(tmpdir)
    shutil.copytree(Path(project_folder) / "rpi4_net", "rpi4_net")
    os.chdir("rpi4_net")

    application = AutojailApp()
    command = application.find("generate")
    tester = CommandTester(command)

    assert (
        tester.execute(interactive=False, args="--skip-check --generate-only")
        == 0
    )

    assert Path("rpi4-net.c").exists()
    assert Path("rpi4-net-guest.c").exists()

    assert filecmp.cmp("rpi4-net.c", "golden/rpi4-net.c")
    assert filecmp.cmp("rpi4-net-guest.c", "golden/rpi4-net-guest.c")


def test_config_rpi4_default(tmpdir):
    """ Tests that rpi4_default creates the expected configuration"""

    os.chdir(tmpdir)
    shutil.copytree(Path(project_folder) / "rpi4_default", "rpi4_default")
    os.chdir("rpi4_default")

    application = AutojailApp()
    command = application.find("generate")
    tester = CommandTester(command)

    assert (
        tester.execute(interactive=False, args="--skip-check --generate-only")
        == 0
    )
    assert Path("raspberry-pi4.c").exists()

    assert filecmp.cmp("raspberry-pi4.c", "golden/raspberry-pi4.c")


def test_config_rpi4_fixed_pci_mmconfig_base(tmpdir):
    """ Tests that rpi4_fixed_pci_mmconfig_base creates the expected configuration"""

    os.chdir(tmpdir)
    shutil.copytree(
        Path(project_folder) / "rpi4_fixed_pci_mmconfig_base",
        "rpi4_fixed_pci_mmconfig_base",
    )
    os.chdir("rpi4_fixed_pci_mmconfig_base")

    application = AutojailApp()
    command = application.find("generate")
    tester = CommandTester(command)

    assert (
        tester.execute(interactive=False, args="--skip-check --generate-only")
        == 0
    )
    assert Path("raspberry-pi4.c").exists()

    assert filecmp.cmp("raspberry-pi4.c", "golden/raspberry-pi4.c")


def prepare_qemu_scripts():
    def ensure_executable(script_path: Path):
        curr_mode = script_path.stat().st_mode
        if not (curr_mode & stat.S_IXUSR):
            script_path.chmod(curr_mode | stat.S_IXUSR)

    ensure_executable(qemu_scripts_folder / "start_qemu.sh")
    ensure_executable(qemu_scripts_folder / "stop_qemu.sh")


@pytest.mark.skipif(
    not shutil.which("qemu-system-aarch64")
    or not shutil.which("aarch64-linux-gnu-gcc"),
    reason="Requires qemu-system-aarch64 and aarch64-linux-gnu-gcc",
)
def test_config_qemu(tmpdir):
    """ Tests that rpi4_fixed_pci_mmconfig_base creates the expected configuration"""

    os.chdir(tmpdir)
    shutil.copytree(
        Path(project_folder) / "qemu_net", "qemu_net",
    )
    os.chdir("qemu_net")
    tmp_proj_dir = Path(tmpdir) / "qemu_net"

    clone_command = [
        "git",
        "clone",
        "--branch",
        "next",
        "https://github.com/siemens/jailhouse.git",
    ]
    subprocess.run(clone_command, check=True)

    os.symlink(
        qemu_download_folder / "linux-jailhouse-images" / "build-full",
        "kernel",
        target_is_directory=True,
    )

    def generate_script(name):
        script_path = tmp_proj_dir / name
        assert not script_path.exists()

        script_path.write_text(
            f"""#!/bin/bash
{qemu_scripts_folder / name}
"""
        )

        script_path.chmod(stat.S_IRWXU)

    generate_script("start_qemu.sh")
    generate_script("stop_qemu.sh")

    prepare_qemu_scripts()

    application = AutojailApp()
    extract = application.find("extract")
    extract_tester = CommandTester(extract)

    assert (
        extract_tester.execute(args=f"--cwd {tmp_proj_dir}", interactive=False)
        == 0
    )

    generate = application.find("generate")
    generate_tester = CommandTester(generate)
    assert generate_tester.execute(interactive=False) == 0

    assert Path("root-cell.c").exists()
    assert Path("guest.c").exists()
    assert Path("guest1.c").exists()

    test = application.find("generate")
    test_tester = CommandTester(test)
    assert test_tester.execute(interactive=False) == 0
