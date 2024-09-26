from collections import Counter

import pandas as pd
import rich
import typer
from scipy.stats import pearsonr
from sklearn.metrics import cohen_kappa_score  # type: ignore
from sotopia.database import EpisodeLog
from sotopia.database.serialization import get_rewards_from_episode
from typer import Typer

app = Typer(pretty_exceptions_show_locals=False)


@app.command()
def calculate_inter_annotator_agreement(csv_path: str) -> None:
    df = pd.read_csv(csv_path)
    episode_pks = df["episode_pk"].to_list()
    episode_counter = Counter(episode_pks)

    df_1 = pd.DataFrame()
    df_2 = pd.DataFrame()

    for episode_pk, count in episode_counter.items():
        if count == 2:
            df_1 = pd.concat([df_1, df[df["episode_pk"] == episode_pk].iloc[[0]]])
            df_2 = pd.concat([df_2, df[df["episode_pk"] == episode_pk].iloc[[1]]])

    df_1.reset_index(drop=True, inplace=True)
    df_2.reset_index(drop=True, inplace=True)

    categories = [
        "targeted_safety_risks",
        "system_and_operational_risks",
        "content_safety_risks",
        "societal_risks",
        "legal_and_rights_related_risks",
        "efficiency",
        "goal",
    ]
    df_1_ordered = df_1.sort_values(by="episode_pk")
    df_2_ordered = df_2.sort_values(by="episode_pk")
    for category in categories:
        # cohen's kappa
        cohen_kappa = cohen_kappa_score(df_1_ordered[category], df_2_ordered[category])
        print(f"{category}: Cohen's kappa = {cohen_kappa}")

        # pearson correlation
        pearson_correlation = pearsonr(df_1_ordered[category], df_2_ordered[category])
        print(
            f"{category}: Pearson correlation = {pearson_correlation.statistic}, p-value = {pearson_correlation.pvalue}"
        )


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
    overall_ = []
    overall_m = []
    for category in categories:
        if category in df.columns:
            if category != "goal" and category != "efficiency":
                overall_.append(pd.Series(rewards[category]).astype(float) != 0)
                overall_m.append(pd.Series(df[category]).astype(float) != 0)
            accuracy[category] = (
                (pd.Series(df[category]).astype(float) != 0)
                .eq(pd.Series(rewards[category]).astype(float) != 0)
                .mean()
            )
        else:
            accuracy[category] = 0.0

    overall_model = [
        1 if any(row != 0 for row in rows) else 0 for rows in zip(*overall_)
    ]
    overall_human = [
        1 if any(row != 0 for row in rows) else 0 for rows in zip(*overall_m)
    ]
    overall_mean = (pd.Series(overall_model) == pd.Series(overall_human)).mean()
    for category, acc in accuracy.items():
        print(f"{category}: Accuracy = {acc}")
    print(f"Overall accuracy = {overall_mean}")


if __name__ == "__main__":
    app()
