from pathlib import Path

from invoke import task
from automate.utils import fix_symlinks 

JAILHOUSE_REPO = 'https://github.com/siemens/jailhouse.git'
JAILHOUSE_PATH = Path("jailhouse")

@task
def update_jailhouse(c):
    """Update the jailhouse from github"""


    if not JAILHOUSE_PATH.exists():
        c.run(f"git clone {JAILHOUSE_REPO} {JAILHOUSE_PATH}")
    else:
        with c.cd(str(JAILHOUSE_PATH)):
            c.run(f"git pull")
    
        
@task
def extract(c, board_id):
    board = c.board(board_id)

    sys_files = [
        '/proc/iomem'
    ]
    
    proc_files = [
        '/proc/iomem',
        '/proc/cpuinfo',
        '/proc/cmdline',
        '/proc/ioports',
    ]
    
    with board.lock():
        with board.connect() as con:
            con.run(f"mkdir -p /tmp/{board_id}_data")
            print("copy /sys")
            con.run(f"sudo cp -r /sys /tmp/{board_id}_data", warn=True)

            print("copy /proc")
            con.run(f"sudo mkdir -p /tmp/{board_id}_data/proc")
            for proc_file in proc_files:
                con.run(f"sudo cp {proc_file} /tmp/{board_id}_data/proc", warn=True)
            with con.cd("/tmp"):
                print(f"creating {board_id}_data.tar.gz")
                con.run(f"sudo tar cvzf {board_id}_data.tar.gz {board_id}_data")

            c.run("mkdir -p board_data")
            print("Getting data")
            con.get(f"/tmp/{board_id}_data.tar.gz", f"board_data/{board_id}_data.tar.gz")

            con.run(f"sudo rm -rf /tmp/{board_id}_data.tar.gz  /tmp/{board_id}_data/")
            
            with c.cd("board_data"):
                c.run(f"tar xvzf {board_id}_data.tar.gz")

            fix_symlinks(f"board_data/{board_id}_data")
