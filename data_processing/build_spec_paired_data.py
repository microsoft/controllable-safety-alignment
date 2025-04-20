'''
Given 
    - a set of specs $s_1,\dots, s_n$
    - a set of prompts $P_i=\{p_{i,1},\dots,p_{i,l_i}\}$ for each spec $s_i$
    - a safety-oriented (not very helpful) model $M_\\text{safe}$ (e.g. GPT-4), and a helpful-oriented (not very safe) model $M_\text{help}$ (e.g. GPT-4 without safety alignment)
    - a function $\\texttt{SYSP}(s)$ that convert a spec into a natural language (or structured, e.g. json) system prompt

We generate data where each example is (system prompt, prompt, chosen response, rejected response):

input: safe model generation across all specs, unsafe model generation across all specs, system prompt (in meta prompt template format)

'''
import sys
import os
import argparse
from datasets import load_from_disk, Dataset
from src.jack_utils import load_json, import_module_from_path, convert_list_of_dicts_to_dict_of_lists
import random

def obtain_get_messages_func(prompt_template_file):
    prompt_template = load_json(prompt_template_file)
    assert prompt_template.get('meta_path') is not None
    # meta template
    # meta_path contains path to a python file that contains a function def get_messages(dataset_name: str) which returns a list of messages given from the dataset name (i.e. the spec)
    get_messages = import_module_from_path(prompt_template['name']+'_meta_module', prompt_template['meta_path']).get_messages
    return get_messages

def is_spec_a_subset_of_spec_b(spec_a: str, spec_b: str):
    def str_spec_to_set(spec):
        return set([s for s in spec.split('-') if len(s) > 0])
    return str_spec_to_set(spec_a).issubset(str_spec_to_set(spec_b))



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prompt_template', type=str, required=True)
    parser.add_argument('--safe_generation', type=str, required=True)
    parser.add_argument('--helpful_generation', type=str, required=True)
    parser.add_argument('-s', '--spec_j_prompt_start_idx', type=int, default=0)
    parser.add_argument('-m', '--max_prompt_per_spec_j', type=int, default=sys.maxsize)
    parser.add_argument('--output', type=str, required=True)
    parser.add_argument('--seed', type=int, default=0)

    # options
    parser.add_argument('--balance_domain', action='store_true', help='make sure in-domain and out-of-domain examples are balanced by downsampling out-of-domain examples')
    
    args = parser.parse_args()
    random.seed(args.seed)
    print(f'args: {vars(args)}')
    assert not os.path.exists(args.output)
    processed_data = []

    get_messages = obtain_get_messages_func(args.prompt_template)
    response_datasets = [load_from_disk(path) for path in [args.safe_generation, args.helpful_generation]]

    specs = response_datasets[0].keys()
    for spec_i in specs:
        spec_i_processed_data = {'id': [], 'ood': []}
        for spec_j in specs:
            if len(response_datasets[0][spec_j]) != len(response_datasets[1][spec_j]):
                print(f'Warning: {spec_j} has different number of prompts in the two datasets. Will only consider common prompts.')
            len_j = min(len(response_datasets[0][spec_j]), len(response_datasets[1][spec_j]))

            is_in_domain = is_spec_a_subset_of_spec_b(spec_j, spec_i) and not (spec_j == '--') # if spec_j is '--', it should be a general prompt (from the safe categroy); if so there is nothing to learn for dpo. however in beavertails, it does containing some random unsafe prompts. so if we sample a prompt from '--', currently it's always treated as ood
                    # in-domain, aim for helpfulness (index 1)
            if is_in_domain:
                print(f'In-domain situation: spec_i={spec_i}, spec_j={spec_j}')

            # assumption: the prompts in response_datasets[...][spec_j] will only **at most** induce harms within spec_j
            spec_j_processed_data = []
            for k in range(args.spec_j_prompt_start_idx, min(len_j, args.spec_j_prompt_start_idx+args.max_prompt_per_spec_j)):
                assert response_datasets[0][spec_j][k]['prompt'] == response_datasets[1][spec_j][k]['prompt']
                system_prompt = get_messages(spec_i)[0]['content'] # system prompt can be dynamic, so we need to call get_messages for every example
                prompt = response_datasets[0][spec_j][k]['prompt']
                if is_in_domain:
                    datapoint = {
                        'system_prompt': system_prompt,
                        'prompt': prompt,
                        'chosen_response': response_datasets[1][spec_j][k]['response'],
                        'rejected_response': response_datasets[0][spec_j][k]['response'],
                        'chosen_idx': 1,
                        'spec_i': spec_i,
                        'spec_j': spec_j
                    }
                    # breakpoint()
                else:
                    # with exception: both spec_i and spec_j are safe, we still use the safe model
                    # out-of-domain, aim for safety (index 0)
                    datapoint = {
                        'system_prompt': system_prompt,
                        'prompt': prompt,
                        'chosen_response': response_datasets[0][spec_j][k]['response'],
                        'rejected_response': response_datasets[1][spec_j][k]['response'],
                        'chosen_idx': 0,
                        'spec_i': spec_i,
                        'spec_j': spec_j
                    }
                spec_j_processed_data.append(datapoint)
            domain = 'id' if is_in_domain else 'ood'
            spec_i_processed_data[domain].extend(spec_j_processed_data)
        if args.balance_domain:
            n_id = len(spec_i_processed_data['id'])
            n_ood = len(spec_i_processed_data['ood'])
            if n_ood > n_id:
                spec_i_processed_data['ood'] = random.sample(spec_i_processed_data['ood'], n_id)
                print(f'Warning: downsampling ood examples for {spec_i} from {n_ood} to {n_id}')
            else:
                spec_i_processed_data['id'] = random.sample(spec_i_processed_data['id'], n_ood)
                print(f'Warning: downsampling id examples for {spec_i} from {n_id} to {n_ood}')
        processed_data.extend(spec_i_processed_data['id'])
        processed_data.extend(spec_i_processed_data['ood'])
        print(f'processed {spec_i}, id: {len(spec_i_processed_data["id"])}, ood: {len(spec_i_processed_data["ood"])}')

            
    
    print('total number of examples:', len(processed_data))
    dataset = Dataset.from_dict(convert_list_of_dicts_to_dict_of_lists(processed_data))
    dataset.save_to_disk(args.output)
    print(f'Saved to {args.output}')
