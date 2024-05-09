from json import loads as load_json, dump as write_json
from os import path, walk
from traceback import print_exc

from gen.openapi_adaptor import (
    call_chat,
    assistant_response,
    system_message,
    user_message,
)


def comment_dir(dirname: str, extensions: [str] = ("mkv", "avi", "mp4", "webm")):
    batch = []
    results = []
    try:
        for root, dirs, files in walk(dirname):
            for f in files:
                ext = f.rsplit(".", 1)[-1].lower()
                if ext not in extensions:
                    continue

                file_path = path.join(root, f)
                file_path = file_path[len(dirname) :]
                if file_path.startswith(path.sep):
                    file_path = file_path[1:]

                batch.append(file_path)

                if len(batch) > 10:
                    results.extend(parse_name(batch))
                    batch = []

        if batch:
            results.extend(parse_name(batch))

    except Exception as error:
        print_exc()
        print(error)

    finally:
        with open("results.json", "w") as f:
            write_json(results, f, indent=2)


def parse_name(file_paths: [str]):
    messages = [
        system_message(
            "Parse Series Title, Season, Episode and Episode Title of TV "
            "series from a file name, giving the response as machine readable JSON list."
        ),
        user_message(
            "Only Fools and Horses/Specials/S00E03 - Diamonds Are for Heather.mkv"
            "Line Of Duty/Line Of Duty S02E02.mp4"
            "Your a boat john [jLKJOL8&*UYG].webm"
        ),
        assistant_response(
            """
        [
            {
              "series_title": "Only Fools and Horses",
              "season": "Specials",
              "episode": "3",
              "episode_title": "Diamonds Are Heather"
            },
            {
                "series_title": "Line Of Duty",
                "season": "2",
                "episode": "2",
                "episode_title": ""
            },
            {
                "series_title": "You are a boat John",
                "season": "",
                "episode": "",
                "episode_title": ""
            }
        ]"""
        ),
        user_message("\n".join(file_paths)),
    ]

    response = call_chat(messages)

    return load_json(strip_file_paths(response))


def strip_file_paths(response: str) -> str:
    lines = response.strip().split("\n")
    new_lines = []

    for line in lines:
        line = line.strip()
        if line and line[0] in ("{", "}", '"'):
            if line == "}":
                line = "},"

            new_lines.append(line)

    new_lines[-1] = "}"

    new_lines = "\n".join(new_lines)

    return f"[\n{new_lines}\n]"


if __name__ == "__main__":
    comment_dir("/Users/chris2/Movies")
