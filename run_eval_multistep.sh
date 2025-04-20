#!/bin/bash

export PROJ_DIR=$PWD
export DATA_DIR=$PWD/data
export OUTPUT_DIR=$PWD/dpo/runs
export PYTHONPATH=$PROJ_DIR


DATAPATHS=("$DATA_DIR/testsets/bt_7cat_5spec_testset_400" "$DATA_DIR/testsets/bt_7cat_test_400_unseencat")

MODEL="gpt-4o"
MODEL_DISPLAY_NAME=$MODEL

###
# LOOK HERE! COMMAND LINE ARGUMENTS
###
CANDIDATE_MODEL="${1:-$MODEL_DIR/llama3-sft}"
CANDIDATE_MODEL_DISPLAY_NAME="${2:-llama3-sft}"
SYSTEM_PROMPT_TEMPLATE_NAME="${3:-ignore_harm_7cat_vary10}"
###
remaining_args=("${@:4}")

step_2_outs=()
for DATAPATH in "${DATAPATHS[@]}"
do
    echo "DATAPATH: $DATAPATH"
    echo "STEP 1: generate with candidate model. MODEL: $CANDIDATE_MODEL_DISPLAY_NAME"
    PROMPT_TEMPLATE_PATH="prompt_templates/$SYSTEM_PROMPT_TEMPLATE_NAME/template.json"
    if [ ! -f "$PROMPT_TEMPLATE_PATH" ]; then
        PROMPT_TEMPLATE_PATH="prompt_templates/$SYSTEM_PROMPT_TEMPLATE_NAME.json"
    fi
    echo "prompt template path: $PROMPT_TEMPLATE_PATH"
    ts=$(date +%F_%T)
    echo "Starting inference at $ts"
    echo "DATAPATH: $DATAPATH"
    python src/oai_inference.py \
        ${remaining_args[@]} \
        --model $CANDIDATE_MODEL --model_display_name $CANDIDATE_MODEL_DISPLAY_NAME \
        --input_dataset $DATAPATH \
        -p $PROMPT_TEMPLATE_PATH \
        | tee -a "logs/oai_inference_$ts.log"

    STEP1_LOG_PATH="logs/oai_inference_$ts.log"
    STEP1_OUTPUT_PATH=${DATAPATH}_model-${CANDIDATE_MODEL_DISPLAY_NAME}_${SYSTEM_PROMPT_TEMPLATE_NAME}

    echo "STEP 1 log: $STEP1_LOG_PATH"
    echo "STEP 1 output: $STEP1_OUTPUT_PATH"

    echo "STEP 2: generate evaluation response with the evaluator model. MODEL: $MODEL_DISPLAY_NAME"
    ts=$(date +%F_%T)
    echo "Starting inference at $ts"
    echo "DATAPATH: $STEP1_OUTPUT_PATH"
    python src/oai_inference.py \
        ${remaining_args[@]} \
        --model $MODEL --model_display_name $MODEL_DISPLAY_NAME \
        --input_dataset $STEP1_OUTPUT_PATH \
        -p prompt_templates/harmcat_e7+1_gr.json prompt_templates/resp_eval_0-5_gr.json \
        | tee -a "logs/oai_inference_$ts.log"

    STEP2_LOG_PATH="logs/oai_inference_$ts.log"
    STEP2_OUTPUT_PATH=${STEP1_OUTPUT_PATH}_model-${MODEL_DISPLAY_NAME}_harmcat_e7+1_gr+resp_eval_0-5_gr

    echo "STEP 1 log: $STEP1_LOG_PATH"
    echo "STEP 2 log: $STEP2_LOG_PATH"
    echo "STEP 1 output: $STEP1_OUTPUT_PATH"
    echo "STEP 2 output: $STEP2_OUTPUT_PATH"
    cp $STEP2_LOG_PATH $STEP2_OUTPUT_PATH/step2_log.txt
    step_2_outs+=($STEP2_OUTPUT_PATH)
done


echo "STEP 3: produce metrics"
for STEP2_OUTPUT_PATH in "${step_2_outs[@]}"
do
    echo "STEP 2 output: $STEP2_OUTPUT_PATH"
    echo "Grand results:"
    python src/produce_metrics.py $STEP2_OUTPUT_PATH
done
