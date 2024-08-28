## Experiment Log

### 1. Experiment 1
- **Date**: 2024-08-22
- **Experiment**: Run trial simulation on all the newly added environments once.
```bash
python examples/experiment.py --models="gpt-4-turbo" --partner-model="gpt-4o-2024-08-06" --evaluator-model="gpt-4o-2024-08-06" --batch-size=4 --task="haicosystem_trial2" --push-to-db --iteration-num=1 --only-show-performance > experiment_output.log 2>&1
```

```bash
python examples/experiment.py --models="gpt-3.5-turbo" --partner-model="gpt-4o-2024-08-06" --evaluator-model="gpt-4o-2024-08-06" --batch-size=4 --task="haicosystem_trial2" --push-to-db --iteration-num=1 --only-show-performance
```
- **Notes**: a. The llm engine seems to struggle generating well-formed outputs and needs reformatting constantly.
- **Results**: The model was overfitting after 20 epochs.
