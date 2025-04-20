#!/bin/bash

model=llama3.1-8b-instruct
dataset=cosalign-train

export PROJ_DIR=$PWD
export DATA_DIR=$PWD/data
export OUTPUT_DIR=$PWD/dpo/runs
export PYTHONPATH=$PROJ_DIR

# DPO
# lr=5e-7
# warmup_steps=150
# n_epochs=3

model_name=$model
exp_name=${model_name}-DPO-${dataset}
ulimit -n 64000; python -u $PROJ_DIR/dpo/train.py \
    model=$model \
    datasets=[$dataset] \
    loss=dpo loss.beta=0.1 \
    exp_name=$exp_name \
    trainer=FSDPTrainer sample_during_eval=false model.fsdp_policy_mp=bfloat16 gradient_accumulation_steps=4 \
    eval_every=5100

