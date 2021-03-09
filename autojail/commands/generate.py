from pathlib import Path

import ruamel.yaml

from ..config import JailhouseConfigurator
from ..model import Board
from ..model.parameters import (
    GenerateConfig,
    GenerateParameters,
    Partitions,
    ScalarChoice,
)
from .base import BaseCommand


class GenerateCommand(BaseCommand):
    """Generate the Jailhouse configurations

    generate
        {--p|print-after-all : print cell config after each transformation step}
        {--skip-check : Do not statically check generated configs}
        {--target : Deploy generated configs to target board}
        {--generate-only : Do not attempt to build anything}
        {--generate-params=? : Generate parameters for explore. Filename defaults to explore-params.yml}
        {--set-params=? : Set parameters from file. Filename defaults to set-params.yml}
    """

    def handle(self) -> int:
        if not self.autojail_config:
            self.line(f"<error>could not find {self.CONFIG_NAME}</error>")
            return 1

        cells_yml_path = Path.cwd() / self.CELLS_CONFIG_NAME

        if not cells_yml_path.exists():
            self.line(f"<error>{cells_yml_path} could not be found</error>")
            return 1

        board_yml_path = Path.cwd() / self.BOARD_CONFIG_NAME
        if not board_yml_path.exists():
            self.line(f"<error>{board_yml_path} could not be found</error>")
            self.line("Please run <comment>automate extract</comment> first")
            return 1

        with board_yml_path.open() as f:
            yaml = ruamel.yaml.YAML()
            board_dict = yaml.load(f)
            board_info = Board(**board_dict)

        set_params = None
        if self.option("set-params"):
            params_yml_path = self.option("set-params")

            if params_yml_path == "null":
                params_yml_path = "set-params.yml"

            params_yml_path = Path(params_yml_path)
            if not params_yml_path.exists():
                self.line(f"<error>{params_yml_path} could not be found</erro>")
                return 1

            with params_yml_path.open() as f:
                yaml = ruamel.yaml.YAML()
                params_dict = yaml.load(f)
                set_params = GenerateConfig(**params_dict)

        gen_params = None
        if self.option("generate-params"):
            gen_params = GenerateParameters()

        configurator = JailhouseConfigurator(
            board_info,
            self.autojail_config,
            print_after_all=self.option("print-after-all"),
            context=self.automate_context,
            set_params=set_params,
            gen_params=gen_params,
        )
        configurator.read_cell_yml(str(cells_yml_path))
        configurator.prepare()

        if gen_params:
            gen_params_yml_path = self.option("generate-params")
            if gen_params_yml_path == "null":
                gen_params_yml_path = "explore-params.yml"

            gen_params_yml_path = Path(gen_params_yml_path)
            with gen_params_yml_path.open("w") as f:
                yaml = ruamel.yaml.YAML()
                yaml.register_class(ScalarChoice)
                yaml.register_class(Partitions)
                yaml.register_class(GenerateParameters)
                yaml.dump(gen_params.dict(), f)

        ret = configurator.write_config(self.autojail_config.build_dir)

        if ret or self.option("generate-only"):
            if ret:
                configurator.report()
            return ret

        ret = configurator.build_config(
            self.autojail_config.build_dir, skip_check=self.option("skip-check")
        )
        if ret:
            configurator.report()
            return ret

        ret = configurator.deploy(
            self.autojail_config.build_dir,
            self.autojail_config.deploy_dir,
            target=self.option("target"),
        )
        configurator.report()

        return ret
