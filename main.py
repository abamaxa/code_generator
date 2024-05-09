import argparse
from asyncio import run

from gen.convert_source_language import LanguageConverter
from gen.enums import Language
from gen.openapi_adaptor import OpenAIModel


async def main():
    parser = argparse.ArgumentParser(description="Language Converter")

    parser.add_argument("src", metavar="SRC", help="Source directory path")
    parser.add_argument("dest", metavar="DEST", help="Destination directory path")
    parser.add_argument(
        "--src-lang",
        type=Language,
        default=Language.Rust,
        choices=list(Language),
        help="Source language (default: Rust)",
    )
    parser.add_argument(
        "--dest-lang",
        type=Language,
        default=Language.Golang,
        choices=list(Language),
        help="Destination language (default: Golang)",
    )
    parser.add_argument(
        "--model-name",
        default="rust-go",
        help="Name of the language model (default: rust-go)",
    )
    parser.add_argument(
        "--model",
        default="gpt-4-0125-preview",
        help="OpenAI model to use (default: gpt-4-0125-preview)",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        default=[],
        help="List of files to exclude",
    )

    args = parser.parse_args()

    converter = LanguageConverter(
        args.src_lang,
        args.dest_lang,
        OpenAIModel(args.model_name, model=args.model),
    )

    await converter.convert_directory(args.src, args.dest, set(args.exclude))


if __name__ == "__main__":
    run(main())
