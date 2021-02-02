from typing import Dict, List, Union

from pydantic import BaseModel

ScriptList = List[str]
CheckList = List[str]
LogList = List[str]


class TestEntry(BaseModel):
    script: ScriptList
    check: CheckList = []
    log: LogList = []


class TestConfig(BaseModel):
    __root__: Dict[str, TestEntry]

    def values(self):
        return self.__root__.values()

    def keys(self):
        return self.__root__.keys()

    def items(self):
        return self.__root__.items()

    def __iter__(self):
        return iter(self.__root__)

    def __getitem__(self, item):
        return self.__root__[item]
