import json
import os
import random

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


def upload_envs_to_db(env_file: str) -> None:
    """
    Upload the environments to the database
    """
    with open(env_file, "r") as file:
        env_profile_json = json.load(file)
        env_profile = HaiEnvironmentProfile.parse_obj(env_profile_json)
        env_profile.save()
    print(f"Uploaded {env_file} environment profiles to the database")


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
    human_agent_profile_sample = random.sample(human_agent_profiles, sample_size)
    env_agent_combo_list = [
        (env_id, (human_agent_profile.pk, ai_agent_pk))
        for human_agent_profile in human_agent_profile_sample
    ]
    for env_id, agent in env_agent_combo_list:
        EnvAgentComboStorage(
            env_id=env_id,
            agent_ids=agent,  # TODO: more organic sampling
        ).save()


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
        3, help="The number of human agents to sample for each environment"
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
            EnvAgentComboStorage.delete(storage.pk)
            print(f"Cleaned {index + 1} environment-agent combos")

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
        for index, env in enumerate(HaiEnvironmentProfile.all_pks()):
            HaiEnvironmentProfile.delete(env)
            print(f"Cleaned {index + 1} environment profiles")

    agent_files = os.listdir(agent_folder)
    for agent_file in agent_files:
        upload_agents_to_db(os.path.join(agent_folder, agent_file))

    for env_folder in env_folders.split(","):
        env_files = os.listdir(env_folder)
        for env_file in env_files:
            upload_envs_to_db(os.path.join(env_folder, env_file))

    print("Created environment-agent combo")
    ai_agents: list[AgentProfile] = AgentProfile.find(
        AgentProfile.last_name == "AI"
    ).all()  # type: ignore
    human_agents: list[AgentProfile] = AgentProfile.find(
        AgentProfile.last_name != "AI"
    ).all()  # type: ignore
    env_list = HaiEnvironmentProfile.all_pks()
    for env in env_list:
        assert ai_agents[0].pk is not None
        _sample_env_agent_combo_and_push_to_db(
            env,
            ai_agents[0].pk,
            human_agent_profiles=human_agents,
            sample_size=sample_size,
        )  # TODO: more organic sampling

    env_agent_combo_list = EnvAgentComboStorage.find().all()
    print(f"Created {len(env_agent_combo_list)} environment-agent combos")


if __name__ == "__main__":
    app()
