from abc import ABC
from typing import Tuple

from ..model import Board, JailhouseConfig
from ..utils.logging import getLogger


class BasePass(ABC):
    def __init__(self) -> None:
        self.logger = getLogger()

    def __call__(
        self, board: Board, config: JailhouseConfig
    ) -> Tuple[Board, JailhouseConfig]:
        pass

    @property
    def name(self) -> str:
        return self.__class__.__name__
