import asyncio
import json
import logging
from typing import Annotated

import rich
import typer
from rich.logging import RichHandler
from typer import Typer

from haicosystem.generation_utils import agenerate_hai_scenarios

FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

app = Typer(pretty_exceptions_show_locals=False)

logging.basicConfig(
    level=15,
    format=FORMAT,
    datefmt="[%X]",
    handlers=[
        RichHandler(),
    ],
)


@app.command()
def generate_scenarios(
    inspiration: Annotated[
        str, typer.Option(help="the inspiration prompt for the HAI system")
    ],
) -> None:
    """
    Generate scenarios for the HAI system.
    """
    if (
        "official" in inspiration
    ):  # "official" is a keyword that indicates the prompt is from ToolEmu
        toolemu_data = json.load(
            open("data/all_cases.json")
        )  # Download the data from ToolEmu/assets/all_cases.json repository
        scenario_exist = False
        for entry in toolemu_data:
            if inspiration == entry["name"]:
                scenario_exist = True
                break
        assert scenario_exist, f"Prompt {inspiration} not found in the ToolEmu data"
        inspiration = json.dumps(entry, indent=4)

    examples_dict = json.load(open("data/example_scenarios.json"))
    examples = "\n\n".join([json.dumps(ex, indent=4) for ex in examples_dict.values()])

    hai_env_profile = asyncio.run(
        agenerate_hai_scenarios(
            model_name="gpt-4-turbo",
            inspiration_prompt=inspiration,
            examples=examples,
            temperature=1.2,
        )
    )
    rich.print(hai_env_profile.json(indent=4))


if __name__ == "__main__":
    app()
