import itertools
import re
import subprocess
import json
import sys
from tempfile import NamedTemporaryFile
from typing import Iterable

from gen.openapi_adaptor import Question

from .common import Parser, ParsedItem


class RustParser(Parser):
    @classmethod
    def parse(cls, code) -> list[ParsedItem]:
        with NamedTemporaryFile("w") as f:
            f.write(code)
            f.flush()

            return parse_rust_file(f.name)

    @classmethod
    def extract_source_and_tests(cls, source: str) -> tuple[str, str]:
        lines = source.split("\n")

        source_lines = []
        test_lines = []

        in_tests = False
        skip_next = False

        for line in lines:
            if skip_next:
                skip_next = False
                continue

            if line.startswith("#[cfg(test)]"):
                skip_next = True
                in_tests = True
                continue

            if in_tests:
                if line.startswith("}"):
                    in_tests = False
                    continue

                # assume tests are at the end of the file
                test_lines.append(line)
            else:
                source_lines.append(line)

        return "\n".join(source_lines), "\n".join(test_lines)

    @classmethod
    def get_code_and_imports(cls, code_block: str, question: Question) -> tuple[str, str, set[ParsedItem]]:
        raise NotImplementedError()

    @classmethod
    def assemble_new_code(
        cls, package_name: str, responses: Iterable[tuple[str, Question]]
    ) -> str:
        raise NotImplementedError()
    
    @classmethod
    def enumerate_code(cls, code: list[ParsedItem]) -> Iterable[ParsedItem]:
        impls = [item for item in code if item.type == "impl"]

        impls = sorted(impls, key=lambda x: x.name)

        processed = set()

        template = "{}\n\n{} {{\n\n{}\n\n}}"

        for item in code:
            if item.type == "struct":
                processed.add(item.key)
                yield item

        for _, impl_group in itertools.groupby(impls, key=lambda x: x.name):

            impl_group = list(impl_group)

            for item in impl_group:
                processed.add(item.key)

            if len(impl_group) > 1:
                for impl in impl_group:
                    if " for " not in impl.name:
                        break
            else:
                impl = impl_group[0]

            first_line = impl.source[: impl.source.find("{")].strip()
            name = impl.name.split(" ")[0]

            struct = [item for item in code if item.name == name and item.type == "struct"]
            if not struct:
                continue
            
            struct = struct[0]
        
            for item in code:
                if item.type == "impl" or item.receiver != impl.name:
                    continue

                if item.key in processed:
                    continue

                processed.add(item.key)

                if item.receiver == impl.name:
                    yield ParsedItem(
                        name=item.name,
                        type=item.type,
                        source=template.format(
                            struct.source,
                            first_line,
                            item.source,
                        )
                    )

                else:
                    yield impl

        for item in code:
            if item.key not in processed:
                yield item  
            

def parse_rust_file(file_path):
    result = subprocess.run(
        ["cargo", "run", "--", file_path], capture_output=True, text=True
    )
    if result.returncode != 0:
        print("{}Error in parsing:", result.stderr)
        return None

    json_results = json.loads(result.stdout)

    imports = []
    clean_results = []

    for item in json_results:
        if item["type"] == "use":
            imports.extend(extract_imports(item["source"]))
        else:
            clean_results.append(item)

    clean_results = [ParsedItem(**item) for item in clean_results]

    clean_results.append(
        ParsedItem(name="imports", type="imports", source=",".join(imports))
    )

    return clean_results


def extract_imports(code):
    # Regular expression pattern to match Rust use statements
    pattern = r"use\s+[\w:]*::\{([^}]*)\};|use\s+[\w:]*::(\w+);"
    matches = re.findall(pattern, code)

    # Extract imported items
    imports = []
    for match in matches:
        # If the import is a single item
        if match[1]:
            imports.append(match[1])
        # If the import is a list of items
        else:
            items = match[0].split(",")
            imports.extend([item.strip() for item in items])

    return imports


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python parse_rust.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    module_objects = parse_rust_file(file_path)

    for item in module_objects:
        print(item)
