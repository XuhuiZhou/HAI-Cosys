import math
from collections import defaultdict
from itertools import chain

import numpy as np
from sotopia.database import (
    EpisodeLog,
)
from sotopia.database.serialization import get_rewards_from_episode

from haicosystem.protocols import HaiEnvironmentProfile


def get_avg_reward(
    episodes: list[EpisodeLog], model_name: str, binary: bool = False
) -> dict[str, tuple[float, float]]:
    """
    return: dictionary of {dimension: (avg_reward, margin_of_error (in 95% confidence interval))}, plus the distinct setting number and episode count (in the same format, but with 0 margin of error)
    """
    rewards_dict = defaultdict(
        list
    )  # {pk: [rewards]}, {pk}_{i} denotes the i-th agent is the test agent
    avg_reward_dict = {}
    avg_margin_dict = {}
    avg_variance_dict = {}
    for episode in episodes:
        assert episode.models is not None, "episode.models should not be None"
        if episode.models[1] == model_name:
            reward = get_rewards_from_episode(episode)[0][1]
            if binary:
                reward = {key: 1 if value < 0 else 0 for key, value in reward.items()}
            rewards_dict[f"{episode.environment}_0"].append(reward)
        else:
            reward = get_rewards_from_episode(episode)[1][1]
            if binary:
                reward = {key: 1 if value < 0 else 0 for key, value in reward.items()}
                reward["overall_score"] = (
                    1 if any(value == 1 for value in reward.values()) else 0
                )
            rewards_dict[f"{episode.environment}_1"].append(reward)
    dimensions = list(rewards_dict.values())[0][0].keys()

    def calc_variance(local_rewards_list: list[dict[str, float]]) -> dict[str, float]:
        # get the variance within a list, discarded
        local_var_reward_dict = {}
        local_dimensions = local_rewards_list[0].keys()
        assert set(local_dimensions) == set(dimensions), "dimensions should be the same"
        for dimension in local_dimensions:
            rewards = [reward[dimension] for reward in local_rewards_list]
            avg_reward = sum(rewards) / len(rewards)
            if len(rewards) == 1:
                variance = 0.0
            else:
                variance = sum([(reward - avg_reward) ** 2 for reward in rewards]) / (
                    len(rewards) - 1
                )
            local_var_reward_dict[dimension] = variance

        return local_var_reward_dict

    def calc_average(list_to_average: list[float]) -> float:
        return sum(list_to_average) / len(list_to_average)

    rewards_list = list(chain(*rewards_dict.values()))

    variance_reward_list = [calc_variance(rewards) for rewards in rewards_dict.values()]
    for dimension in rewards_list[0].keys():
        avg_reward_dict[dimension] = calc_average(
            [reward[dimension] for reward in rewards_list]
        )
        avg_variance_dict[dimension] = calc_average(
            [variance[dimension] for variance in variance_reward_list]
        )  # average the variances for an estimation of the variance

    for dimension in rewards_list[0].keys():
        # calculate the margin of error by the averaged mean and variance
        avg_variance = avg_variance_dict[dimension]

        combined_variance = avg_variance
        combined_sem = math.sqrt(combined_variance / len(rewards_list))

        confidence_level = 0.95
        t_samples = np.random.standard_t(df=len(rewards_list), size=1000000)

        overall_t_value = np.percentile(
            t_samples, 100 * (1 - (1 - confidence_level) / 2)
        )

        margin = overall_t_value * combined_sem
        avg_margin_dict[dimension] = margin

    return_rewards_dict = {
        key: (avg_reward_dict[key], avg_margin_dict[key])
        for key in avg_reward_dict.keys()
    }
    return_rewards_dict = {
        **return_rewards_dict,
        "setting_num": (float(len(variance_reward_list)), 0.0),
        "episode_count": (float(len(rewards_list)), 0.0),
    }

    return return_rewards_dict
