from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable

from gen.openapi_adaptor import Question


@dataclass(frozen=True)
class ParsedItem:
    name: str
    type: str
    source: str
    receiver: str | None = None

    @property
    def key(self) -> str:
        return "{}||{}||".format(self.name, self.type, self.receiver)


class Parser(ABC):
    @classmethod
    @abstractmethod
    def parse(cls, code: str) -> list[ParsedItem]:
        pass

    @classmethod
    @abstractmethod
    def extract_source_and_tests(cls, source: str) -> tuple[str, str]:
        pass

    @classmethod
    @abstractmethod
    def get_code_and_imports(cls, code_block: str, question: Question) -> tuple[str, str]:
        pass

    @classmethod
    @abstractmethod
    def assemble_new_code(
        cls, package_name: str, responses: Iterable[tuple[str, Question]]
    ) -> str:
        pass

    @classmethod
    @abstractmethod
    def enumerate_code(cls, code: list[ParsedItem]) -> list[str]:
        pass


def extract_code_block(new_source: str, markdown_name: str) -> str:
    code_block = new_source[new_source.find(f"```{markdown_name}") :]
    code_block = code_block[code_block.find("\n") + 1 :]
    return code_block[: code_block.find("```")]


def extract_code_blocks(new_source: str, markdown_name: str) -> Iterable[str]:
    start_marker = f"```{markdown_name}"
    code_block = new_source

    while True:
        start_pos = code_block.find(start_marker)
        if start_pos == -1:
            break   

        code_block = code_block[start_pos :]
        code_block = code_block[code_block.find("\n") + 1 :]
        
        end_pos = code_block.find("```")
        
        yield code_block[: end_pos]

        code_block = code_block[end_pos + 3: ]


TAB = "    "
