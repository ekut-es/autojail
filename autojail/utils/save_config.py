from ipaddress import IPv4Interface, IPv4Network, IPv6Interface, IPv6Network
from pathlib import Path
from typing import Optional

import ruamel.yaml

from ..model.datatypes import (
    ByteSize,
    ExpressionInt,
    HexInt,
    IntegerList,
    JailhouseFlagList,
)
from ..model.jailhouse import JailhouseConfig


def repr_string(representer, data):
    return representer.represent_scalar("tag:yaml.org,2002:str", str(data))


def save_jailhouse_config(
    path: Path, config: Optional[JailhouseConfig]
) -> None:
    if config is not None:
        with path.open("w") as f:
            yaml = ruamel.yaml.YAML()
            yaml.register_class(HexInt)
            yaml.register_class(ByteSize)
            yaml.register_class(IntegerList)
            yaml.register_class(JailhouseFlagList)
            yaml.register_class(ExpressionInt)
            yaml.representer.add_representer(IPv4Interface, repr_string)
            yaml.representer.add_representer(IPv4Network, repr_string)
            yaml.representer.add_representer(IPv6Interface, repr_string)
            yaml.representer.add_representer(IPv6Network, repr_string)

            cells_dict = config.dict(exclude_unset=True, exclude_defaults=True)
            yaml.dump(cells_dict, f)
