## Experiment Log

### 1. Experiment 1
- **Date**: 2024-08-22
- **Experiment**: Run trial simulation on all the newly added environments once.
```bash
python examples/experiment.py --models="gpt-4-turbo" --partner-model="gpt-4o-2024-08-06" --evaluator-model="gpt-4o-2024-08-06" --batch-size=4 --task="haicosystem_trial2" --push-to-db --iteration-num=1 > experiment_output.log 2>&1
```
note: it actually means `gpt-4-turbo-2024-04-09`

```bash
python examples/experiment.py --models="gpt-3.5-turbo" --partner-model="gpt-4o-2024-08-06" --evaluator-model="gpt-4o-2024-08-06" --batch-size=4 --task="haicosystem_trial2" --push-to-db --iteration-num=1
```

note: it actually means `gpt-3.5-turbo-0613`

```bash
python examples/experiment.py --models="together_ai/meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo" --partner-model="gpt-4o-2024-08-06" --evaluator-model="gpt-4o-2024-08-06" --batch-size=4 --task="haicosystem_trial2" --push-to-db --iteration-num=1
```

```bash
python examples/experiment.py --models="together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo" --partner-model="gpt-4o-2024-08-06" --evaluator-model="gpt-4o-2024-08-06" --batch-size=4 --task="haicosystem_trial2" --push-to-db --iteration-num=1
```

- **Notes**: a. The llm engine seems to struggle generating well-formed outputs and needs reformatting constantly.
- **Results**: The model was overfitting after 20 epochs.


### 2. Experiment 2
- **Date**: 2024-09-03

- **Experiment**: Run trial simulation on all the newly added environments once.
```bash
python examples/experiment.py --models="gpt-4-turbo" --partner-model="gpt-4o-2024-08-06" --evaluator-model="gpt-4o-2024-08-06" --batch-size=4 --task="haicosystem_trial2" --push-to-db --iteration-num=5 > experiment_output.log 2>&1
```
note: it actually means `gpt-4-1106-preview`

```bash
python examples/experiment.py --models="gpt-3.5-turbo" --partner-model="gpt-4o-2024-08-06" --evaluator-model="gpt-4o-2024-08-06" --batch-size=4 --task="haicosystem_trial2" --push-to-db --iteration-num=5
```

note: it actually means `gpt-3.5-turbo-0613`

```bash
python examples/experiment.py --models="together_ai/meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo" --partner-model="gpt-4o-2024-08-06" --evaluator-model="gpt-4o-2024-08-06" --batch-size=4 --task="haicosystem_trial2" --push-to-db --iteration-num=5
```

```bash
python examples/experiment.py --models="together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo" --partner-model="gpt-4o-2024-08-06" --evaluator-model="gpt-4o-2024-08-06" --batch-size=4 --task="haicosystem_trial2" --push-to-db --iteration-num=5
```

- **Notes**: a. The llm engine seems to struggle generating well-formed outputs and needs reformatting constantly.
- **Results**: The model was overfitting after 20 epochs.


### 3. Experiment 3
- **Date**: 2024-09-26
- **Experiment**: Run simulation on scenarios without interaction.
```bash[discarded]
python examples/experiment.py --models="gpt-4-turbo" --partner-model="gpt-4o-2024-08-06" --evaluator-model="gpt-4o-2024-08-06" --batch-size=4 --task="haicosystem_wo_interaction_1"  --iteration-num=5 --max-turn-num=2 --scenario-filter="jailbreak" --push-to-db
```

- **Notes**: The human agent won't say the jailbreaking sentence faithfully.

```bash
python examples/experiment.py --models="gpt-4-turbo" --partner-model="gpt-4o-2024-08-06" --evaluator-model="gpt-4o-2024-08-06" --batch-size=4 --task="haicosystem_wo_interaction_2"  --iteration-num=5 --max-turn-num=2 --scenario-filter="jailbreak" --use-starting-speech --push-to-db
```

- **Notes**: With the starting speech, the problem is being fixed.


### 4. Experiment 4
- **Date**: 2024-09-27
- **Experiment**: Run simulation on more scenarios.
```bash
python examples/experiment.py --models="gpt-4-turbo" --partner-model="gpt-4o-2024-08-06" --evaluator-model="gpt-4o-2024-08-06" --batch-size=4 --task="haicosystem_trial2" --iteration-num=5 --push-to-db
```

```bash
python examples/experiment.py --models="together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo" --partner-model="gpt-4o-2024-08-06" --evaluator-model="gpt-4o-2024-08-06" --batch-size=4 --task="haicosystem_trial2" --iteration-num=5 --push-to-db
```

- **Notes**: The model was overfitting after 20 epochs.
