import asyncio
import csv
import json
import logging
import random
import subprocess
from typing import Annotated, Optional

import typer
from rich.logging import RichHandler
from sotopia.database import EpisodeLog
from sotopia.envs.evaluators import SotopiaDimensions

from haicosystem.envs.evaluators import EvaluationForAIAgent
from haicosystem.protocols.database import HaiEnvironmentProfile
from haicosystem.server import run_async_server
from haicosystem.utils import BridgeSampler

random.seed(42)

app = typer.Typer()


@app.command()
def sample_episodes_for_annotating_eval(
    episode_tags: Annotated[str, typer.Option(help="tags of the episodes to sample")],
    num_episodes: Annotated[
        int, typer.Option(help="number of episodes to sample", min=1)
    ],
    output_file: Annotated[
        str, typer.Option(help="output file to save the sampled episodes")
    ],
) -> None:
    """
    Sample episodes for annotating evaluation
    """
    episode_collection = []
    episode_tag_list = episode_tags.split(",")
    for episode_tag in episode_tag_list:
        episode_logs = EpisodeLog.find(EpisodeLog.tag == episode_tag).all()
        episode_collection.extend(episode_logs)
    sampled_episodes = random.sample(episode_collection, num_episodes)
    evaluation_metrics = (
        ["risky_or_not"]
        + list(EvaluationForAIAgent.__fields__.keys())
        + list(SotopiaDimensions.__fields__.keys())
    )
    spreadsheet_header = ["episode_pk", "episode_link", "model"] + evaluation_metrics
    spreadsheet_rows = []
    for episode in sampled_episodes:
        assert isinstance(episode, EpisodeLog)
        assert episode.models is not None
        episode_link = f"http://localhost:8501/?pk={episode.pk}"
        episode_row = [episode.pk, episode_link, episode.models[0]]
        for metric in evaluation_metrics:
            episode_row.append("")
        spreadsheet_rows.append(episode_row)

    with open(output_file, "w") as file:
        writer = csv.writer(file)
        writer.writerow(spreadsheet_header)
        writer.writerows(spreadsheet_rows)

    print(
        f"Sampled {num_episodes} episodes for annotating evaluation and saved to {output_file}"
    )


if __name__ == "__main__":
    app()
