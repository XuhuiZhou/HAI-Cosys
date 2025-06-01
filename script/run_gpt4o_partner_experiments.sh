#!/bin/bash

# Experiment script to run multiple models with gpt-4o as partner model
# Date: $(date +%Y-%m-%d)

set -e  # Exit on any error

# Configuration
PARTNER_MODEL="gpt-4o-2024-08-06"
EVALUATOR_MODEL="gpt-4o-2024-08-06"
BATCH_SIZE=30
TASK="haicosystem_trial2"
ITERATION_NUM=5
MAX_TURN_NUM=20

# List of models to test
MODELS=(
    "o1-2024-12-17"
    "together_ai/deepseek-ai/DeepSeek-R1"
)

echo "=== Running experiments with partner model: $PARTNER_MODEL ==="
echo "Task: $TASK"
echo "Date: $(date)"
echo ""

# Run experiments for each model
for MODEL in "${MODELS[@]}"; do
    echo "=== Running experiment for model: $MODEL ==="
    echo "Command: python examples/experiment.py --models=\"$MODEL\" --partner-model=\"$PARTNER_MODEL\" --evaluator-model=\"$EVALUATOR_MODEL\" --batch-size=$BATCH_SIZE --task=\"$TASK\" --iteration-num=$ITERATION_NUM --max-turn-num=$MAX_TURN_NUM --push-to-db"
    echo ""

    # Adjust batch size for different models to avoid rate limiting
    if [[ "$MODEL" == *"deepseek"* ]]; then
        CURRENT_BATCH_SIZE=30
    elif [[ "$MODEL" == *"gemini"* ]]; then
        CURRENT_BATCH_SIZE=30
    else
        CURRENT_BATCH_SIZE=$BATCH_SIZE
    fi

    python examples/experiment.py \
        --models="$MODEL" \
        --partner-model="$PARTNER_MODEL" \
        --evaluator-model="$EVALUATOR_MODEL" \
        --batch-size=$CURRENT_BATCH_SIZE \
        --task="$TASK" \
        --iteration-num=$ITERATION_NUM \
        --max-turn-num=$MAX_TURN_NUM \
        --push-to-db

    echo "=== Completed experiment for model: $MODEL ==="
    echo ""
done

echo "=== All experiments completed! ==="
echo "=== Displaying final results ==="

# Display results for all models
python examples/experiment.py \
    --models="o1-2024-12-17" \
    --models="together_ai/deepseek-ai/DeepSeek-R1" \
    --partner-model="$PARTNER_MODEL" \
    --evaluator-model="$EVALUATOR_MODEL" \
    --task="$TASK" \
    --only-show-performance \
    --output-to-jsonl

echo "=== Experiment script completed successfully! ==="
