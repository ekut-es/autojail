from typing import Dict, List, Union

from pydantic import BaseModel


class ScriptEntry(BaseModel):
    command: str
    connection: str = "ssh"


ScriptList = List[Union[str, ScriptEntry]]
CheckList = List[str]
LogList = List[str]


class TestEntry(BaseModel):
    script: ScriptList
    check: CheckList = []
    log: LogList = []


class TestConfig(BaseModel):
    reset_script: ScriptList = []
    stop_script: ScriptList = []
    start_script: ScriptList = []
    pre_run_script: ScriptList = []
    post_run_script: ScriptList = []
    tests: Dict[str, TestEntry] = {}
