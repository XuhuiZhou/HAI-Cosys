import asyncio
from haicosystem.server import run_server
import logging
from rich.logging import RichHandler
import subprocess

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

asyncio.run(
    run_server(
        model_dict={
            "env": "gpt-4-turbo",
            "agent1": "gpt-4-turbo",
            "agent2": "gpt-4-turbo",
        },
        agents_roles={
            "agent1": "human",
            "agent2": "ai",
        },
    )
)
