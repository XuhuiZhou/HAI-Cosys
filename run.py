import asyncio
import json
import logging
import subprocess

from rich.logging import RichHandler
from typer import Typer

from haicosystem.protocols.database import HaiEnvironmentProfile
from haicosystem.server import BridgeSampler, run_server

app = Typer()

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
filename = "./data/example_scenarios.json"
with open(filename, "r") as file:
    env_profiles_json = json.load(file)
env_profile = HaiEnvironmentProfile.parse_obj(
    env_profiles_json["TeladocRequestPrescription_0"]
)
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
        push_to_db=False,
        tag="haicosystem_debug",
    )
)
