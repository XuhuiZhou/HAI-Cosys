import asyncio
import json
import logging
import subprocess
from typing import Annotated, Optional

import typer
from rich.logging import RichHandler
from sotopia.database import EpisodeLog

from haicosystem.protocols.database import HaiEnvironmentProfile
from haicosystem.server import aevaluate_one_episode

app = typer.Typer(pretty_exceptions_show_locals=False)

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
    episode_pk: Annotated[
        Optional[str], typer.Option(help="the filename of the scenario")
    ] = "",
    episode_index: Annotated[
        Optional[str], typer.Option(help="the codename of the scenario")
    ] = "",
    push_to_db: Annotated[
        bool, typer.Option(help="Whether to push to the database")
    ] = False,
) -> None:
    """
    Run the server with the given codename, and push the results to the database if push_to_db is True.
    """
    assert episode_pk or episode_index, "Either filename or codename must be provided"
    if episode_pk:
        episode = EpisodeLog.get(episode_pk)
        assert isinstance(episode, EpisodeLog)
    else:
        episode = EpisodeLog.find(EpisodeLog.tag == "haicosystem_debug")[
            int(episode_index)
        ]  # type: ignore
        assert isinstance(episode, EpisodeLog)
    asyncio.run(
        aevaluate_one_episode(
            episode=episode, model="gpt-4-turbo", push_to_db=push_to_db
        )
    )


if __name__ == "__main__":
    app()
