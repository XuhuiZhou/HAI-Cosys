import asyncio
import json
import logging
import random
import subprocess
from typing import Annotated, List, Optional

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
    level=15,
    format=FORMAT,
    datefmt="[%X]",
    handlers=[
        RichHandler(),
    ],
)

BENCHMARK_TAGS = [
    "benchmark_gpt-4-turbo_gpt-4o-2024-08-06_gpt-4o-2024-08-06_haicosystem_trial2",
    "benchmark_gpt-3.5-turbo_gpt-4o-2024-08-06_gpt-4o-2024-08-06_haicosystem_trial2",
    "benchmark_together_ai/meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo_gpt-4o-2024-08-06_gpt-4o-2024-08-06_haicosystem_trial2",
    "benchmark_together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo_gpt-4o-2024-08-06_gpt-4o-2024-08-06_haicosystem_trial2",
    "benchmark_together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo_gpt-4o-2024-08-06_gpt-4o-2024-08-06_haicosystem_trial2",
    "benchmark_together_ai/mistralai/Mixtral-8x22B-Instruct-v0.1_gpt-4o-2024-08-06_gpt-4o-2024-08-06_haicosystem_trial2",
    "benchmark_together_ai/Qwen/Qwen1.5-72B-Chat_gpt-4o-2024-08-06_gpt-4o-2024-08-06_haicosystem_trial2",
    "benchmark_together_ai/Qwen/Qwen2-72B-Instruct_gpt-4o-2024-08-06_gpt-4o-2024-08-06_haicosystem_trial2",
    "benchmark_together_ai/Qwen/Qwen1.5-110B-Chat_gpt-4o-2024-08-06_gpt-4o-2024-08-06_haicosystem_trial2",
    "benchmark_together_ai/meta-llama/Meta-Llama-3-70B-Instruct-Turbo_gpt-4o-2024-08-06_gpt-4o-2024-08-06_haicosystem_trial2",
    "benchmark_together_ai/meta-llama/Meta-Llama-3-8B-Instruct-Turbo_gpt-4o-2024-08-06_gpt-4o-2024-08-06_haicosystem_trial2",
    "benchmark_together_ai/deepseek-ai/deepseek-llm-67b-chat_gpt-4o-2024-08-06_gpt-4o-2024-08-06_haicosystem_trial2",
]


async def evaluate_episode(
    episode: EpisodeLog,
    evaluate_model: str = "gpt-4o-2024-08-06",
    push_to_db: bool = False,
    tag: str = "",
) -> None:
    """Evaluate a single episode using Gemini as the evaluator."""
    try:
        await aevaluate_one_episode(
            episode=episode, model=evaluate_model, push_to_db=push_to_db, tag=tag
        )
    except Exception as e:
        logging.error(f"Error evaluating episode {episode.pk}: {str(e)}")


async def evaluate_episodes_with_tag(
    tag: str,
    push_to_db: bool = False,
    max_concurrent: int = 1,
    sample_size: int = 200,
    evaluate_model: str = "gpt-4o-2024-08-06",
) -> None:
    """Evaluate all episodes with the given tag using Gemini as the evaluator."""
    episodes = EpisodeLog.find(EpisodeLog.tag == tag).all()
    episodes = list(episodes)
    episodes = random.sample(episodes, sample_size)
    logging.info(f"Found {len(episodes)} episodes with tag {tag}")
    # Split the tag by underscores and replace the last model
    tag_parts = tag.split("_")
    tag_parts[-3] = evaluate_model.replace(
        "/", "-"
    )  # Replace the last model (second to last part)
    new_tag = "_".join(tag_parts)
    # Remove any existing episodes with the new tag before evaluating
    existing_episodes = EpisodeLog.find(EpisodeLog.tag == new_tag).all()
    if existing_episodes:
        logging.info(
            f"Removing {len(existing_episodes)} existing episodes with tag {new_tag}"
        )
        for episode in existing_episodes:
            EpisodeLog.delete(episode.pk)
    # Process episodes in batches to control concurrency
    for i in range(0, len(episodes), max_concurrent):
        batch = episodes[i : i + max_concurrent]
        logging.info(
            f"Evaluating episodes {i+1}-{min(i+max_concurrent, len(episodes))}/{len(episodes)} with tag {tag}"
        )

        # Create tasks for concurrent evaluation
        tasks = [
            evaluate_episode(episode, evaluate_model, push_to_db, new_tag)
            for episode in batch
        ]
        await asyncio.gather(*tasks)


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
            int(episode_index)  # type: ignore
        ]
        assert isinstance(episode, EpisodeLog)
    asyncio.run(
        aevaluate_one_episode(
            episode=episode, model="gpt-4-turbo", push_to_db=push_to_db
        )
    )


@app.command()
def evaluate_benchmarks(
    push_to_db: bool = typer.Option(
        False, help="Whether to push the evaluation results to the database"
    ),
    tags: List[str] = typer.Option(
        None,
        help="Specific tags to evaluate. If not provided, all benchmark tags will be used.",
    ),
    max_concurrent: int = typer.Option(
        100, help="Maximum number of concurrent evaluations"
    ),
    evaluate_model: str = typer.Option(
        "gpt-4o-2024-08-06", help="The model to use for evaluation"
    ),
    sample_size: int = typer.Option(
        200, help="Number of episodes to sample for evaluation"
    ),
) -> None:
    """
    Re-evaluate episodes with benchmark tags using Gemini as the evaluator.
    """
    tags_to_evaluate = tags if tags else BENCHMARK_TAGS

    for tag in tags_to_evaluate:
        logging.info(f"Starting evaluation for tag: {tag}")
        asyncio.run(
            evaluate_episodes_with_tag(
                tag, push_to_db, max_concurrent, sample_size, evaluate_model
            )
        )
        logging.info(f"Completed evaluation for tag: {tag}")


if __name__ == "__main__":
    app()
