import logging
from pathlib import Path
import os.path
import stat

from invoke import task
from automate.utils import fix_symlinks
from automate.utils.kernel import KernelData
from automate.utils.network import rsync

from ruamel.yaml import YAML

ROOT_PATH = Path(os.path.dirname(os.path.abspath(__file__)))
JAILHOUSE_REPO = 'https://github.com/siemens/jailhouse.git'
JAILHOUSE_BRANCH = 'next'
JAILHOUSE_PATH = ROOT_PATH / "jailhouse"
JAILHOUSE_BOARDS = ["jetsontx2"]

autojailhouse_yml_template = r"""
# (automate|ssh)
project_type:

# (automate-id|ssh login)
board_id:

cross_compiler:
    # automate id
    id:
    # absolute path to bin directory
    bin-path:
    prefix:
    cc:
    cxx:
    ld:
    asm:

base_architecture:

# absolute path to kernel build directory containing object files
kernel_build_dir:

# user name to use for login, key authentication required
ssh_login:

# full address of JailHouse git repository to be used
jailhouse_git:

kernel_params:
    # kernel command-line MEM parameter
    mem:
    # kernel command-line VMALLOC parameter
    vmalloc:
"""

def check_project_config(c, autojailhouse_yml) -> bool:
    check_host = lambda host : c.run(f"ping -W 1 -c 1 {host}", hide='both').exited == 0
    valid = True

    if autojailhouse_yml['project_type'] == "automate":
        try:
            c.board(autojailhouse_yml['board_id'])
        except:
            logging.error("Invalid automate board-id")
            valid = False

        try:
            c.compiler(autojailhouse_yml['cross_compiler']['id'])
        except:
            logging.error("Invalid automate compiler-id")
            valid = False

    else:
        if not check_host(autojailhouse_yml['board_id']):
            logging.error("Invalid SSH board host")
            valid = False

        cross_compiler = autojailhouse_yml['cross_compiler']
        cross_compiler_bin_path = Path(cross_compiler['bin_path'])
        if not cross_compiler_bin_path.exists():
            logging.error("Invalid cross-compiler bin path")
            valid = False

        prefix = cross_compiler['prefix']
        if not (cross_compiler_bin_path / (prefix + cross_compiler['cc'])).exists():
            logging.error("Invalid CC compiler")
            valid = False

        if not (cross_compiler_bin_path / (prefix + cross_compiler['cxx'])).exists():
            logging.error("Invalid CXX compielr")
            valid = False

    return valid

def generate_config_automate(c, board_id, autojailhouse_yml):
    """ Generates an initial <autojailhouse.yml> config file using automate """

    autojailhouse_yml['project_type'] = "automate"
    board = c.board(board_id)

    cross_compiler = board.compiler()
    autojailhouse_yml['cross_compiler']['id'] = cross_compiler.id
    autojailhouse_yml['base_architecture'] = str(cross_compiler.machine)

    kernel_data = board.kernel_data("default")
    build_cache_path = kernel_data.build_cache_path
    autojailhouse_yml['kernel_build_dir'] = str(build_cache_path)

    return autojailhouse_yml


@task
def init(c, board_id, kernel_build_dir=None, jailhouse_git=JAILHOUSE_REPO, cross_compiler=None, base_arch=None, ssh_login=None, \
    cross_compiler_prefix=None, cross_compiler_cc='gcc', cross_compiler_cxx='g++', overwrite_existing=False, kernel_mem=None, \
    kernel_vmalloc=None):

    """ Initializes an AutoJailhouse project
    """

    if os.path.exists("autojailhouse.yml") and not overwrite_existing:
        assert(False and "Output file <autojailhouse.yml> already existing")

    yaml = YAML()
    autojailhouse_yml = yaml.load(autojailhouse_yml_template)

    autojailhouse_yml['board_id'] = board_id
    autojailhouse_yml['jailhouse_git'] = jailhouse_git

    kernel = autojailhouse_yml['kernel_params']
    if not kernel_mem:
        assert(False and "Missing kernel parameter MEM")

    kernel['mem'] = kernel_mem
    kernel['vmalloc'] = kernel_vmalloc

    if not kernel_build_dir or not jailhouse_git or not cross_compiler or not base_arch:
        autojailhouse_yml = generate_config_automate(c, board_id, autojailhouse_yml)
    else:
        autojailhouse_yml['project_type'] = "ssh"

        autojailhouse_yml['cross_compiler']['bin_path'] = cross_compiler
        autojailhouse_yml['cross_compiler']['cc'] = cross_compiler_cc

        autojailhouse_yml['cross_compiler']['cxx'] = cross_compiler_cxx
        autojailhouse_yml['cross_compiler']['prefix'] = cross_compiler_prefix

        autojailhouse_yml['base_architecture'] = base_arch

        autojailhouse_yml['kernel_build_dir'] = kernel_build_dir
        autojailhouse_yml['ssh_login'] = ssh_login

    assert(check_project_config(c, autojailhouse_yml) and "Failed to create valid config")
    logging.info("Successfully created autojail project configuration")

    with open("autojailhouse.yml", 'w') as fd:
        yaml.dump(autojailhouse_yml, fd)


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
            logging.error("Git pull failed")
            logging.error("You might wan't to try 'automate-run update --reset' to reset the jailhouse checkout before pulling")
            return -1 
            
        c.run(f"git checkout ${JAILHOUSE_BRANCH}")


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
         
            kernel_path = ROOT_PATH / "kernels" / board_id
         
            if not kernel_path.exists() or sync_kernel:
                print("Getting cached kernel build")
                c.run(f"mkdir -p {kernel_path}")
                c.run(f"cp {build_cache_path} kernels/{board.id}")
                with c.cd(f"kernels/{board.id}"):
                    c.run(f"tar xJf {kernel_data.build_cache_name}")
         
            kernel_arch = kernel_data.arch
            kdir =  ROOT_PATH / "kernels" / board.id / kernel_data.srcdir
            kdir = os.path.realpath(kdir.absolute())
            dest_dir =  ROOT_PATH / "builds" / board.id / "jailhouse"
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
