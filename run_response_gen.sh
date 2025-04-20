#!/bin/bash

export PROJ_DIR=$PWD
export DATA_DIR=$PWD/data
export OUTPUT_DIR=$PWD/dpo/runs
export PYTHONPATH=$PROJ_DIR

DATAPATHS=("$DATA_DIR/by_spec/wg_non_adv_prompts/gpt-4o_label_sup4-notsup4" "$DATA_DIR/by_spec/bt_gpt-4o_label/test_sup4-notsup4" "$DATA_DIR/by_spec/bt_gpt-4o_label/train_sup4-notsup4")

MODEL="gpt4o-unsafe-jack" 
MODEL_DISPLAY_NAME=$MODEL

ts=$(date +%F_%T)
echo "Starting inference at $ts"
for DATAPATH in "${DATAPATHS[@]}"
do
    echo "DATAPATH: $DATAPATH"
    python src/oai_inference.py \
        ${@} \
        --model $MODEL --model_display_name $MODEL_DISPLAY_NAME \
        --input_dataset $DATAPATH \
        -p prompt_templates/given_sys_generate.json \
        | tee -a "logs/oai_inference_$ts.log"
done

echo "log file: logs/oai_inference_$ts.log"

    # -a is optional if it's contained in prompt template
    
    # NEW combined eval
    # -p prompt_templates/addressed_eval.json prompt_templates/harmcat_eval_7cat_improved.json -r 0.3 \

    # -p prompt_templates/helpful_eval_strict_gpt4o.json prompt_templates/harmcat_eval_7cat.json -r 0.3 \

    # -p prompt_templates/helpful_eval_strict_gpt4o.json prompt_templates/harmful_eval_generic.json prompt_templates/harmful_except_7cat/template.json -r 0.1

    # -p prompt_templates/helpful_eval_strict_gpt4o.json prompt_templates/harmful_eval_generic.json prompt_templates/harmful_except_btsimple/template.json -r 0.1 \

    # combined eval
    # -p prompt_templates/helpful_eval_strict_gpt4o.json prompt_templates/harmful_eval_generic.json prompt_templates/harmful_except_cat/harmful_eval_except.json -r 0.1 \

    # generate response
    # -p prompt_templates/json_harm_spec/template.json
    # -p prompt_templates/vanilla_generate.json
    # -p prompt_templates/unsafe_generate.json
    # -p prompt_templates/ignore_harm_spec_generate/ignore_harm_spec_generate.json

    # allow certain categories
    # -a "[[YES]]_rate" -p prompt_templates/harmful_except_cat/harmful_eval_except_$spec.json -r 0.2

    # categorical harmful eval with harm category definition
    # -a "category_eval" -p prompt_templates/harmful_eval_by_cat_withdef.json -r 0.05

    # categorical harmful eval
    # TODO: find a suitable -r for this
    # -a "category_eval" -p prompt_templates/harmful_eval_by_cat.json -r 0.1

    # generic harmful eval
    # -a "[[YES]]_rate" -p prompt_templates/harmful_eval_generic.json -r 1

    # helpful eval
    # -p prompt_templates/helpful_eval_strict_gpt4o.json
    # OLD, NOT WORKING -p prompt_templates/helpful_eval.json