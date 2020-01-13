from invoke import task
from automate.utils import fix_symlinks 

@task
def extract(c, board_id):
    board = c.board(board_id)
    with board.lock():
        with board.connect() as con:
            con.run(f"mkdir -p /tmp/{board_id}_data")
            print("copy /sys")
            con.run(f"sudo cp -r /sys /tmp/{board_id}_data", hide='both', warn=True)

            print("copy /proc")
            con.run(f"sudo cp -r /proc /tmp/{board_id}_data", hide='both', warn=True)
            with con.cd("/tmp"):
                print(f"creating {board_id}_data.tar.gz")
                con.run(f"sudo tar cvzf {board_id}_data.tar.gz {board_id}_data")

            c.run("mkdir -p board_data")
            con.get(f"/tmp/{board_id}_data.tar.gz", "board_data/")

            con.run(f"sudo rm -rf /tmp/{board_id}_data.tar.gz /tmp/{board_id}_data/")
            
            with c.cd("board_data"):
                c.run(f"tar xvzf {board_id}_data.tar.gz")

            fix_symlinks(f"board_data/{board_id}_data")
