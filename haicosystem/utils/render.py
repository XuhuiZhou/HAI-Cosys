import json
from typing import TypedDict

from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from sotopia.database import EpisodeLog

from haicosystem.protocols import messageForRendering


def pick_color_for_agent(
    agent_name: str,
    available_colors: list[str],
    occupied_colors: list[str],
    agent_color_map: dict[str, str],
) -> tuple[list[str], list[str], dict[str, str], str]:
    """Pick a color for the agent based on the agent name and the available colors."""

    if agent_name in agent_color_map:
        return (
            available_colors,
            occupied_colors,
            agent_color_map,
            agent_color_map[agent_name],
        )
    else:
        if available_colors:
            color = available_colors.pop(0)
            agent_color_map[agent_name] = color
            occupied_colors.append(color)
            return available_colors, occupied_colors, agent_color_map, color
        else:
            return available_colors, occupied_colors, agent_color_map, "white"


def parse_reasoning(reasoning: str, num_agents: int) -> tuple[list[str], str]:
    """Parse the reasoning string into a dictionary."""
    sep_token = "SEPSEP"
    for i in range(1, num_agents + 1):
        reasoning = (
            reasoning.replace(f"Agent {i} comments:\n", sep_token)
            .strip(" ")
            .strip("\n")
        )
    all_chunks = reasoning.split(sep_token)
    general_comment = all_chunks[0].strip(" ").strip("\n")
    comment_chunks = all_chunks[-num_agents:]

    return comment_chunks, general_comment


def render_for_humans(episode: EpisodeLog) -> list[messageForRendering]:
    """Generate a list of messages for human-readable version of the episode log."""

    messages_for_rendering: list[messageForRendering] = []

    for idx, turn in enumerate(episode.messages):
        is_observation_printed = False

        if idx == 0:
            assert (
                len(turn) >= 2
            ), "The first turn should have at least environment messages"

            messages_for_rendering.append(
                {"role": "Background Info", "type": "info", "content": turn[0][2]}
            )
            messages_for_rendering.append(
                {"role": "Background Info", "type": "info", "content": turn[1][2]}
            )
            messages_for_rendering.append(
                {"role": "System", "type": "divider", "content": "Start Simulation"}
            )

        for sender, receiver, message in turn:
            if not is_observation_printed and "Observation:" in message and idx != 0:
                extract_observation = message.split("Observation:")[1].strip()
                if extract_observation:
                    messages_for_rendering.append(
                        {
                            "role": "Observation",
                            "type": "observation",
                            "content": extract_observation,
                        }
                    )
                is_observation_printed = True

            if receiver == "Environment":
                if sender != "Environment":
                    if "did nothing" in message:
                        continue
                    elif "left the conversation" in message:
                        messages_for_rendering.append(
                            {
                                "role": "Environment",
                                "type": "leave",
                                "content": f"{sender} left the conversation",
                            }
                        )
                    else:
                        if "said:" in message:
                            message = message.split("said:")[1].strip()
                            messages_for_rendering.append(
                                {"role": sender, "type": "said", "content": message}
                            )
                        else:
                            message = message.replace("[action]", "")
                            messages_for_rendering.append(
                                {"role": sender, "type": "action", "content": message}
                            )
                else:
                    messages_for_rendering.append(
                        {
                            "role": "Environment",
                            "type": "environment",
                            "content": message,
                        }
                    )

    messages_for_rendering.append(
        {"role": "System", "type": "divider", "content": "End Simulation"}
    )

    reasoning_per_agent, general_comment = parse_reasoning(
        episode.reasoning,
        len(
            set(
                msg["role"]
                for msg in messages_for_rendering
                if msg["type"] in {"said", "action"}
            )
        ),
    )

    messages_for_rendering.append(
        {"role": "General", "type": "comment", "content": general_comment}
    )

    for idx, reasoning in enumerate(reasoning_per_agent):
        try:
            reward_for_agent = episode.rewards[idx]
            assert not isinstance(reward_for_agent, float)
            messages_for_rendering.append(
                {
                    "role": f"Agent {idx + 1}",
                    "type": "comment",
                    "content": f"{reasoning}\n{'=' * 100}\nEval scores: {str(reward_for_agent[1])}",
                }
            )
        except AssertionError:
            messages_for_rendering.append(
                {
                    "role": f"Agent {idx + 1}",
                    "type": "comment",
                    "content": f"{reasoning}\n{'=' * 100}\nEval scores: {str(reward_for_agent)}",
                }
            )
    return messages_for_rendering


def rich_rendering(messages: list[messageForRendering]) -> None:
    """Render the list of messages using rich library."""

    console = Console()

    available_colors: list[str] = [
        "medium_violet_red",
        "green",
        "slate_blue1",
        "yellow",
    ]
    occupied_colors: list[str] = []
    agent_color_map: dict[str, str] = {}

    def pick_color_for_agent(agent: str) -> str:
        if agent not in agent_color_map:
            if available_colors:
                color = available_colors.pop(0)
                occupied_colors.append(color)
            else:
                color = occupied_colors.pop(0)
                available_colors.append(color)
            agent_color_map[agent] = color
        return agent_color_map[agent]

    for message in messages:
        role = message["role"]
        msg_type = message["type"]
        content = message["content"]

        if msg_type == "info":
            console.print(Panel(content, title=role, style="blue", title_align="left"))
        elif msg_type == "divider":
            console.print("=" * 100)
            console.print(content)
            console.print("=" * 100)
        elif msg_type == "observation":
            try:
                display_content = JSON(content, highlight=False)
            except json.JSONDecodeError:
                display_content = content  # type: ignore
            console.print(
                Panel(
                    display_content,
                    title=role,
                    style="yellow",
                    title_align="left",
                )
            )
        elif msg_type == "leave":
            console.print(Panel(content, title=role, style="red", title_align="left"))
        elif msg_type == "said":
            sender_color = pick_color_for_agent(role)
            console.print(
                Panel(
                    content,
                    title=f"{role} (Said)",
                    style=sender_color,
                    title_align="left",
                )
            )
        elif msg_type == "action":
            sender_color = pick_color_for_agent(role)
            try:
                display_content = JSON(content, highlight=False)
            except json.JSONDecodeError:
                display_content = content  # type: ignore

            console.print(
                Panel(
                    display_content,
                    title=f"{role} (Action)",
                    style=sender_color,
                    title_align="left",
                )
            )
        elif msg_type == "environment":
            console.print(Panel(content, style="white"))
        elif msg_type == "comment":
            console.print(
                Panel(
                    content,
                    title=f"{role} (Comments)",
                    style="blue",
                    title_align="left",
                )
            )
