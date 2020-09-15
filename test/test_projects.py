import filecmp
import os
import shutil
from pathlib import Path

from cleo import CommandTester
from ruamel.yaml import YAML

from autojail.main import AutojailApp

project_folder = os.path.join(os.path.dirname(__file__), "test_data")


def test_init(tmpdir):
    os.chdir(tmpdir)
    application = AutojailApp()
    command = application.find("init")
    tester = CommandTester(command)

    yaml = YAML()

    tester.execute(interactive=False)
    assert os.path.exists(os.path.join(tmpdir, "autojail.yml"))
    with open("autojail.yml") as f:
        data1 = yaml.load(f)

    tester.execute(["-f"], interactive=False)
    assert os.path.exists(os.path.join(tmpdir, "autojail.yml"))
    with open("autojail.yml") as f:
        data2 = yaml.load(f)

    tester.execute(["-f"], interactive=True, inputs="\n\n\n\n\n\n\n\n\n")
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

    tester.execute(
        "-f --arch arm --name jailhouse_test --uart /dev/ttyUSB0",
        interactive=False,
    )
    assert os.path.exists(os.path.join(tmpdir, "autojail.yml"))
    with open("autojail.yml") as f:
        data_test = yaml.load(f)

    assert data_test["name"] == "jailhouse_test"
    assert data_test["arch"] == "ARM"
    assert data_test["uart"] == "/dev/ttyUSB0"

    try:
        import automate  # noqa

        tester.execute("-f -a", interactive=False)
        assert os.path.exists(os.path.join(tmpdir, "autojail.yml"))
    except ModuleNotFoundError:
        pass


def test_simple(tmpdir):
    """tests a simple generation from cells.yml only"""
    os.chdir(tmpdir)
    application = AutojailApp()
    command = application.find("init")
    tester = CommandTester(command)
    tester.execute(interactive=False)

    command = application.find("generate")
    tester = CommandTester(command)
    tester.execute(interactive=False)


def test_config_rpi4_net(tmpdir):
    """ Tests that rpi4_net creates the expected configuration for rpi4_net"""

    os.chdir(tmpdir)
    shutil.copytree(Path(project_folder) / "rpi4_net", "rpi4_net")
    os.chdir("rpi4_net")

    application = AutojailApp()
    command = application.find("generate")
    tester = CommandTester(command)
    tester.execute(interactive=False)

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
    tester.execute(interactive=False)

    assert Path("raspberry-pi4.c").exists()

    assert filecmp.cmp("raspberry-pi4.c", "golden/raspberry-pi4.c")
