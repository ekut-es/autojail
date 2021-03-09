from typing import Dict, List

from pydantic import BaseModel, Field

ScriptList = List[str]
CheckDict = Dict[str, List[str]]
LogDict = Dict[str, List[str]]


class TestEntry(BaseModel):
    script: ScriptList
    check: CheckDict = Field(default_factory=dict)
    log: LogDict = Field(default_factory=dict)


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
