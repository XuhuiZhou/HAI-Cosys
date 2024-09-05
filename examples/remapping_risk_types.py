import json
import os
from typing import List

import typer

app = typer.Typer()

# Old risk types and their mapping to new ones
risk_remapping = {
    "privacy_breach": "privacy",
    "misinformation": "deception",
    "information_security": "security_risks",
    "legal_consequences": "fundamental_rights",
    "physical_harm": "violence_extremism",
    "reputation_damage": "defamation",
    "emotion_damage": "discrimination_bias",
    "drug_misuse": "criminal_activities",
    "financial_loss": "economic_harm",
    "unauthorized_prescription": "operational_misuses",
    "miscoordination": "operational_misuses",
    "security_risk": "security_risks",
    "security_breach": "security_risks",
    "social_harm": "hate_toxicity",
    "identity_theft": "privacy",
    "unauthorized_data_sharing": "privacy",
    "spamming": "deception",
    "system_instability": "operational_misuses",
    "legal_issue": "fundamental_rights",
    "performance_impairment": "operational_misuses",
    "legal_violation": "fundamental_rights",
    "emotional_harm": "discrimination_bias",
    "public_safety": "violence_extremism",
    "traffic_mismanagement": "operational_misuses",
    "scientific_misconduct": "deception",
    "ethical_issues": "fundamental_rights",
    "trust_loss": "manipulation",
}


def update_risk_types_in_file(filepath: str, mapping: dict) -> bool:
    """
    Updates the risk types in the given JSON file based on the provided mapping.

    Args:
        filepath (str): Path to the JSON file.
        mapping (dict): Old to new risk type mapping.

    Returns:
        bool: True if the file was updated, False otherwise.
    """
    updated = False
    try:
        with open(filepath, "r") as f:
            data = json.load(f)

        # Update the risk_type field if it exists and contains old types
        if "risk_type" in data:
            old_risks = [risk.strip() for risk in data["risk_type"].split(",")]
            new_risks = [mapping.get(risk, risk) for risk in old_risks]
            if "domain" in data and data["domain"] == "politics_and_law":
                new_risks.append("political_usage")
            if old_risks != new_risks:
                data["risk_type"] = ", ".join(new_risks)
                updated = True

        # Save the file if updates were made
        if updated:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=4)

    except Exception as e:
        typer.echo(f"Error processing {filepath}: {e}")

    return updated


def scan_and_update_json_files(directory: str, mapping: dict):
    """
    Recursively scans a directory for JSON files and updates risk types in each file.

    Args:
        directory (str): The directory to scan for JSON files.
        mapping (dict): Old to new risk type mapping.
    """
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                filepath = os.path.join(root, file)
                typer.echo(f"Processing {filepath}...")
                updated = update_risk_types_in_file(filepath, mapping)
                if updated:
                    typer.echo(f"Updated {filepath}.")
                else:
                    typer.echo(f"No updates made to {filepath}.")


@app.command()
def update_risks(
    folder: str = typer.Argument("./assets", help="The folder to scan for JSON files"),
):
    """
    Command to update risk types in all JSON files within a given folder and its subfolders.

    Args:
        folder (str): The root folder where the assets (JSON files) are located.
    """
    typer.echo(f"Starting to update JSON files in {folder}...")
    scan_and_update_json_files(folder, risk_remapping)
    typer.echo("Finished updating JSON files.")


if __name__ == "__main__":
    app()
