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
    output_file: Annotated[
        str, typer.Option(help="the output file to save the generated scenarios")
    ] = "",
    domain: Annotated[
        str, typer.Option(help="the domain of the scenarios to generate")
    ] = "personal_services",
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

    elif ".txt" in inspiration:
        inspiration = open(inspiration).read()
    if output_file:
        inspiration += f"Make sure the codename of the scenario is {output_file} without the extension."

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

    output_json = json.loads(hai_env_profile.json())
    remove_keys = ["pk", "occupation_constraint", "agent_constraint", "age_constraint"]
    output_json = {k: v for k, v in output_json.items() if k not in remove_keys}
    if output_file:
        with open(f"./data/{domain}/{output_file}", "w") as f:
            json.dump(output_json, f, indent=4)


if __name__ == "__main__":
    app()
