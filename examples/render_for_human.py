from typing import Annotated, Optional

import typer
from sotopia.database import EpisodeLog
from typer import Typer

from haicosystem.utils.render import render_for_humans, rich_rendering

app = Typer()


@app.command()
def print_episode(
    episode_pk: Annotated[
        Optional[str], typer.Option(help="the filename of the scenario")
    ] = "",
    episode_index: Annotated[
        Optional[str], typer.Option(help="the codename of the scenario")
    ] = "",
    tag: Annotated[
        Optional[str], typer.Option(help="the tag of the scenario")
    ] = "benchmark_gpt-4-turbo_gpt-4o_gpt-4o_haicosystem_trial0",
) -> None:
    """
    Print a human readable version of the episode log; episode_number is the index of the episode in the database.
    """
    assert episode_pk or episode_index, "Either filename or codename must be provided"
    if episode_pk:
        episode = EpisodeLog.get(episode_pk)
        assert isinstance(episode, EpisodeLog)
    else:
        episode = EpisodeLog.find(EpisodeLog.tag == tag)[episode_index]  # type: ignore
        assert isinstance(episode, EpisodeLog)
    messages = render_for_humans(episode)
    rich_rendering(messages)


if __name__ == "__main__":
    app()
