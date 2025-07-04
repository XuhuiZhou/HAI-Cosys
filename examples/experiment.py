import asyncio
import json
import logging
import subprocess
from collections import defaultdict
from datetime import datetime
from logging import FileHandler
from pathlib import Path
from typing import OrderedDict, cast

import numpy as np
import requests
import rich
import typer
from rich.logging import RichHandler
from sotopia.database import (
    AgentProfile,
    EnvAgentComboStorage,
    EpisodeLog,
)
from sotopia.envs.evaluators import (
    RuleBasedTerminatedEvaluator,
)
from sotopia.messages import AgentAction, Observation
from sotopia.samplers import (
    BaseSampler,
    EnvAgentCombo,
)
from tqdm import tqdm

from haicosystem.agents import LLMAgentBot, LLMAgentHuman
from haicosystem.envs import ParellelHaicosystemEnv, SafetyLLMEvaluator
from haicosystem.grounding_engine import LLMGroundingEngine
from haicosystem.protocols import HaiEnvironmentProfile
from haicosystem.server import run_async_server
from haicosystem.utils import get_avg_reward

app = typer.Typer(pretty_exceptions_show_locals=False, pretty_exceptions_enable=False)

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


def initilize_benchmark_combo(
    url: str, filter_env_ids: list[str] = []
) -> list[EnvAgentComboStorage]:
    if url:
        response = requests.get(url)
        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            print("Data fetched successfully")
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            raise ValueError("Failed to fetch data")
        list_of_env_agent_combo_storage = []
        for combo in data:
            env_agent_combo_storage = EnvAgentComboStorage(
                env_id=combo["env_id"], agent_ids=combo["agent_ids"]
            )
            list_of_env_agent_combo_storage.append(env_agent_combo_storage)
    else:
        list_of_env_agent_combo_storage = EnvAgentComboStorage.find().all()  # type: ignore
        if filter_env_ids:
            list_of_env_agent_combo_storage = [
                combo
                for combo in list_of_env_agent_combo_storage
                if combo.env_id in filter_env_ids
            ]
    return list_of_env_agent_combo_storage


def _set_up_logs(
    *,
    log_file_level: int = logging.DEBUG,
    log_rich_level: int = logging.INFO,
    log_format: str = "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    log_file: str = datetime.now().strftime("./logs/%H_%M_%d_%m_%Y.log"),
    print_logs: bool = False,
) -> None:
    # date and message only
    logging_path = Path(log_file)
    logging_path.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=log_file_level,
        format=log_format,
        datefmt="[%X]",
        handlers=[
            FileHandler(logging_path),
            RichHandler(level=log_rich_level) if print_logs else RichHandler(level=100),
        ],
    )


def save_to_jsonl(
    model_rewards_dict: dict[str, dict[str, tuple[float, float]]],
    partner_model: str,
) -> None:
    simplified_model_name = partner_model.split("/")[-1]
    output_fn = f"./models_vs_{simplified_model_name}.jsonl"
    outputs: list[str] = []
    for model, rewards in model_rewards_dict.items():
        formatted_reward = OrderedDict(
            {
                "model_name": model,
                **{
                    f"{v[0]} {v[1]}": rewards[k][0]
                    for k, v in dimension_range_mapping.items()
                },
            }
        )
        outputs.append(json.dumps(formatted_reward))
    with open(output_fn, "w") as f:
        f.write("\n".join(outputs))

    print(f"Output saved to {output_fn}")


default_model_list: list[str] = [
    "gpt-4o",
]
dimension_range_mapping = OrderedDict(
    {
        "social_rules": ["SOC", [-10, 0]],
        "secret": ["SEC", [-10, 0]],
        "financial_and_material_benefits": ["FIN", [-5, 5]],
        "relationship": ["REL", [-5, 5]],
        "knowledge": ["KNO", [0, 10]],
        "goal": ["GOAL", [0, 10]],
        "believability": ["BEL", [0, 10]],
    }
)


def display_in_table(
    model_rewards_dict: dict[str, dict[str, tuple[float, float]]],
) -> None:
    table = rich.table.Table(
        title=f"Risks Evaluation (+/- CI bounds)",
    )
    table.add_column("Model")
    for dimension in model_rewards_dict[list(model_rewards_dict.keys())[0]].keys():
        table.add_column(dimension)
    table.add_column("Settings")
    table.add_column("Episodes")
    for model, rewards in model_rewards_dict.items():
        table.add_row(
            model,
            *(
                [f"{rewards[k][0]:.2f} ± {rewards[k][1]:.2f}" for k in rewards.keys()]
                + [f"{rewards[k][0]:.0f}" for k in ["setting_num", "episode_count"]]
            ),
        )
    rich.print(table)


def benchmark_display(
    model_list: list[str] = default_model_list,
    partner_model: str = "together_ai/meta-llama/Llama-3-70b-chat-hf",
    evaluator_model: str = "gpt-4o",
    task: str = "hard",
    output_to_jsonl: bool = False,
    filter_env_ids: list[str] = [],
) -> None:
    """
    Usage: sotopia benchmark-display --model-list gpt-4o --model-list together_ai/meta-llama-Llama-3-70b-chat-hf
    Aggregate all the results for the benchmark, as described in https://github.com/sotopia-lab/sotopia-space/blob/main/data_dir/models_vs_gpt35.jsonl
    """

    print(f"Displaying performance for {model_list} vs {partner_model} on task {task}")
    model_rewards_dict = dict()
    for model in model_list:
        tag = f"benchmark_{model}_{partner_model}_{evaluator_model}_{task}"
        rich.print(f"[bold purple]{tag}[/bold purple]")
        episodes = EpisodeLog.find(EpisodeLog.tag == tag).all()
        if filter_env_ids:
            episodes = [
                episode
                for episode in episodes
                if episode.environment in filter_env_ids  # type: ignore
            ]
        if len(episodes) == 0:
            print(f"No episodes found for {model}")
            continue
        avg_rewards = get_avg_reward(episodes, model)  # type: ignore
        binary_avg_rewards = get_avg_reward(episodes, model, binary=True)  # type: ignore
        model_rewards_dict[model] = avg_rewards
        binary_model_rewards_dict = {model: binary_avg_rewards}
        # print(f"Model: {model}, episodes: {len(episodes)}, Avg Rewards: {avg_rewards}")
        rich.print(model_rewards_dict)
        rich.print("Ratio of episodes with positive risks")
        rich.print(binary_model_rewards_dict)

    display_in_table(model_rewards_dict)

    rich.print("Ratio of episodes with risks:")
    display_in_table(binary_model_rewards_dict)
    if output_to_jsonl:
        save_to_jsonl(model_rewards_dict, partner_model)


def preprocess_episode_data(
    episode_list_with_tag: list[EpisodeLog],
) -> dict[tuple[str, tuple[str, ...], tuple[str, ...]], bool]:
    """Preprocess episodes into a dictionary for quick lookup."""
    episode_dict = {}
    for episode in episode_list_with_tag:
        assert isinstance(episode, EpisodeLog), "episode should be an EpisodeLog"
        assert episode.models is not None, "episode.models should not be None"
        episode_key = (
            episode.environment,
            tuple(episode.agents),
            tuple(episode.models),
        )
        episode_dict[episode_key] = True
    return episode_dict


def check_existing_episodes(
    env_id: str,
    agent_ids: list[str],
    models: dict[str, str],
    index: str,
    episode_dict: dict[tuple[str, tuple[str, ...], tuple[str, ...]], bool],
) -> bool:
    models_list = (
        (models["env"], models["test_model"], models["partner_model"])
        if index == "0"
        else (models["env"], models["partner_model"], models["test_model"])
    )
    episode_key = (env_id, tuple(agent_ids), models_list)
    return episode_dict.get(episode_key, False)


def _list_all_env_agent_combo_not_in_db(
    model_names: dict[str, str],
    env_agent_combo_storage_index_list: list[tuple[EnvAgentComboStorage, str]],
    max_turn_num: int = 20,
    tag: str = "",
    task: str = "",
) -> list[EnvAgentCombo[Observation, AgentAction]]:
    """Iterate over each environment and return the first env-agent combo not in the database."""
    assert tag, "tag should not be empty"

    # Preprocess the episodes for fast lookup
    episode_list_with_tag: list[EpisodeLog] = EpisodeLog.find(
        EpisodeLog.tag == tag
    ).all()  # type: ignore
    episode_dict = preprocess_episode_data(episode_list_with_tag)
    list_of_env_agent_combo_storage = []
    for env_agent_combo_storage, index in env_agent_combo_storage_index_list:
        agent_ids = env_agent_combo_storage.agent_ids
        env_id = env_agent_combo_storage.env_id
        if check_existing_episodes(
            env_id=env_id,
            agent_ids=agent_ids,
            models=model_names,
            index=index,
            episode_dict=episode_dict,
        ):
            logging.info(
                f"Episode for {env_id} with agents {agent_ids} using {list(model_names.values())} already exists"
            )
            continue
        env_profile = HaiEnvironmentProfile.get(env_id)
        env = ParellelHaicosystemEnv(
            env_profile=env_profile,
            model_name=model_names["env"],
            action_order="round-robin",
            evaluators=[
                RuleBasedTerminatedEvaluator(
                    max_turn_number=max_turn_num, max_stale_turn=3
                ),
            ],
            terminal_evaluators=[
                SafetyLLMEvaluator(model_names["env"]),
            ],
            grounding_engines=[
                LLMGroundingEngine(model_name=model_names["env"]),
            ],
        )
        agent_profiles = [AgentProfile.get(id) for id in agent_ids]
        # make sure the second agent (i.e., the agent being benchmarked) is always the indexed agent
        agents = [
            agent_class(agent_profile=agent_profile, model_name=agent_model)
            for agent_profile, agent_model, agent_class in zip(
                agent_profiles,
                [model_names["test_model"], model_names["partner_model"]]
                if index == "0"
                else [model_names["partner_model"], model_names["test_model"]],
                [LLMAgentHuman, LLMAgentBot],
            )
        ]
        list_of_env_agent_combo_storage.append((env, agents))
    return list_of_env_agent_combo_storage  # type: ignore


def run_async_benchmark_in_batch(
    *,
    env_agent_combo_list: list[EnvAgentCombo[Observation, AgentAction]],
    batch_size: int = 1,
    tag: str = "",
    push_to_db: bool = False,
    verbose: bool = False,
    use_starting_speech: bool = False,
) -> None:
    env_agent_combo_batch: list[EnvAgentCombo[Observation, AgentAction]] = []
    loop = asyncio.get_event_loop()
    for env_agent_combo in tqdm(
        env_agent_combo_list,
        desc="Running all envs in batch",
    ):
        env_agent_combo_batch.append(env_agent_combo)
        if len(env_agent_combo_batch) == batch_size:
            logging.info(
                f"Running batch of {batch_size} episodes: {env_agent_combo_batch}"
            )
            loop.run_until_complete(
                run_async_server(
                    sampler=BaseSampler[Observation, AgentAction](),
                    env_agent_combo_list=env_agent_combo_batch,
                    push_to_db=push_to_db,
                    tag=tag,
                    use_starting_speech=use_starting_speech,
                )
            )
            env_agent_combo_batch = []
    else:
        if env_agent_combo_batch:
            logging.info(
                f"Running batch of {batch_size} episodes: {env_agent_combo_batch}"
            )
            loop.run_until_complete(
                run_async_server(
                    sampler=BaseSampler[Observation, AgentAction](),
                    env_agent_combo_list=env_agent_combo_batch,
                    push_to_db=push_to_db,
                    tag=tag,
                    use_starting_speech=use_starting_speech,
                )
            )
        # remove episodes that has bad rewards
        simulated_episodes = EpisodeLog.find(EpisodeLog.tag == tag).all()
        valid_episodes = [
            len(relevant_episode.rewards) == 2  # type: ignore
            and not isinstance(relevant_episode.rewards[0], float)  # type: ignore
            and not isinstance(relevant_episode.rewards[1], float)  # type: ignore
            for relevant_episode in simulated_episodes
        ]
        for valid, episode in zip(valid_episodes, simulated_episodes):
            if not valid:
                pk = episode.pk
                assert isinstance(pk, str)
                EpisodeLog.delete(pk)


def group_combos_into_env_id_trunks(
    benchmark_combo: list[EnvAgentComboStorage],
) -> list[list[EnvAgentComboStorage]]:
    # Create a mapping from env_id to a list of combos with that env_id
    env_id_map: dict[str, list[EnvAgentComboStorage]] = defaultdict(list)
    for combo in benchmark_combo:
        env_id_map[combo.env_id].append(combo)
    # Now create trunks
    trunks: list[list[EnvAgentComboStorage]] = []
    while any(env_id_map.values()):
        new_trunk: list[EnvAgentComboStorage] = []
        for env_id, combos in list(env_id_map.items()):
            if combos:  # If there are combos left for this env_id
                new_trunk.append(combos.pop(0))  # Take one combo
            if not combos:  # If no combos are left, remove the key
                del env_id_map[env_id]
        trunks.append(new_trunk)
    return trunks


@app.command()
def benchmark(
    models: list[str] = typer.Option(
        default_model_list,
        help=f"All the language model you want to benchmark. Default is the pre-loaded model list {default_model_list}.",
    ),
    max_turn_num: int = typer.Option(
        20, help="The maximum number of turns for an interaction."
    ),
    scenario_filter: str = typer.Option(
        "",
        help="The key word to filter the relevant scenarios from the codename of the scenarios.",
    ),
    use_starting_speech: bool = typer.Option(
        False,
        help="Use the starting speech of the environment.",
    ),
    partner_model: str = typer.Option(
        "together_ai/meta-llama/Llama-3-70b-chat-hf",
        help="The partner model you want to use.",
    ),
    evaluator_model: str = typer.Option(
        "gpt-4o", help="The evaluator model you want to use."
    ),
    batch_size: int = typer.Option(10, help="The batch size you want to use."),
    iteration_num: int = typer.Option(
        4,
        help="The number of iterations you want to run through the unique envs, this could be used to do partial benchmarking.",
    ),
    task: str = typer.Option(
        "hard",
        help="The task id you want to benchmark. Will be integrated in the tag with the model names (benchmark_[model]_[partner_model]_[evaluator_model]_[task]).",
    ),
    url: str = typer.Option("", help="The url to fetch the benchmark combo."),
    print_logs: bool = typer.Option(False, help="Print logs."),
    only_show_performance: bool = typer.Option(
        False,
        help="only show the evaluation results fetched from the database wo running the simulation.",
    ),
    output_to_jsonl: bool = typer.Option(False, help="Output to jsonl."),
    push_to_db: bool = typer.Option(False, help="Push to db."),
) -> None:
    """A simple command-line interface example."""
    _set_up_logs(print_logs=print_logs)
    filter_env_ids: list[str] = []  # if filter_env_ids is empty, all envs will be used
    if scenario_filter:
        for env_profile in HaiEnvironmentProfile.find().all():
            assert isinstance(env_profile, HaiEnvironmentProfile)
            if scenario_filter in env_profile.codename:
                assert isinstance(env_profile.pk, str)
                filter_env_ids.append(env_profile.pk)
    if only_show_performance:
        benchmark_display(
            models,
            partner_model,
            evaluator_model,
            task,
            output_to_jsonl,
            filter_env_ids,
        )
        return
    benchmark_combo_all = initilize_benchmark_combo(url, filter_env_ids)
    benchmark_combo_trunks = group_combos_into_env_id_trunks(benchmark_combo_all)
    for iter_num, benchmark_combo in enumerate(benchmark_combo_trunks):
        if iter_num >= iteration_num:
            break
        env_agent_combo_storage_index_list = [
            (env_agent_combo_storage, "1")
            for env_agent_combo_storage in benchmark_combo
        ]
        for model in models:
            typer.echo(
                f"Running benchmark for {model} chatting with {partner_model} on task {task} with {evaluator_model} as the evaluator."
            )
            tag = f"benchmark_{model}_{partner_model}_{evaluator_model}_{task}"
            typer.echo(typer.style(f"Tag: {tag}", fg=typer.colors.GREEN, bold=True))
            model_names = {
                "env": evaluator_model,
                "test_model": model,
                "partner_model": partner_model,
            }
            env_agent_combo_list = _list_all_env_agent_combo_not_in_db(
                model_names=model_names,
                tag=tag,
                env_agent_combo_storage_index_list=env_agent_combo_storage_index_list,
                max_turn_num=max_turn_num,
                task=task,
            )
            number_of_fix_turns = (
                0  # maximum number of times to fix the problematic episodes
            )
            while True:
                run_async_benchmark_in_batch(
                    env_agent_combo_list=env_agent_combo_list,
                    batch_size=batch_size,
                    tag=tag,
                    verbose=False,
                    push_to_db=push_to_db,
                    use_starting_speech=use_starting_speech,
                )
                env_agent_combo_list = _list_all_env_agent_combo_not_in_db(
                    model_names=model_names,
                    tag=tag,
                    env_agent_combo_storage_index_list=env_agent_combo_storage_index_list,
                    task=task,
                    max_turn_num=max_turn_num,
                )
                number_of_fix_turns += 1
                if len(env_agent_combo_list) == 0 or number_of_fix_turns >= 5:
                    break

    benchmark_display(
        models,
        partner_model,
        evaluator_model,
        task,
        output_to_jsonl=output_to_jsonl,
        filter_env_ids=filter_env_ids,
    )


if __name__ == "__main__":
    app()
