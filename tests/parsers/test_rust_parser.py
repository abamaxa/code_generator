from pathlib import Path

import pytest
from gen.parsers.rust import extract_imports, RustParser


FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.mark.skip
def test_rust_expression_finder():
    # Example usage
    test_strings = [
        (
            "impl<'a, Q: Serialize + Sync + Send + 'a> JsonFetcher<'a, YoutubeResponse, Q> for HTTPClient",
            "JsonFetcher",
        ),
        ("struct MyStruct", "MyStruct"),
        ("fn my_function()", "my_function"),
        ("enum MyEnum", "MyEnum"),
        ("const MY_CONST: u32", "MY_CONST"),
        ("trait MyTrait", "MyTrait"),
        ("impl MediaServer", "MediaServer"),
    ]

    for code, expected in test_strings:
        results = RustParser.parse(code)
        assert expected in results
        assert results[expected] == code
        # assert len(imports) == 0


@pytest.mark.skip
def test_parse_rust_file():
    rust_file = FIXTURES / "rust_code.rs"
    code = rust_file.read_text()

    results, imports = RustParser.parse(code)

    expected_keys = ("ACCESS_DENIED_MSG", "HTTPClient", "JsonFetcher", "TextFetcher")

    expected_imports = [
        "get_openai_api_key",
        "ChatGPTRequest",
        "ChatGPTResponse",
        "YoutubeResponse",
        "JsonFetcher",
        "TextFetcher",
        "anyhow",
        "Result",
        "async_trait",
        "ACCEPT",
        "AUTHORIZATION",
        "CONTENT_TYPE",
        "StatusCode",
        "Serialize",
    ]

    assert tuple(sorted(results.keys())) == expected_keys
    assert imports == expected_imports


def test_rust_block_finder():
    import re

    # Regular expression for matching Rust struct, fn, enum, const, trait names, and names in impl blocks with optional pub and async prefixes
    rust_pattern = r"\b(pub\s+)?(async\s+)?(struct|fn|enum|const|trait)\s+([_a-zA-Z][_a-zA-Z0-9]*)|\b(pub\s+)?impl(?:<[^>]+>)?\s+(?:for\s+)?([_a-zA-Z][_a-zA-Z0-9]*)(?:<[^>]+>)?(?:\s+for\s+[_a-zA-Z][_a-zA-Z0-9]*)?"
    # rust_pattern = r'\b(pub\s+)?(async\s+)?(struct|fn|enum|const|trait)\s+([_a-zA-Z][_a-zA-Z0-9]*)|\b(pub\s+)?impl(?:<[^>]+>)?\s+(?:[\w:]+\s+)?for\s+([_a-zA-Z][_a-zA-Z0-9]*)(?:<[^>]+>)?(?:\s+where\s+[_a-zA-Z][_a-zA-Z0-9\s,:=<>+.]*)?'

    # Example usage
    test_strings = [
        "impl<'a, Q: Serialize + Sync + Send + 'a> JsonFetcher<'a, YoutubeResponse, Q> for HTTPClient",
        "pub struct MyStruct",
        "struct MyStruct",
        "pub async fn generate_video_metadatas(path: PathBuf, repo: Repository) -> Result<Option<VideoDetails>, MetaDataError>",
        "async fn do_it()",
        "fn do_it()",
        "pub enum MyEnum",
        "enum MyEnum",
        "pub const MY_CONST: u32",
        "const MY_CONST: u32",
        "pub trait MyTrait",
        "trait MyTrait",
        "pub impl<'a, Q: Serialize + Sync + Send + 'a> JsonFetcher<'a, YoutubeResponse, Q> for HTTPClient",
        "impl MediaServer",
        "impl MediaServer",
        "impl fmt::Display for MetaDataError",
    ]

    for test in test_strings:
        match = re.search(rust_pattern, test)
        if match:
            item_type = match.group(3) if match.group(3) else "impl"
            matched_name = match.group(4) if match.group(4) else match.group(6)

            print(
                f"In '{test}', the matched type is: '{item_type}', name: '{matched_name}'"
            )
        else:
            pytest.fail(f"No match found in '{test}'")


def test_extract_imports():
    rust_code = """
    use sqlx::migrate::{
        MigrateDatabase, 
        MigrateError, Migrator
    };
    use sqlx::sqlite::{SqlitePool, SqliteRow};
    use std::path;
    """

    expected_output = [
        "MigrateDatabase",
        "MigrateError",
        "Migrator",
        "SqlitePool",
        "SqliteRow",
        "path",
    ]

    assert extract_imports(rust_code) == expected_output


def test_rust_parser():
    rust_file = FIXTURES / "services"

    for rust_file in rust_file.glob("*.rs"):
        if rust_file.name == "mod.rs":
            continue

        code = rust_file.read_text()

        results = RustParser.parse(code)

        assert len(results) > 0


def test_extract_source_and_tests():
    rust_code = FIXTURES / "rust_code.rs"

    source, tests = RustParser.extract_source_and_tests(rust_code.read_text())

    assert source
    assert tests


def test_deconstruction():

    #rust_code = FIXTURES / "message_exchange.rs"
    rust_code = FIXTURES / "services" / "media_store.rs"

    source, _ = RustParser.extract_source_and_tests(rust_code.read_text())

    results = RustParser.parse(source)

    impls = [item for item in results if item.type == "impl"]

    questions = []

    for impl in impls:
        methods = [item for item in results if item.receiver == impl.name]

        template = "{}\n\n{} {{\n\n{}\n\n}}"

        types = {m.type for m in methods}

        first_line = impl.source[: impl.source.find("{")].strip()

        struct = [item for item in results if item.name == impl.name and item.type == "struct"][0]

        for method in methods:
            question = template.format(
                first_line,
                method.source,
            )

            questions.append({"question": question, "struct": struct.source})
    
    print(questions)