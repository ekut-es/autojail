from typing import Any, List, Union

from dataclasses import dataclass, field
from rich import table, text
from rich.console import Console, ConsoleOptions, RenderResult
from rich.style import Style
from tabulate import tabulate


@dataclass
class Table:
    headers: List[str] = field(default_factory=list)
    content: List[Any] = field(default_factory=list)

    def __str__(self):
        return tabulate(self.content, headers=self.headers, tablefmt="github")

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        tab = table.Table()
        if self.headers:
            for column in self.headers:
                tab.add_column(column)

        for row in self.content:
            tab.add_row(*row)
        yield tab

    def append(self, row) -> None:
        self.content.append(row)


Content = Union["Section", str, Table]


@dataclass
class Section:
    title: str
    content: List[Content] = field(default_factory=list)

    def __str__(self):
        return self._string()

    def _string(self, indent: int = 2) -> str:
        res = "#" * indent + " " + self.title
        res += "\n\n"
        for item in self.content:
            if isinstance(item, Section):
                res += item._string(indent + 1) + "\n"
            else:
                res += str(item) + "\n"
        res += "\n"
        return res

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        yield text.Text(self.title, justify="left", style="bold")
        for item in self.content:
            yield (item)

    def add(self, item: Content) -> None:
        self.content.append(item)


@dataclass
class Report:
    title: str
    sections: List[Section] = field(default_factory=list)

    def __str__(self) -> str:
        res = "# " + self.title + "\n\n"
        for section in self.sections:
            res += str(section)
        return res

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        yield text.Text(self.title, justify="left", style=Style(bold=True))
        for section in self.sections:
            yield section

    def add(self, section) -> None:
        self.sections.append(section)
