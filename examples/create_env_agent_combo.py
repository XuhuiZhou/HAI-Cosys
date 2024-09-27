import json
import os
import random
import time

import typer
from sotopia.agents.llm_agent import LLMAgent
from sotopia.database import AgentProfile, EnvAgentComboStorage
from sotopia.messages import AgentAction, Observation
from sotopia.samplers import ConstraintBasedSampler

from haicosystem.protocols import HaiEnvironmentProfile

app = typer.Typer(pretty_exceptions_show_locals=False)


def upload_agents_to_db(agent_file: str) -> None:
    """
    Upload the agents to the database
    """
    with open(agent_file, "r") as file:
        agent_profile_json = json.load(file)
        agent_profile = AgentProfile.parse_obj(agent_profile_json)
        agent_profile.save()
    print(f"Uploaded {agent_file} agent profiles to the database")


@app.command()
def update_env_on_db(env_file: str) -> None:
    """
    Update the environments to the database
    """
    with open(env_file, "r") as file:
        env_profile_json = json.load(file)
        env_profile_list = HaiEnvironmentProfile.find(
            HaiEnvironmentProfile.codename == env_profile_json["codename"]
        ).all()
        assert len(env_profile_list) == 1
        env_profile = env_profile_list[0]
        print(env_profile.pk)
        for key, value in env_profile_json.items():
            if hasattr(env_profile, key):
                if getattr(env_profile, key) != value:
                    setattr(env_profile, key, value)
                    print(f"Updated {key} to {value}")
                else:
                    print(f"No update for {key}")
        env_profile.save()
    print(f"Updated {env_file} environment profiles to the database")


@app.command()
def update_envs_on_db(env_folder: str) -> None:
    """
    Update the environments to the database
    """
    env_files = os.listdir(env_folder)
    for env_file in env_files:
        if env_file.endswith(".json"):
            update_env_on_db(os.path.join(env_folder, env_file))


def upload_envs_to_db(env_file: str) -> str | None:
    """
    Upload the environments to the database
    """
    with open(env_file, "r") as file:
        env_profile_json = json.load(file)
        env_profile = HaiEnvironmentProfile.parse_obj(env_profile_json)
        existing_env_profile = HaiEnvironmentProfile.find(
            HaiEnvironmentProfile.codename == env_profile.codename
        ).all()
        if len(existing_env_profile) > 0:
            print(f"Environment {env_profile.codename} already exists")
            return existing_env_profile[0].pk
            # return None
        env_profile.save()
    print(f"Uploaded {env_file} environment profiles to the database")
    return env_profile.pk


def _sample_env_agent_combo_and_push_to_db(
    env_id: str,
    ai_agent_pk: str,
    human_agent_profiles: list[AgentProfile],
    sample_size: int = 3,
) -> None:
    # sampler = ConstraintBasedSampler[Observation, AgentAction](env_candidates=[env_id])
    # env_agent_combo_list = list(
    #     sampler.sample(agent_classes=[LLMAgent] * 2, replacement=False, size=1)
    # )
    env_profile = HaiEnvironmentProfile.get(pk=env_id)
    if env_profile.domain == "technology_and_science":
        human_agent_profile_sample = [
            human_agent_profile
            for human_agent_profile in human_agent_profiles
            if human_agent_profile.occupation == "Researcher"
        ]
    else:
        human_agent_profile_sample = random.sample(human_agent_profiles, sample_size)
    env_agent_combo_list = [
        (env_id, (human_agent_profile.pk, ai_agent_pk))
        for human_agent_profile in human_agent_profile_sample
    ]
    breakpoint()
    for env_id, agent in env_agent_combo_list:
        EnvAgentComboStorage(
            env_id=env_id,
            agent_ids=agent,  # TODO: more organic sampling
        ).save()


def show_env_stats(env_paths: list[str]) -> None:
    env_profile_jsons = []
    for env_path in env_paths:
        with open(env_path, "r") as file:
            env_profile_json = json.load(file)
            env_profile_jsons.append(env_profile_json)
    # total number of environments
    print(f"Total number of environments: {len(env_profile_jsons)}")

    # number of environments with respect to domain
    domain_count: dict[str, int] = {}
    for env_profile_json in env_profile_jsons:
        domain = env_profile_json["domain"]
        if domain in domain_count:
            domain_count[domain] += 1
        else:
            domain_count[domain] = 1
    print("Number of environments with respect to domain:")
    for domain, count in domain_count.items():
        print(f"{domain}: {count}")

    # number of environments with respect to intents
    intent_count: dict[str, int] = {}
    for env_profile_json in env_profile_jsons:
        intents = env_profile_json["agent_intent_labels"]
        for intent in intents:
            if intent in intent_count:
                intent_count[intent] += 1
            else:
                intent_count[intent] = 1
    print("Number of environments with respect to intents:")
    for intent, count in intent_count.items():
        print(f"{intent}: {count}")


@app.command()
def create_env_agent_combo(
    agent_folder: str = typer.Option(
        "./assets/ai_agent_profiles", help="The folder containing the agent JSON files"
    ),
    env_folders: str = typer.Option(
        "./assets/personal_services",
        help="The folder containing the environment JSON files, seperate by comma",
    ),
    clean_combos: bool = typer.Option(
        False, help="Whether to clean the existing environment-agent combos"
    ),
    sample_size: int = typer.Option(
        5, help="The number of human agents to sample for each environment"
    ),
    env_stats: bool = typer.Option(
        False, help="Whether to print the environment statistics"
    ),
    only_updated_envs: bool = typer.Option(
        False, help="Whether to only update the environments that have been updated"
    ),
) -> None:
    """
    Create environment-agent combo from the given JSON files
    """
    if clean_combos:
        typer.confirm(
            "Are you sure you want to clean the existing environment-agent combos?",
            abort=True,
        )
        for index, storage in enumerate(EnvAgentComboStorage.find().all()):
            count = 0
            env_profile = HaiEnvironmentProfile.get(pk=storage.env_id)  # type: ignore
            if env_profile.domain == "technology_and_science":
                EnvAgentComboStorage.delete(storage.pk)
                print(f"Cleaned {count} environment-agent combos")
                count += 1

        typer.confirm(
            "Are you sure you want to clean the existing AI agent profiles?", abort=True
        )
        for index, agent in enumerate(
            AgentProfile.find(AgentProfile.last_name == "AI").all()
        ):
            AgentProfile.delete(agent.pk)
            print(f"Cleaned {index + 1} AI agent profiles")

        typer.confirm(
            "Are you sure you want to clean the existing HAI environment profiles?",
            abort=True,
        )
        for index, env in enumerate(HaiEnvironmentProfile.find().all()):
            HaiEnvironmentProfile.delete(env.pk)
            print(f"Cleaned {index + 1} environment profiles")
        time.sleep(5)

    env_paths = []
    for env_folder in env_folders.split(","):
        env_files = os.listdir(env_folder)
        env_files = [env_file for env_file in env_files if env_file.endswith(".json")]
        for env_file in env_files:
            env_paths.append(os.path.join(env_folder, env_file))
    if env_stats:
        show_env_stats(env_paths)
        return

    updated_envs = []
    for env_path in env_paths:
        updated_pk = upload_envs_to_db(env_path)
        if updated_pk is not None:
            updated_envs.append(updated_pk)

    # agent_files = os.listdir(agent_folder)
    # for agent_file in agent_files:
    #     if agent_file.endswith(".json"):
    #         upload_agents_to_db(os.path.join(agent_folder, agent_file))

    print("Created environment-agent combo")
    ai_agents: list[AgentProfile] = AgentProfile.find(
        AgentProfile.last_name == "AI"
    ).all()  # type: ignore
    human_agents: list[AgentProfile] = AgentProfile.find(
        AgentProfile.last_name != "AI"
    ).all()  # type: ignore
    env_list: list[HaiEnvironmentProfile] = []
    if only_updated_envs:
        env_list = [HaiEnvironmentProfile.get(pk=pk) for pk in updated_envs]
    else:
        env_list = HaiEnvironmentProfile.find().all()  # type: ignore
    print(f"# AI agents: {len(ai_agents)}")
    print(f"# Human agents: {len(human_agents)}")
    print(f"# Environments: {len(env_list)}")
    for env in env_list:
        assert ai_agents[0].pk is not None
        assert env.pk is not None
        _sample_env_agent_combo_and_push_to_db(
            env.pk,
            ai_agents[0].pk,
            human_agent_profiles=human_agents,
            sample_size=sample_size,
        )  # TODO: more organic sampling

    env_agent_combo_list = EnvAgentComboStorage.find().all()
    print(f"Created {len(env_agent_combo_list)} environment-agent combos")


if __name__ == "__main__":
    app()
