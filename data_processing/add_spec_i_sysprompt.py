'''
given a dataset dict where split name is prompt harm categories, and each example contain 'prompt', for each 
'''
import argparse
from datasets import load_from_disk, Dataset, DatasetDict
import random
from data_processing.build_spec_paired_data_simple import obtain_get_messages_func, spec_list_to_str
from src.produce_metrics import cat_str_to_list
import os

def parse_setup(setup):
    return [s.split('/') for s in setup.split('-')]

def get_all_seen_categories(dataset):
    all_seen_categories = set()
    for split_name in dataset.keys():
        all_seen_categories.update(cat_str_to_list(split_name))
    return list(all_seen_categories)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)

    parser.add_argument('--prompt_template', type=str, default='prompt_templates/ignore_harm_7cat_vary10/template.json')
    parser.add_argument('--setup', type=str, default='superset/4-not_superset/4')

    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()
    setups = parse_setup(args.setup)
    random.seed(args.seed)
    assert not os.path.exists(args.output), f'{args.output} already exists'

    get_messages = obtain_get_messages_func(args.prompt_template)
    dataset = load_from_disk(args.dataset)

    all_seen_categories = get_all_seen_categories(dataset)

    new_dict = {}
    for spec_j, split in dataset.items():
        new_split = {
            'system_prompt': [],
            'prompt': [],
            'spec_i': [],
            'spec_j': [],
        }
        for ex in split:
            for mode, repeat in setups:
                for _ in range(int(repeat)):
                    messages, spec_i_list = get_messages(spec_j, mode=mode, dataset_categories=all_seen_categories, return_actual_specs=True)
                    spec_i = spec_list_to_str(spec_i_list)
                    system_prompt = messages[0]['content']
                    
                    new_split['system_prompt'].append(system_prompt)
                    new_split['prompt'].append(ex['prompt'])
                    new_split['spec_i'].append(spec_i)
                    new_split['spec_j'].append(spec_j)
        new_dict[spec_j] = Dataset.from_dict(new_split)
    new_dataset = DatasetDict(new_dict)
    new_dataset.save_to_disk(args.output)
    print(f'Saved to {args.output}')
    print(new_dataset)
    with open(os.path.join(args.output, 'info.txt'), 'w') as f:
        f.write(f'args: {vars(args)}\n')
        f.write(f'new_dataset: {new_dataset}')
    breakpoint()