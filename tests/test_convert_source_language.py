from pathlib import Path
from unittest.mock import patch

import pytest
from gen.convert_source_language import LanguageConverter, ParsedCode, RustQuestion
from gen.enums import Language
from gen.openapi_adaptor import OpenAIModel
from gen.parsers import RustParser


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.skip
@pytest.mark.asyncio
async def test_convert_folder(tmpdir):
    converter = LanguageConverter(
        Language.Rust, Language.Golang, OpenAIModel("rust-go")
    )

    await converter.convert_directory(str(FIXTURES), str(tmpdir))

    output = tmpdir / "rust_code.go"

    new_code = output.read_text("utf-8")

    assert len(new_code.split("\n")) > 50

    print(new_code)

    test_output = tmpdir / "test_rust_code.go"

    test_code = test_output.read_text("utf-8")

    assert len(test_code.split("\n")) > 50

    print(test_code)


@pytest.mark.skip
@pytest.mark.asyncio
async def test_conversion(tmpdir):
    source_folder = FIXTURES / "services"

    for source_file in source_folder.glob("*.rs"):
        if source_file.name == "mod.rs":
            continue

        new_source, new_tests = await convert_file(tmpdir, source_file, "responses-services")

        assert new_source is not None

        assert new_tests != ""

    print(tmpdir)


@pytest.mark.asyncio
async def test_convert_file(tmpdir):

    source_file = FIXTURES / "services" / "media_store.rs"

    new_source, new_tests = await convert_file(tmpdir, source_file, "services", "responses-services")

    assert new_source is not None

    assert new_tests != ""

    # print(tmpdir)


async def convert_file(tmpdir, source_file: Path, package_name: str, responses_folder_name: str):
    
    responses_folder = FIXTURES / responses_folder_name

    converter_name = "rust-go"

    new_source, new_tests = (None, None)

    async def fake_chat_gpt(messages, question):
        response_map = read_response_folder(responses_folder, converter_name, question)
        if question.name in response_map:
            return response_map[question.name][1], question
        raise ValueError(f"no response for {question.name}")
        # return "", question

    with patch("gen.openapi_adaptor.OpenAIModel.call_chat", side_effect=fake_chat_gpt):
        converter = LanguageConverter(
            Language.Rust, Language.Golang, OpenAIModel(converter_name)
        )

        source, tests = RustParser.extract_source_and_tests(source_file.read_text())

        dest = Path(tmpdir / source_file.name.replace("rs", "go"))

        new_source = await converter.convert_source(
            package_name, source, dest, converter.make_source_conversion_messages
        )

        if tests:
            tests_dest = dest.parent / f"{dest.stem}_test{dest.suffix}"

            new_tests = await converter.convert_source(
                package_name,
                tests,
                tests_dest,
                converter.make_test_conversion_messages,
            )

    return new_source, new_tests


def read_response_folder(folder, converter_name, question):

    assert folder.exists()

    response_files = folder.glob(f"{converter_name}-*-{question.filename.stem}.md")

    response_map = {}

    for response_file in response_files:
        name, original, response = read_response_file(response_file)

        # assert name not in response_map
        if name in response_map:
            if response_map[name][0].strip() != question.expression.strip():
                print(f"WARNING: ignoring duplicate name {name}")
                continue

        response_map[name] = (original, response)

    return response_map


def read_response_file(f):
    data = f.read_text()
    lines = data.split("\n")

    name = lines[0].strip()
    original = []
    response = []
    in_original = False

    for idx, line in enumerate(lines[1:]):
        if line.startswith("```"):
            if not original:
                in_original = True
                continue

            response = lines[idx + 2 :]
            break
        elif line.endswith("```"):
            original.append(line.replace("```", ""))
            response = lines[idx + 2 :]
            break
        elif in_original:
            original.append(line)

    return name, "\n".join(original), "\n".join(response)
