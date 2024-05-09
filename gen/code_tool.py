import asyncio
from os import path, walk
from pathlib import Path
from gen.enums import Language

from gen.openapi_adaptor import call_chat, list_models, ok

COMMENT_STYLES = {
    Language.Python: "Google docstring",
    Language.Typescript: "JSDoc",
    Language.Rust: "Rust",
    Language.Golang: "Go",
}


class CodeTool:
    def __init__(self, language: Language):
        self.language = language

    async def generate_unit_tests(self, code: str, libs: list[str]):
        messages = [
            {
                "role": "system",
                "content": f"You are an expert in {self.language.name} programming.",
            },
            {"role": "user", "content": "Write unit tests for the following code:"},
            ok(),
            {"role": "user", "content": code},
            ok(),
            self.get_comment_style(),
        ]

        if libs:
            messages.extend(
                [
                    {"role": "assistant", "content": "Ok"},
                    {
                        "role": "user",
                        "content": f"Please use this following libraries: {', '.join(libs)}",
                    },
                ]
            )

        return await call_chat(messages)

    async def generate_comments(self, code: str):
        messages = [
            {
                "role": "system",
                "content": f"You are an expert in {self.language.name} programming.",
            },
            {
                "role": "user",
                "content": f"Please re-write the following {self.language.name} code "
                f"adding helpful and varied {COMMENT_STYLES[self.language]} style comments that "
                f"describe the code and its design, "
                "including a description of the parameters to every method and function.",
            },
            {"role": "user", "content": code},
        ]

        return await call_chat(messages)

    async def generate_from_model(self, model: str, libs: list[str] = None):

        messages = [
            {
                "role": "system",
                "content": f"You are an expert in {self.language.name} programming.",
            },
            {
                "role": "user",
                "content": "Please write a class to support persisting the following model:",
            },
            {"role": "assistant", "content": "Ok"},
            {"role": "user", "content": model},
            {"role": "assistant", "content": "Ok"},
            {
                "role": "user",
                "content": "please store the connection in a member variable and include methods to "
                "open and close the database connection",
            },
            {"role": "assistant", "content": "Ok"},
            self.get_comment_style(),
        ]

        if libs:
            messages.extend(
                [
                    ok(),
                    {
                        "role": "user",
                        "content": f"Please use this following libraries: {', '.join(libs)}",
                    },
                ]
            )

        return await call_chat(messages)

    def comment_dir(self, dirname: str, extensions: list[str] = ("ts", "tsx")):

        for root, dirs, files in walk(dirname):
            for f in files:
                ext = f.rsplit(".", 1)[-1]
                if ext not in extensions:
                    continue

                file_path = Path(path.join(root, f))
                self.comment_file(file_path)

    def comment_file(self, file_path: Path):
        code = file_path.read_text()
        if code.startswith("/**"):
            return

        new_code = self.generate_comments(code)
        if len(new_code) < len(code):
            print(f"lost code from {file_path}")
            print(new_code)

        file_path.write_text(new_code)

    def get_comment_style(self) -> dict:
        return {
            "role": "user",
            "content": f"Please add helpful and varied {COMMENT_STYLES[self.language]} style comments "
            f"that describe the code and its design, including a description of the "
            f"parameters to every method and function.",
        }


async def main():

    await list_models(True)

    test_file = Path(__file__).parent.parent / "tests" / "fixtures" / "python_code.py"

    ct = CodeTool(Language.Python)

    await ct.generate_unit_tests(test_file.read_text(), ["pytest"])


if __name__ == "__main__":
    asyncio.run(main())
