import asyncio
from haicosystem.server import run_server

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
