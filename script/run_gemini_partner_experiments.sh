#!/bin/bash

# Experiment script to run multiple models with gemini/gemini-2.5-flash-preview-05-20 as partner model
# Date: $(date +%Y-%m-%d)

set -e  # Exit on any error

# Configuration
PARTNER_MODEL="gemini/gemini-2.5-flash-preview-05-20"
EVALUATOR_MODEL="gpt-4o-2024-08-06"
BATCH_SIZE=30
TASK="haicosystem_gemini_partner"
ITERATION_NUM=5
MAX_TURN_NUM=20

# List of models to test
MODELS=(
    "gpt-4-turbo"
    "gpt-3.5-turbo"
    "together_ai/meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo"
    "together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
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

    # Adjust batch size for larger models to avoid rate limiting
    if [[ "$MODEL" == *"405B"* ]]; then
        CURRENT_BATCH_SIZE=30
    elif [[ "$MODEL" == *"70B"* ]]; then
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
    --models="gpt-4-turbo" \
    --models="gpt-3.5-turbo" \
    --models="together_ai/meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo" \
    --models="together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo" \
    --partner-model="$PARTNER_MODEL" \
    --evaluator-model="$EVALUATOR_MODEL" \
    --task="$TASK" \
    --only-show-performance \
    --output-to-jsonl

echo "=== Experiment script completed successfully! ==="
