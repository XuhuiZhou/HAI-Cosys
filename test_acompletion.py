import asyncio

from litellm import acompletion
from pydantic import BaseModel


# Example Pydantic model for response format
class ExampleResponse(BaseModel):
    text: str


async def main():
    model_name = "gpt-3.5-turbo"  # Replace with your desired model
    content = "Hello, how are you?"

    response = await acompletion(
        model=model_name,
        response_format=ExampleResponse,
        messages=[{"role": "user", "content": content}],
    )
    print(response.choices[0].message.content)


if __name__ == "__main__":
    asyncio.run(main())
