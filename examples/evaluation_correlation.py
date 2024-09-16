import pandas as pd
import typer
import rich
from scipy.stats import pearsonr

from sotopia.database import EpisodeLog
from typer import Typer

# from haicosystem.utils.render import render_for_humans, rich_rendering

app = Typer()

@app.command()
def calculate_pearson_correlation(episode_pk, csv_path) -> None:
    df = pd.read_csv(csv_path)

     
    episode = EpisodeLog.get(df['episode_pk'])
    # TO-DO extract annotations from episode rewrad
    # df['agent_annotation'] = df['episode_pk'].apply(EpisodeLog.get)

    correlations = {}

    categories = ['targeted_safety_risks', 'system_and_operational_risks', 'content_safety_risks', 
                  'societal_risks', 'legal_and_rights_related_risks', 'efficiency', 'goal']
    
    
    for category in categories:
        if category in df.columns:
            corr, p_value = pearsonr(df['agent_annotation'], df[category])
            correlations[category] = (corr, p_value)
        else:
            correlations[category] = ('N/A', 'Category not found in CSV')

    for category, (corr, p_value) in correlations.items():
        print(f"{category}: Pearson correlation = {corr}, p-value = {p_value}")

if __name__ == "__main__":
    app()
