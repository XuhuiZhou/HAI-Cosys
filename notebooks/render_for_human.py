from typer import Typer
from sotopia.database import EpisodeLog
from haicosystem.utils.render import render_for_humans

app = Typer()


@app.command()
def print_episode(episode_number: int) -> None:
    """
    Print a human readable version of the episode log; episode_number is the index of the episode in the database.
    """
    episode = EpisodeLog.find(EpisodeLog.tag == "haicosystem_debug")[episode_number]  # type: ignore
    assert isinstance(episode, EpisodeLog)
    render_for_humans(episode)


if __name__ == "__main__":
    app()
