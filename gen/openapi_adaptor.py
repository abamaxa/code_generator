from abc import ABC, abstractmethod
import asyncio
from datetime import datetime
from operator import attrgetter
from os import getenv, makedirs
from pathlib import Path
from time import sleep

from openai import AsyncOpenAI, BadRequestError


# MODEL = getenv("OPENAI_MODEL", "gpt-4-0125-preview")  # "gpt-4-1106-preview")
MODEL = getenv("OPENAI_MODEL", "gpt-3.5-turbo-0125")
ORG_ID = getenv("OPENAI_ORG_ID", "org-4Qf0MN6QYIyYR6nBrtIrGshi")
LOG_DIR = Path(getenv("LOG_DIR", Path(__file__).parent.parent / "responses"))


client = AsyncOpenAI(api_key=getenv("OPENAI_API_KEY"), organization=ORG_ID)


class AIModel(ABC):
    @abstractmethod
    async def list_models(list_all=False):
        pass

    @abstractmethod
    async def call_chat(
        messages: [dict], expr: str = None, trys: int = 3, print_output=False
    ):
        pass


class Question(ABC):
    @abstractmethod
    def get_text(self) -> str:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def get_filename(self) -> str:
        pass


class OpenAIModel(AIModel):
    def __init__(self, name: str, model: str = None, log_dir: str = None) -> None:
        super().__init__()
        self.name = name
        self.model = model or MODEL
        self.log_dir = Path(log_dir or LOG_DIR)

    async def list_models(self, list_all=False):
        response = await client.models.list()
        models = sorted(response.data, key=attrgetter("id"))
        for model in models:
            if list_all or "gpt" in model.id:
                print(model.id)

    async def call_chat(
        self,
        messages: [dict],
        question: Question = None,
        trys: int = 3,
        print_output=False,
    ) -> (str, Question):
        while trys:
            try:
                response = await client.chat.completions.create(
                    model=MODEL,
                    # response_format={ "type": "json_object" },
                    messages=messages,
                )
                break
            except BadRequestError as err:
                print(err)
                raise err

            except Exception as err:
                print(err)
                sleep(1)

            trys -= 1

        return self.extract_results(response, print_output, question)

    def extract_results(self, response, print_output, question) -> (str, Question):
        results = []
        for choice in response.choices or []:
            try:
                content = choice.message.content
                if print_output:
                    print(content)
                results.append(content)
            except Exception as err:
                print(err)
                print(choice)
                raise err

        results = "\n".join(results)

        self.log(question, results)

        return results, question

    def log(self, question: Question, message: str):
        now = datetime.now()
        filename = f"{self.name}-{now.time().isoformat()}-{question.get_filename()}.md"

        filepath = self.log_dir / now.date().isoformat() / filename

        makedirs(filepath.parent, exist_ok=True)

        with open(filepath, "w") as f:
            if question:
                f.write(f"{question.get_text()}\n\n")

            f.write(message)


def system_message(content: str) -> dict:
    return {"role": "system", "content": content}


def user_message(content: str) -> dict:
    return {"role": "user", "content": content}


def assistant_response(content: str) -> dict:
    return {"role": "assistant", "content": content}


def ok() -> dict:
    return {"role": "assistant", "content": "Ok"}


if __name__ == "__main__":
    asyncio.run(OpenAIModel("test").list_models())
