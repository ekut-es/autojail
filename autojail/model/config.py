from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel

if TYPE_CHECKING:
    from pydantic.typing import CallableGenerator


class AutojailLogin(str):
    @classmethod
    def __get_validators__(cls) -> "CallableGenerator":
        yield cls.validate

    @classmethod
    def validate(cls, v: str) -> "AutojailLogin":
        v = v.strip()
        if v.startswith("automate:"):
            return cls(v)
        elif v.startswith("ssh:"):
            return cls(v)
        else:  # Default assume ssh connection
            return cls("ssh:" + v)

    @property
    def is_ssh(self) -> bool:
        return self.startswith("ssh:")

    @property
    def is_automate(self) -> bool:
        return self.startswith("automate:")

    @property
    def user(self) -> str:
        if self.is_automate:
            return ""

        user_name = self.split(":")[1]
        if "@" in user_name:
            return user_name.split("@")[0]
        return ""

    @property
    def host(self) -> str:
        host_part = self.split(":")[1]
        if "@" in host_part:
            host_part = host_part.split("@")[1]
            return host_part
        return host_part


class AutojailArch(str):
    @classmethod
    def __get_validators__(cls) -> "CallableGenerator":
        yield cls.validate

    @classmethod
    def validate(cls, v: str) -> "AutojailArch":
        archs = ["ARM", "ARM64"]
        if v not in archs:
            raise ValueError(
                "Only the following architectures are supported atm: "
                + ", ".join(archs)
            )

        return cls(v)


class AutojailConfig(BaseModel):
    name: str
    board: str
    login: AutojailLogin
    arch: AutojailArch
    cross_compile: str
    kernel_dir: str
    jailhouse_dir: str
    uart: Optional[str] = None
    kernel_cmdline: Optional[str] = None
    jailhouse_git: Optional[str] = None
    kernel_git: Optional[str] = None
