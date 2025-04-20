#!/bin/bash

export PROJ_DIR=$PWD
export DATA_DIR=$PWD/data
export OUTPUT_DIR=$PWD/dpo/runs
export PYTHONPATH=$PROJ_DIR

# ==== V1 ====
# V1 test
# PROMPT_DATASET="data/by_spec/bt_multi_4-gpt-4-32k_label/test"
# PROMPT2RESPONSE="data/prompt2response/bt_multi_4-gpt-4-32k_label/V1-given_sys_combine/test.json"
# OUTPUT="data/paired/bt_multi_4-gpt-4-32k_label/V1-given_sys_combine/test"
# V1 train
# PROMPT_DATASET="data/by_spec/bt_multi_4-gpt-4-32k_label/train"
# PROMPT2RESPONSE="data/prompt2response/bt_multi_4-gpt-4-32k_label/V1-given_sys_combine/train.json"
# OUTPUT="data/paired/bt_multi_4-gpt-4-32k_label/V1-given_sys_combine/train"


# ==== V2 ====
# V2 test-no_em
# PROMPT_DATASET="data/by_spec/bt_multi_4-gpt-4-32k_label/test"
# PROMPT2RESPONSE="data/prompt2response/bt_multi_4-gpt-4-32k_label/V2-given_sys-a+h/test-no_em.json"
# OUTPUT="data/paired/bt_multi_4-gpt-4-32k_label/V2-given_sys-a+h/test-no_em"

# V2 test-no_em-small
# PROMPT_DATASET="data/by_spec/bt_multi_4-gpt-4-32k_label/test"
# PROMPT2RESPONSE="data/prompt2response/bt_multi_4-gpt-4-32k_label/V2-given_sys-a+h/test-no_em.json"
# OUTPUT="data/paired/bt_multi_4-gpt-4-32k_label/V2-given_sys-a+h/test-no_em-small"
# EXTRA_ARGS="--max_prompt_per_spec_j 50"

# V2 train-no_em
# PROMPT_DATASET="data/by_spec/bt_multi_4-gpt-4-32k_label/train"
# PROMPT2RESPONSE="data/prompt2response/bt_multi_4-gpt-4-32k_label/V2-given_sys-a+h/train-no_em.json"
# OUTPUT="data/paired/bt_multi_4-gpt-4-32k_label/V2-given_sys-a+h/train-no_em"


# ==== V3 ====
# V3 test
# PROMPT_DATASET="data/by_spec/bt_multi_4-gpt-4-32k_label/test"
# PROMPT2RESPONSE="data/prompt2response/bt_multi_4-gpt-4-32k_label/V3-given_sys-a+h/test.json"
# OUTPUT="data/paired/bt_multi_4-gpt-4-32k_label/V3-given_sys-a+h/test"

# V3 test-small
# PROMPT_DATASET="data/by_spec/bt_multi_4-gpt-4-32k_label/test"
# PROMPT2RESPONSE="data/prompt2response/bt_multi_4-gpt-4-32k_label/V3-given_sys-a+h/test.json"
# OUTPUT="data/paired/bt_multi_4-gpt-4-32k_label/V3-given_sys-a+h/test-small"
# EXTRA_ARGS="--max_prompt_per_spec_j 50"

# V3 train
# PROMPT_DATASET="data/by_spec/bt_multi_4-gpt-4-32k_label/train"
# PROMPT2RESPONSE="data/prompt2response/bt_multi_4-gpt-4-32k_label/V3-given_sys-a+h/train.json"
# OUTPUT="data/paired/bt_multi_4-gpt-4-32k_label/V3-given_sys-a+h/train"

# ==== V4 ====
# V4 test-small
# PROMPT_DATASET=("data/by_spec/bt_gpt-4o_label/test")
# PROMPT2RESPONSE="data/prompt2response/V4-bt_gpt-4o+wg/test.json"
# OUTPUT="data/paired/V4-bt_gpt-4o+wg/test-small"
# EXTRA_ARGS="--max_prompt_per_spec_j 50"

# V4 train
# PROMPT_DATASET=("data/by_spec/bt_gpt-4o_label/train" "data/by_spec/wg_non_adv_prompts/gpt-4o_label")
# PROMPT2RESPONSE="data/prompt2response/V4-bt_gpt-4o+wg/train.json"
# OUTPUT="data/paired/V4-bt_gpt-4o+wg/train"

# V4 train_2000
# PROMPT_DATASET=("data/by_spec/bt_gpt-4o_label/train" "data/by_spec/wg_non_adv_prompts/gpt-4o_label")
# PROMPT2RESPONSE="data/prompt2response/V4-bt_gpt-4o+wg/train.json"
# OUTPUT="data/paired/V4-bt_gpt-4o+wg/train_2000"
# EXTRA_ARGS="--max_prompt_per_spec_j 2000"

# ==== V5 ====
TRAIN_CATEGORIES="data_processing/train_categories/single_4.json"
# V5 test-small
# PROMPT_DATASET=("data/by_spec/bt_gpt-4o_label/test")
# PROMPT2RESPONSE="data/prompt2response/V5-bt+wg-addr_imp/test.json"
# OUTPUT="data/paired/V5-bt+wg-addr_imp/test-small"
# EXTRA_ARGS="--max_prompt_per_spec_j 50"

# V5 train
# PROMPT_DATASET=("data/by_spec/bt_gpt-4o_label/train" "data/by_spec/wg_non_adv_prompts/gpt-4o_label")
# PROMPT2RESPONSE="data/prompt2response/V5-bt+wg-addr_imp/train.json"
# OUTPUT="data/paired/V5-bt+wg-addr_imp/train"

# V5 train_7cat
PROMPT_DATASET=("data/by_spec/bt_gpt-4o_label/train" "data/by_spec/wg_non_adv_prompts/gpt-4o_label")
PROMPT2RESPONSE="data/prompt2response/V5-bt+wg-addr_imp/train.json"
OUTPUT="data/paired/V5-bt+wg-addr_imp/train_7cat"
TRAIN_CATEGORIES="data_processing/train_categories/single_7.json"


python data_processing/build_spec_paired_data_simple.py \
    --prompt_template prompt_templates/ignore_harm_7cat_vary10/template.json \
    --modes "mixed" \
    --train_categories $TRAIN_CATEGORIES \
    --output $OUTPUT \
    --prompt_dataset "${PROMPT_DATASET[@]}" \
    --prompt2response $PROMPT2RESPONSE \
    $EXTRA_ARGS
