from rich import print
from rich.json import JSON
from rich.panel import Panel
from sotopia.database import EpisodeLog


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


def render_for_humans(episode: EpisodeLog) -> None:
    """Generate a human readable version of the episode log."""

    available_colors: list[str] = [
        "medium_violet_red",
        "green",
        "slate_blue1",
        "yellow",
    ]
    occupied_colors: list[str] = []
    agent_color_map: dict[str, str] = {}

    for idx, turn in enumerate(episode.messages):
        is_observation_printed = False

        if idx == 0:
            assert (
                len(turn) >= 2
            ), "The first turn should have at least environment messages"

            print(
                Panel(
                    turn[0][2],
                    title="Background Info",
                    style="blue",
                    title_align="left",
                )
            )
            print(
                Panel(
                    turn[1][2],
                    title="Background Info",
                    style="blue",
                    title_align="left",
                )
            )
            print("=" * 100)
            print("Start Simulation")
            print("=" * 100)

        for sender, receiver, message in turn:
            # "Observation" indicates the agent takes an action
            if not is_observation_printed and "Observation:" in message and idx != 0:
                extract_observation = message.split("Observation:")[1].strip()
                if extract_observation:
                    print(
                        Panel(
                            JSON(extract_observation, highlight=False),
                            title="Observation",
                            style="yellow",
                            title_align="left",
                        )
                    )
                is_observation_printed = True

            if receiver == "Environment":
                if sender != "Environment":
                    if "did nothing" in message:
                        continue
                    elif "left the conversation" in message:
                        print(
                            Panel(
                                f"{sender} left the conversation",
                                title="Environment",
                                style="red",
                                title_align="left",
                            )
                        )
                    else:
                        # Conversation
                        if "said:" in message:
                            (
                                available_colors,
                                occupied_colors,
                                agent_color_map,
                                sender_color,
                            ) = pick_color_for_agent(
                                sender,
                                available_colors,
                                occupied_colors,
                                agent_color_map,
                            )
                            message = message.split("said:")[1].strip()
                            print(
                                Panel(
                                    f"{message}",
                                    title=f"{sender} (Said)",
                                    style=sender_color,
                                    title_align="left",
                                )
                            )
                        # Action
                        else:
                            (
                                available_colors,
                                occupied_colors,
                                agent_color_map,
                                sender_color,
                            ) = pick_color_for_agent(
                                sender,
                                available_colors,
                                occupied_colors,
                                agent_color_map,
                            )
                            message = message.replace("[action]", "")
                            print(
                                Panel(
                                    JSON(message, highlight=False),
                                    title=f"{sender} (Action)",
                                    style=sender_color,
                                    title_align="left",
                                )
                            )
                else:
                    print(Panel(message, style="white"))
    print("=" * 100)
    print("End Simulation")
    print("=" * 100)

    reasoning_per_agent, general_comment = parse_reasoning(
        episode.reasoning, len(agent_color_map)
    )

    print(
        Panel(
            general_comment,
            title="General (Comments)",
            style="blue",
            title_align="left",
        )
    )

    for idx, reasoning in enumerate(reasoning_per_agent):
        print(
            Panel(
                f"{reasoning}\n"
                + "=" * 100
                + "\nRewards: "
                + str(episode.rewards[idx]),
                title=f"Agent {idx + 1} (Comments)",
                style="blue",
                title_align="left",
            )
        )
