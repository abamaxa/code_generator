from functools import partial
from pathlib import Path
import subprocess
import json
from tempfile import NamedTemporaryFile
from typing import Iterable, Set

from gen.openapi_adaptor import Question

from .common import TAB, Parser, ParsedItem, extract_code_block, extract_code_blocks

GO_PARSER = Path(__file__).parent.parent.parent / "bin" / "go_parser"


class GoParser(Parser):
    @classmethod
    def parse(cls, code: str) -> list[ParsedItem]:

        with NamedTemporaryFile("w") as f:
            if "package" not in code:
                code = f"package main\n\n{code}"

            f.write(code)
            f.flush()

            # Call the Go executable
            result = subprocess.run([GO_PARSER, f.name], capture_output=True, text=True)

            if result.returncode != 0:
                print("GoParser Error:", result.stdout)
                return None

            # Parse the JSON output
            json_result = json.loads(result.stdout)

            return [ParsedItem(**item) for item in json_result]

    @classmethod
    def extract_source_and_tests(cls, source: str) -> tuple[str, str]:
        raise NotImplementedError()

    @classmethod
    def assemble_new_code(
        cls, package_name: str, responses: Iterable[tuple[str, Question]]
    ) -> str:
        new_code = []
        imports = set()
        already_added = set()

        for response, question in responses:
            found = False
            code_blocks = []

            for _code in extract_code_blocks(response, "go"):
                code_blocks.append(_code)
                _code, _imports = cls.get_code_and_imports(_code, question, already_added)
                if not _code:
                    continue

                found = True
                new_code.append(_code)

                if _imports:
                    imports.update(_imports.split(","))

                break

            if not found:
                new_code.append(f"/* {question.expression} */")
                for _block in code_blocks:
                    new_code.append(f"/* {_block} */")

        new_code.insert(0, cls.make_imports(imports))

        new_code.insert(0, f"package {package_name}")

        new_code = "\n\n".join(new_code)

        new_code += "\n"

        return new_code

    @classmethod
    def get_code_and_imports(cls, code_block, question: Question, already_added: Set[ParsedItem]) -> tuple[str, str]:
        if not code_block.strip():
            return None, None #f"// {question.expression}", ""

        try:
            parsed_go = cls.parse(code_block)
            if parsed_go is None:
                raise ValueError(f"Error parsing code: {question.get_name()}")

            imports = None
            code_item = []
            name = question.get_name()
            lname = name.lower()

            _match_name = partial(cls.match_name, name, lname)

            for item in parsed_go:
                if item.key in already_added:
                    continue

                if _match_name(item.name):
                    code_item.append(item.source)
                    already_added.add(item.key)

                elif item.receiver and _match_name(item.receiver) and question.type_name in ("method", "function"):
                    already_added.add(item.key)

                elif item.name == "import":
                    imports = item.source

            candidates = []
            if not code_item:
                for item in parsed_go:
                    if item.key in already_added:
                        continue

                    if item.type in ("Function", "Method") and item.name != "main":
                        candidates.append(item)

            if len(candidates) == 1:
                already_added.add(candidates[0].key)
                code_item.append(candidates[0].source)         

            if code_item:
                return "\n\n".join(code_item), imports

        except Exception as err:
            print(err)

        #if question.type_name in ("type",):
        #    return None, None

        return None, None

    @classmethod
    def match_name(cls, name, lname, item_name):
        if not item_name:
            return False

        item_name_lower = item_name.lower().replace("_", "")

        if (
            item_name == name or item_name_lower == lname
        ):  # or item_name.lower() == lname[:-1]:
            return True

        if item_name_lower == "new" + lname:
            return True

        return False

    @classmethod
    def extract_go_code_old(cls, code_block):
        code = []
        skip_until = None

        for line in code_block.split("\n"):
            if line.startswith("package main"):
                continue
            elif line.startswith('import "'):
                continue
            elif line.startswith("import ("):
                skip_until = ")"
            elif line.startswith("func main"):
                skip_until = "}"

            if skip_until:
                if line.startswith(skip_until):
                    skip_until = ""

                continue

            code.append(line)

        return "\n".join(code)

    @classmethod
    def make_imports(cls, imports):
        _imports = "\n".join([f'{TAB}"{i}"' for i in sorted(imports)])
        return f"import (\n{_imports}\n)\n"


if __name__ == "__main__":
    code = """
    package main

    import (
        "fmt"
    )

    // Constant for the access denied message.
    // In Go, you would use a typed constant with the `const` keyword.
    const AccessDeniedMsg string = "Access denied, ensure access tokens have been set"

    func main() {
        // Usage of the constant within a function. This simulates using the constant in some context.
        fmt.Println(AccessDeniedMsg) // This will print the access denied message
    }
    """

    results = GoParser.parse(code)

    print(results)
