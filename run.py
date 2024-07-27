import asyncio
import json
import logging
import subprocess
from typing import Annotated

import typer
from rich.logging import RichHandler

from haicosystem.protocols.database import HaiEnvironmentProfile
from haicosystem.server import BridgeSampler, run_server

app = typer.Typer()

# date and message only
FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

process = subprocess.Popen(
    ["git", "rev-parse", "HEAD"], shell=False, stdout=subprocess.PIPE
)
git_head_hash = process.communicate()[0].strip()

logging.basicConfig(
    level=20,
    format=FORMAT,
    datefmt="[%X]",
    handlers=[
        RichHandler(),
    ],
)


@app.command()
def example_run(
    codename: Annotated[str, typer.Option(help="the codename of the scenario")],
    push_to_db: Annotated[
        bool, typer.Option(help="Whether to push to the database")
    ] = False,
) -> None:
    """
    Run the server with the given codename, and push the results to the database if push_to_db is True.
    """
    filename = "./data/example_scenarios.json"
    with open(filename, "r") as file:
        env_profiles_json = json.load(file)
    env_profile = HaiEnvironmentProfile.parse_obj(env_profiles_json[codename])
    asyncio.run(
        run_server(
            sampler=BridgeSampler(env_candidates=[env_profile]),
            model_dict={
                "env": "gpt-4-turbo",
                "agent1": "gpt-4-turbo",
                "agent2": "gpt-4-turbo",
            },
            agents_roles={
                "agent1": "human",
                "agent2": "ai",
            },
            push_to_db=push_to_db,
            tag="haicosystem_debug",
        )
    )


if __name__ == "__main__":
    app()
