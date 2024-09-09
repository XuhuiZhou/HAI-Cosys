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
