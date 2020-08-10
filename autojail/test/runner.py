from pathlib import Path
from typing import Union

from ruamel.yaml import YAML

from ..model.test import TestConfig
from ..utils.logging import getLogger


class TestRunner:
    def __init__(self, config: Union[Path, str]) -> None:
        config = Path(config)

        with config.open("r") as config_file:
            yaml = YAML()
            config_dict = yaml.load(config_file)
            self.config = TestConfig(**config_dict)

        self.logger = getLogger()

    def run(self) -> None:
        self.logger.info("Executing tests")
        from ..utils import debug

        debug(self.config)
