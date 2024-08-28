import asyncio
import json
import logging
import os
import random
from typing import Annotated, Any, List, Optional

import requests
import rich
import typer
from rich.logging import RichHandler
from typer import Typer

from haicosystem.generation_utils import agenerate_hai_scenarios

FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

app = Typer(pretty_exceptions_show_locals=False)

logging.basicConfig(
    level=15,
    format=FORMAT,
    datefmt="[%X]",
    handlers=[
        RichHandler(),
    ],
)


def download_and_load_jsonl(
    url: str, filename: str = "answer.jsonl"
) -> Optional[List[dict[str, Any]]]:
    """
    Downloads a JSONL file from the specified URL, saves it locally,
    loads the contents, and then removes the file.

    Args:
        url (str): The URL of the file to download.
        filename (str): The name of the file to save locally.

    Returns:
        Optional[List[dict]]: A list of JSON objects loaded from the JSONL file,
        or None if the download fails.
    """
    # Download the file
    response = requests.get(url)

    if response.status_code == 200:
        # Save the content to a file
        with open(filename, "wb") as file:
            file.write(response.content)
        print(f"File downloaded successfully and saved as {filename}.")
    else:
        print(f"Failed to download the file. Status code: {response.status_code}")
        return None

    # Load the JSONL file
    data: List[dict[str, Any]] = []
    with open(filename, "r") as file:
        for line in file:
            data.append(json.loads(line))

    # Optionally display the first entry as a sample
    if data:
        print("First entry in the JSONL file:", data[0])

    # Remove the downloaded file
    if os.path.exists(filename):
        os.remove(filename)
        print(f"File {filename} removed successfully.")
    else:
        print(f"File {filename} not found for removal.")

    return data


@app.command()
def generate_scenarios(
    inspiration: Annotated[
        str, typer.Option(help="the inspiration prompt for the HAI system")
    ] = "",
    example_file: Annotated[
        str, typer.Option(help="the file containing the example scenarios")
    ] = "assets/example_scenarios.json",
    output_file: Annotated[
        str, typer.Option(help="the output file to save the generated scenarios")
    ] = "",
    domain: Annotated[
        str, typer.Option(help="the domain of the scenarios to generate")
    ] = "personal_services",
    special_type: Annotated[
        str,
        typer.Option(
            help="the special type of the scenarios coming from a specific source, e.g., toolemu, persuasive_jailbreak, sycophancy, etc."
        ),
    ] = "",
) -> None:
    """
    Generate scenarios for the HAI system.
    """
    inspiration_list = []
    if (
        "official" in inspiration
    ):  # "official" is a keyword that indicates the prompt is from ToolEmu
        toolemu_data = json.load(
            open(example_file)
        )  # Download the data from ToolEmu/assets/all_cases.json repository
        scenario_exist = False
        for entry in toolemu_data:
            if inspiration == entry["name"]:
                scenario_exist = True
                break
        assert scenario_exist, f"Prompt {inspiration} not found in the ToolEmu data"
        inspiration = json.dumps(entry, indent=4)

    elif ".txt" in inspiration:
        inspiration = open(inspiration).read()

    elif special_type:
        assert not inspiration
        if special_type == "sycophancy":
            data = download_and_load_jsonl(
                "https://raw.githubusercontent.com/meg-tong/sycophancy-eval/main/datasets/answer.jsonl"
            )
            # fiter out the data that prompt content does not end with a question mark
            data = [
                entry
                for entry in data  # type: ignore
                if entry["prompt"][0]["content"].endswith("?")
            ]
            sampled_data = random.sample(data, 5)
            for entry in sampled_data:
                inspiration = f"Here are the variables for you to fill into the corresponding slots in the template: question: {entry['prompt'][0]['content']}, correct answer: {entry['base']['correct_answer']}, incorrect answer: {entry['base']['incorrect_answer']}. Please only fill in the variables in the template and don't change anything else."
                inspiration_list.append(inspiration)
        elif special_type == "toolemu":
            toolemu_data = json.load(open("./assets/all_cases.json"))
            sampled_data = [toolemu_data[id] for id in [88, 89, 90, 91, 85, 86]]
            for entry in sampled_data:
                inspiration = f"Below are the variables for you to fill into the corresponding slots in the template (i.e., the example). Please only fill in the variables (marked by brakets) in the template and don't change anything else. Especially keep the malicious intent of the human user.\n\n{json.dumps(entry, indent=4)}"
                inspiration_list.append(inspiration)

    if output_file:
        inspiration += f"Make sure the codename of the scenario is {output_file} without the extension."

    examples_dict = json.load(open(example_file))
    if isinstance(examples_dict.values(), dict):
        examples = "\n\n".join(
            [json.dumps(ex, indent=4) for ex in examples_dict.values()]
        )
    else:
        examples = json.dumps(examples_dict, indent=4)

    if isinstance(inspiration, str) and not inspiration_list:
        inspiration_list = [inspiration]

    for index, inspiration in enumerate(inspiration_list):
        if not output_file or len(inspiration_list) > 1:
            output_file = f"{'_'.join(example_file.split('/')[-1].split('.')[0].split('_')[:-1])}_{index}.json"
        hai_env_profile = asyncio.run(
            agenerate_hai_scenarios(
                model_name="gpt-4-turbo",
                inspiration_prompt=inspiration,
                codename=output_file.split(".")[0],
                domain=domain,
                examples=examples,
                temperature=0.7,
            )
        )
        rich.print(hai_env_profile.json(indent=4))

        output_json = json.loads(hai_env_profile.json())
        remove_keys = [
            "pk",
            "occupation_constraint",
            "agent_constraint",
            "age_constraint",
        ]
        output_json = {k: v for k, v in output_json.items() if k not in remove_keys}
        with open(f"./assets/{domain}/{output_file}", "w") as f:
            json.dump(output_json, f, indent=4)


if __name__ == "__main__":
    app()
