#!/bin/bash

export PROJ_DIR=$PWD
export DATA_DIR=$PWD/data
export OUTPUT_DIR=$PWD/dpo/runs
export PYTHONPATH=$PROJ_DIR

DATAPATHS=("data/testsets/bt_7cat_5spec_testset_400_model-llama3.1-8b-instruct-SFT-V5-bt+wg-addr_imp-DPO_ignore_harm_7cat_vary10_model-gpt-4o_harmcat_e7+1_gr+resp_eval_0-5_gr" "data/testsets/bt_7cat_test_400_unseencat_model-llama3.1-8b-instruct-SFT-V5-bt+wg-addr_imp-DPO_ignore_harm_7cat_vary10_model-gpt-4o_harmcat_e7+1_gr+resp_eval_0-5_gr" )

MODEL=$1
MODEL_DISPLAY_NAME=$2
remaining_args=("${@:3}")

ts=$(date +%F_%T)
echo "Starting inference at $ts"
for DATAPATH in "${DATAPATHS[@]}"
do
    echo "DATAPATH: $DATAPATH"
    python src/oai_inference.py \
        ${remaining_args[@]} \
        --model $MODEL --model_display_name $MODEL_DISPLAY_NAME \
        --input_dataset $DATAPATH \
        -p prompt_templates/harmcat_e7+1_gr.json \
        --response_key harm_categorization_response_self \
        | tee -a "logs/oai_inference_$ts.log"
done

echo "log file: logs/oai_inference_$ts.log"
