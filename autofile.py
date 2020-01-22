import logging
from pathlib import Path
import os.path

from invoke import task
from automate.utils import fix_symlinks
from automate.utils.kernel import KernelData
from automate.utils.network import rsync

ROOT_PATH = Path(os.path.dirname(os.path.abspath(__file__)))
JAILHOUSE_REPO = 'https://github.com/siemens/jailhouse.git'
JAILHOUSE_PATH = ROOT_PATH / "jailhouse"
JAILHOUSE_BOARDS = ["jetsontx2"]

@task
def update(c):
    """Update the jailhouse from github"""
    if not JAILHOUSE_PATH.exists():
        c.run(f"git clone {JAILHOUSE_REPO} {JAILHOUSE_PATH}")
    else:
        with c.cd(str(JAILHOUSE_PATH)):
            c.run(f"git pull")

@task
def build(c, board_ids="all", sync_kernel=False):
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
            kernel_data = board.kernel_data("default")
         
            build_cache_path = kernel_data.build_cache_path
         
            if not build_cache_path.exists():
                logging.warning(f"Could not find cached kernel build directory for board {board.id}")
                logging.warning(f"Skipping jailhouse build")
                continue
         
            kernel_path = Path("kernels") / board_id
         
            if not kernel_path.exists() or sync_kernel:
                print("Getting cached kernel build")
                c.run(f"mkdir -p {kernel_path}")
                c.run(f"cp {build_cache_path} kernels/{board.id}")
                with c.cd(f"kernels/{board.id}"):
                    c.run(f"tar xJf {kernel_data.build_cache_name}")
         
            kernel_arch = kernel_data.arch
            kdir =  Path("kernels") / board.id / kernel_data.srcdir
            kdir = os.path.realpath(kdir.absolute())
            dest_dir =  Path("builds") / board.id / "jailhouse"
            cross_compile = cross_compiler.bin_path / cross_compiler.prefix 
         
         
            c.run(f"mkdir -p {dest_dir}")
            c.run(f"rsync -r --delete jailhouse/ {dest_dir}")
            with c.cd(str(dest_dir)):
                c.run(f"rm -rf configs/*/dts") # Currently does not build for many targets
                c.run(f"make CROSS_COMPILE={cross_compile} KDIR={kdir} ARCH={kernel_arch}  V=1")
            
            
    return False
                
            
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
            build_dir = Path("builds") / board_id / "jailhouse"
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
                '/sys/bus/pci/devices/*/config',
                '/sys/bus/pci/devices/*/resource',
                '/sys/devices/system/cpu/cpu*/uevent',
                '/sys/firmware/acpi/tables/APIC',
                '/sys/firmware/acpi/tables/MCFG'
                '/proc/iomem',
                '/proc/cpuinfo',
                '/proc/cmdline',
                '/proc/ioports',
            ]
             
            with board.lock_ctx():
                with board.connect() as con:
                    con.run(f"sudo rm -rf /tmp/{board_id}_data")
                    con.run(f"mkdir -p /tmp/{board_id}_data")
         
                    for file in files:
                        con.run(f"sudo cp --parents {file} /tmp/{board_id}_data/", warn=True)
         
                    with con.cd("/tmp"):
                        print(f"creating {board_id}_data.tar.gz")
                        con.run(f"sudo rm -f {board_id}_data.tar.gz")
                        con.run(f"sudo tar cvzf {board_id}_data.tar.gz {board_id}_data")
             
                    c.run("mkdir -p board_data")
                    print("Getting data")
                    con.get(f"/tmp/{board_id}_data.tar.gz", f"board_data/{board_id}_data.tar.gz")
             
                    con.run(f"sudo rm -rf /tmp/{board_id}_data.tar.gz  /tmp/{board_id}_data/")
                    
            with c.cd("board_data"):
                c.run(f"tar xvzf {board_id}_data.tar.gz")
                
            c.run("chown -R ${USER} board_data/")
            fix_symlinks(f"board_data/{board_id}_data")
