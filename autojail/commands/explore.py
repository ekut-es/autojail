from pathlib import Path

import numpy
import ruamel.yaml
from hannah_optimizer.aging_evolution import AgingEvolution

from ..config import JailhouseConfigurator
from ..model import Board
from ..model.parameters import (
    GenerateConfig,
    GenerateParameters,
    Partitions,
    ScalarChoice,
)
from ..test import TestRunner
from .base import BaseCommand


class ExploreCommand(BaseCommand):
    """Explore jailhouse configuration space to optimize configuration

    explore
    {--skip-check : Do not statically check generated configs}
    {--p|print-after-all : print cell config after each transformation step}
    """  # noqa

    def handle(self) -> int:
        if not self.autojail_config:
            self.line(f"<error>could not find {self.CONFIG_NAME}</error>")
            return 1

        self.cells_yml_path = Path.cwd() / self.CELLS_CONFIG_NAME

        if not self.cells_yml_path.exists():
            self.line(
                f"<error>{self.cells_yml_path} could not be found</error>"
            )
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

        self.board_info = board_info

        gen_params = GenerateParameters()
        set_params = None

        step = 0

        result = self._run_config(step, set_params, gen_params)

        optimizer = AgingEvolution(
            10,
            1,
            0.1,
            {"test", 0.5},
            gen_params.dict(),
            numpy.random.RandomState(1234),
        )
        for step in range(1, 20):
            set_params = optimizer.ask()
            from devtools import debug

            debug(set_params.flatten())

        return 0

    def _run_config(self, step, set_params, gen_params):
        board_info = self.board_info
        cells_yml_path = self.cells_yml_path
        build_dir = Path.cwd() / "explore" / str(step) / "build"
        deploy_dir = Path.cwd() / "explore" / str(step) / "deploy"

        build_dir.mkdir(exist_ok=True, parents=True)
        deploy_dir.mkdir(exist_ok=True, parents=True)

        self.autojail_config.build_dir = str(build_dir)
        self.autojail_config.deploy_dir = str(deploy_dir)

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
        ret = configurator.write_config(self.autojail_config.build_dir)

        ret = configurator.build_config(
            build_dir, skip_check=self.option("skip-check")
        )

        ret = configurator.deploy(build_dir, deploy_dir,)

        test_jailhouse_config = self.load_jailhouse_config(
            Path("report/generated_cells.yml")
        )
        if not test_jailhouse_config:
            return 1

        test_config = self.load_test_config()
        if not test_config:
            return 1

        automate_context = self.automate_context

        # runner = TestRunner(
        #     self.autojail_config,
        #     board_info,
        #     test_jailhouse_config,
        #     test_config,
        #     automate_context,
        # )

        # runner.run()
