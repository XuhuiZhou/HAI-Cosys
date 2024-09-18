import pandas as pd
import rich
import typer
from scipy.stats import pearsonr
from sotopia.database import EpisodeLog
from sotopia.database.serialization import get_rewards_from_episode
from typer import Typer

app = Typer()


def get_rewards_from_episodes(
    episode_pks: list[str], categories: list[str]
) -> dict[str, list[float]]:
    rewards: dict[str, list[float]] = {category: [] for category in categories}
    for episode_pk in episode_pks:
        episode = EpisodeLog.get(episode_pk)
        reward = get_rewards_from_episode(episode)
        reward_agent_2 = reward[1][1]
        for category in categories:
            rewards[category].append(float(reward_agent_2[category]))
    return rewards


@app.command()
def calculate_pearson_correlation_and_accuracy(csv_path: str) -> None:
    df = pd.read_csv(csv_path)

    categories = [
        "targeted_safety_risks",
        "system_and_operational_risks",
        "content_safety_risks",
        "societal_risks",
        "legal_and_rights_related_risks",
        "efficiency",
        "goal",
    ]
    rewards = get_rewards_from_episodes(df["episode_pk"].to_list(), categories)
    correlations: dict[str, tuple[float, float]] = {}
    for category in categories:
        if category in df.columns:
            result = pearsonr(df[category].astype(float), rewards[category])
            correlations[category] = (result.statistic, result.pvalue)
        else:
            correlations[category] = (0.0, 0.0)

    for category, (corr, p_value) in correlations.items():
        print(f"{category}: Pearson correlation = {corr}, p-value = {p_value}")

    # Calculate accuracy
    accuracy = {}
    for category in categories:
        if category in df.columns:
            accuracy[category] = (
                (pd.Series(df[category]).astype(float) != 0)
                .eq(pd.Series(rewards[category]).astype(float) != 0)
                .mean()
            )
        else:
            accuracy[category] = 0.0

    for category, acc in accuracy.items():
        print(f"{category}: Accuracy = {acc}")


if __name__ == "__main__":
    app()
