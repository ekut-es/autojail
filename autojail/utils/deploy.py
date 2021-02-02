import logging
from pathlib import Path


def deploy_target(connection, bundle_path: Path) -> None:
    logging.info("Deploying to target")
    if not bundle_path.exists():
        raise Exception("Deploy {bundle_path} target does not exist")
    connection.put(str(bundle_path), remote="/tmp")
    with connection.cd("/tmp"):
        connection.run(
            f"sudo tar --overwrite -C / -hxzf {bundle_path.name}",
            in_stream=False,
        )
    connection.run("sudo depmod", in_stream=False, warn=True)
