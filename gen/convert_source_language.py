from asyncio import gather, run
from dataclasses import dataclass
from os import makedirs, path, walk
from pathlib import Path

from gen.enums import Language
from gen.openapi_adaptor import AIModel, OpenAIModel, Question, ok
from gen.parsers import GoParser, RustParser, ParsedItem
from gen.parsers.common import Parser


extensions = {
    Language.Golang: [".go"],
    Language.Rust: [".rs"],
    Language.Python: [".py"],
    Language.Typescript: [".ts", ".tsx"],
}

markdown_names = {
    Language.Golang: "go",
    Language.Rust: "rust",
    Language.Python: "python",
    Language.Typescript: "typescript",
}


@dataclass
class ParsedCode:
    code_objects: list[ParsedItem]

    @property
    def imports(self):
        imports = [i for i in self.code_objects if i.type == "imports"]
        return ",".join(imports).split(",")


@dataclass
class RustQuestion(Question):
    item: ParsedItem
    code: ParsedCode
    filename: str

    def get_text(self) -> str:
        return f"{self.name}\n\n```rust\n{self.expression}\n```\n"

    def get_name(self) -> str:
        """
        Convert a Rust-style snake_case function name to a Go-style camelCase or PascalCase function name.

        :param rust_function_name: The Rust function name in snake_case.
        :param public_function: If True, converts to PascalCase for exported functions in Go.
                                If False, converts to camelCase for unexported functions.
        :return: The converted function name in Go style.
        """
        components = self.name.split("_")
        if self.name[0].isupper():
            # Convert to PascalCase for exported functions
            return "".join(x.capitalize() for x in components)
        else:
            # Convert to camelCase for unexported functions
            return components[0] + "".join(x.capitalize() for x in components[1:])

    def get_filename(self) -> str:
        return Path(self.filename).stem
    
    @property
    def expression(self) -> str:
        return self.item.source
    
    @property
    def name(self) -> str:
        return self.item.name
    
    @property
    def type_name(self) -> str:
        return self.item.type
    
    def __repr__(self) -> str:
        return self.name


@dataclass
class LanguageConverter:
    source_language: Language
    target_language: Language
    model: AIModel

    async def convert_directory(self, src_dir: str, dest_dir: str, exclude=set[str]):
        from_ext = extensions[self.source_language]
        to_ext = extensions[self.target_language][0]
        tasks = []

        for root, _, files in walk(src_dir, topdown=False):
            for f in files:
                if f == "mod.rs" or f in exclude:
                    continue

                f = path.join(root, f)

                src = Path(f)

                if src.suffix not in from_ext:
                    continue

                dest = Path(f.replace(src_dir, dest_dir).replace(src.suffix, to_ext))

                tasks.extend(self.convert_file(src, dest))

        await gather(*tasks)

    def convert_file(self, src: Path, dest: Path):
        print(f"converting {src} to {dest}")
        if not dest.parent.exists():
            makedirs(dest.parent)

        code = src.read_text()

        package_name = str(src.parent.name)

        source, tests = self.source_parser.extract_source_and_tests(code)

        tasks = []

        if source:
            tasks.append(
                self.convert_source(
                    package_name, source, dest, self.make_source_conversion_messages
                )
            )

        if tests:
            tests_dest = dest.parent / f"{dest.stem}_test{dest.suffix}"

            tasks.append(
                self.convert_source(
                    package_name, tests, tests_dest, self.make_test_conversion_messages
                )
            )

        return tasks

    async def convert_source_simple(self, _, code, dest, conversion_func):
        messages = conversion_func(code)
        new_code, _ = await self.model.call_chat(messages, None)
        if dest:
            dest.write_text(self.extract_code_block(new_code))

        return new_code

    async def convert_source(self, package_name, code, dest, conversion_func):
        tasks = []
        code_objects = self.source_parser.parse(code)
        if code_objects is None:
            raise ValueError(f"Error parsing code. {dest}")

        parsed_code = ParsedCode(code_objects)

        for item in self.source_parser.enumerate_code(code_objects):
            if item.name == "imports":
                continue
            messages = conversion_func(item.source)
            tasks.append(
                self.model.call_chat(
                    messages, RustQuestion(item, parsed_code, dest)
                )
            )

        response = await gather(*tasks)

        new_code = self.target_parser.assemble_new_code(package_name, response)

        if dest:
            dest.write_text(new_code)

        return new_code

    def make_source_conversion_messages(self, code, libs=[]):
        messages = [
            {
                "role": "system",
                "content": f"You are an expert programmer with in depth knowledge of the {self.source_language.name} and {self.target_language.name} programming languages.",
            },
            ok(),
            {
                "role": "user",
                "content": f"I would like you to re-write some source code written {self.source_language.name} to {self.target_language.name}, ensure "
                        f"that the code is well formatted, follows best practices and is uses valid syntax so that can be parsed by the {self.target_language.name} compiler."
            },
            ok(),
            {"role": "user", "content": code},
        ]

        if libs:
            messages.extend(
                [
                    ok(),
                    {
                        "role": "user",
                        "content": f"Please use this following libraries if applicable: {', '.join(self.libs)}",
                    },
                ]
            )

        return messages

    def make_test_conversion_messages(self, code, libs=[]):
        messages = [
            {
                "role": "system",
                "content": f"You are an expert programmer with in depth knowledge of the {self.source_language.name} and {self.target_language.name} programming languages.",
            },
            {
                "role": "user",
                "content": f"Please re-write the following tests written in {self.source_language.name} to {self.target_language.name} "
                f"adding helpful comments that describe the code. "
                "Please convert the entire file, DO NOT leave placeholders for someone else to finish converting the code.",
            },
            ok(),
            {"role": "user", "content": code},
        ]

        if libs:
            messages.extend(
                [
                    ok(),
                    {
                        "role": "user",
                        "content": f"Please use this following libraries if applicable: {', '.join(self.libs)}",
                    },
                ]
            )

        return messages

    @property
    def source_parser(self):
        return self._get_parser(self.source_language)

    @property
    def target_parser(self):
        return self._get_parser(self.target_language)

    def _get_parser(self, lang: Language) -> Parser:
        if lang == Language.Rust:
            return RustParser
        elif lang == Language.Golang:
            return GoParser
        else:
            raise ValueError(f"Unsupported source language {lang}")
