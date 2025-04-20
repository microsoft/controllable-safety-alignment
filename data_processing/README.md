# Steps to process training data for SFT / DPO

1. (Optional) Obtain a dataset of prompts with labels. See `notebooks/compare_gpt_label_with_cluster.ipynb` and `data_processing/prepare_raw_labeled_prompt_for_pairing.py`
2. (Optional) Run `data_processing/prepare_raw_labeled_prompt_for_pairing.py` to (1) parse raw categorical labeling response (2) select desired labels to consider for train/eval (3) format each split into a DatasetDict where each split is a spec, with column 'prompt' containing prompts of that spec. This produces a "by_spec" dataset.

We provide our processed "by_spec" dataset for BeaverTails and Wildguard as canonical examples. They are located in `data/by_spec/bt_gpt-4o_label` and `data/by_spec/wg_non_adv_prompts`.

3. Get diverse generation of the by_spec dataset by generating responses with different models (both safe and unsafe models). To do this, call both safe and unsafe model on either vanilla template `prompt_templates/vanilla_generate.json` or the safety spec `prompt_templates/ignore_harm_7cat_vary10/template.json` with `src/oai_inference.py`. First reformat data with `data_processing/add_spec_i_sysprompt.py`. Then use script `run_response_gen.sh`
4. Get addressed / harm category label of the response by running `run_response_labeling.sh`
5. Get the prompt2response dict by running `data_processing/aggregate_responses.ipynb`
6. FINALLY! get the paired dataset by running `data_processing/build_paired_data_prompt2response.sh` to call `data_processing/build_spec_paired_data_simple.py`