import logging
import os.path
from pathlib import Path

from automate.utils import fix_symlinks
from automate.utils.network import rsync
from invoke import task

ROOT_PATH = Path(os.path.dirname(os.path.abspath(__file__)))
JAILHOUSE_REPO = "https://github.com/siemens/jailhouse.git"
JAILHOUSE_COMMIT = "master"  # GIT branch or sha or tag to use
JAILHOUSE_PATH = ROOT_PATH / "jailhouse"
JAILHOUSE_BOARDS = ["jetsontx2", "raspberrypi4b-jh1"]


@task
def update(c, reset=False):
    """Update the jailhouse from github"""
    if not JAILHOUSE_PATH.exists():
        c.run(f"git clone {JAILHOUSE_REPO} {JAILHOUSE_PATH}")

    with c.cd(str(JAILHOUSE_PATH)):
        if reset:
            c.run("git reset --hard")
        try:
            c.run("git pull")
        except Exception as e:
            logging.fatal("Git pull failed")
            logging.fatal(
                "You might wan't to try 'automate-run update --reset' to reset the jailhouse checkout before pulling"
            )
            logging.info("Error: %s", str(e))
            return -1

        c.run(f"git checkout '{JAILHOUSE_COMMIT}'")


@task
def build(c, board_ids="all", sync_kernel=False, ignore_dtb=False):
    "Build jailhouse hypervisor and kernel module for target system"
    if board_ids == "all":
        board_ids = JAILHOUSE_BOARDS
    else:
        board_ids = board_ids.split(",")

    with c.cd(str(ROOT_PATH)):
        c.run("mkdir -p builds")
        c.run("mkdir -p kernels")

        for board_id in board_ids:
            board = c.board(board_id)
            cross_compiler = board.compiler()

            kernel_name = "default"
            for kernel_desc in board.os.kernels:
                if kernel_desc.name == "jailhouse":
                    kernel_name = "jailhouse"

            kernel_data = board.kernel_data(kernel_name)

            build_cache_path = kernel_data.build_cache_path

            if not build_cache_path.exists():
                logging.warning(
                    f"Could not find cached kernel build directory for board {board.id} in {str(build_cache_path)} "
                )
                logging.warning("Skipping jailhouse build")
                continue

            kernel_path = ROOT_PATH / "kernels" / board_id / kernel_name

            if not kernel_path.exists() or sync_kernel:
                print("Getting cached kernel build")
                c.run(f"mkdir -p {kernel_path}")
                c.run(
                    f"cp {build_cache_path} kernels/{board.name}/{kernel_name}"
                )
                with c.cd(f"kernels/{board.id}/{kernel_name}"):
                    c.run(f"tar xJf {kernel_data.build_cache_name}")

            kernel_arch = kernel_data.arch
            kdir = (
                ROOT_PATH
                / "kernels"
                / board.name
                / kernel_name
                / kernel_data.srcdir
            )
            kdir = os.path.realpath(kdir.absolute())
            dest_dir = ROOT_PATH / "builds" / board.name / "jailhouse"
            cross_compile = cross_compiler.bin_path / cross_compiler.prefix

            c.run(f"mkdir -p {dest_dir}")
            c.run(f"rsync -r --delete jailhouse/ {dest_dir}")
            with c.cd(str(dest_dir)):

                result = c.run(
                    f"make CROSS_COMPILE={cross_compile} KDIR={kdir} ARCH={kernel_arch}  V=1",
                    warn=True,
                )

                if result.return_code != 0:
                    logging.error("Could not build with device trees")
                    if not ignore_dtb:
                        logging.error("to retry without dtbs try --ignore-dtb")
                        return result.return_code

                    logging.error("retrying build without device trees")

                    c.run(
                        "rm -rf configs/*/dts"
                    )  # Currently does not build for many targets

                    result = c.run(
                        f"make CROSS_COMPILE={cross_compile} KDIR={kdir} ARCH={kernel_arch}  V=1",
                        warn=True,
                    )


@task
def deploy(c, board_ids="all"):
    "Install the built jailhouse hypervisor and kernel module on the board"
    if board_ids == "all":
        board_ids = JAILHOUSE_BOARDS
    else:
        board_ids = board_ids.split(",")

    with c.cd(str(ROOT_PATH)):
        for board_id in board_ids:
            board = c.board(board_id)
            build_dir = ROOT_PATH / "builds" / board_id / "jailhouse"
            with board.connect() as con:
                rsync(con, str(build_dir), str(board.rundir))

                with con.cd(str(board.rundir / "jailhouse")):
                    con.run("sudo cp hypervisor/jailhouse.bin /lib/firmware")


@task
def extract(c, board_ids="all"):
    "Extract board information"
    if board_ids == "all":
        board_ids = JAILHOUSE_BOARDS
    else:
        board_ids = board_ids.split(",")

    with c.cd(str(ROOT_PATH)):
        for board_id in board_ids:
            board = c.board(board_id)

            files = [
                "/sys/bus/pci/devices/*/config",
                "/sys/bus/pci/devices/*/resource",
                "/sys/devices/system/cpu/cpu*/uevent",
                "/sys/firmware/acpi/tables/APIC",
                "/sys/firmware/acpi/tables/MCFG",
                "/sys/firmware/devicetree",
                "/proc/iomem",
                "/proc/cpuinfo",
                "/proc/cmdline",
                "/proc/ioports",
            ]

            with board.lock_ctx():
                with board.connect() as con:
                    con.run(f"sudo rm -rf /tmp/{board_id}")
                    con.run(f"mkdir -p /tmp/{board_id}")

                    for file in files:
                        con.run(
                            f"sudo cp -r --parents {file} /tmp/{board_id}",
                            warn=True,
                        )

                    with con.cd("/tmp"):
                        print(f"creating {board_id}.tar.gz")
                        con.run(f"sudo rm -f {board_id}.tar.gz")
                        con.run(f"sudo tar cvzf {board_id}.tar.gz {board_id}")

                    c.run("mkdir -p board_data")
                    print("Getting data")
                    con.get(
                        f"/tmp/{board_id}.tar.gz",
                        f"board_data/{board_id}.tar.gz",
                    )

                    con.run(
                        f"sudo rm -rf /tmp/{board_id}.tar.gz  /tmp/{board_id}/"
                    )

            with c.cd("board_data"):
                c.run(f"tar xvzf {board_id}.tar.gz")

            c.run("chown -R ${USER} board_data/")
            c.run("chmod -R ug+wr board_data")
            fix_symlinks(f"board_data/{board_id}")


@task
def pre_commit(c):
    "Installs pre commit hooks"
    root_path = Path(os.path.dirname(os.path.abspath(__file__)))
    with c.cd(str(root_path)):
        c.run("pre-commit install")


@task
def build_kernels(c, config_name="jailhouse"):
    "Build kernel configs for jailhouse"

    for board_name in JAILHOUSE_BOARDS:
        board = c.board(board_name)
        for kernel in board.os.kernels:
            if kernel.name == config_name:
                kernel_builder = board.builder(
                    "kernel", f"kernels/{board_name}/{config_name}"
                )
                kernel_builder.configure(config_name)
                kernel_builder.build()
                kernel_builder.install()
                kernel_builder.deploy()
