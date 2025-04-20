'''

Assume we already have a dataset of prompts with labels (see compare_gpt_label_with_cluster.ipynb)

We (1) parse raw categorical labeling response (2) select desired labels to consider for train/eval (3) format each split into a DatasetDict where each split is a spec, with column 'prompt' containing prompts of that spec

'''
import argparse
from src.jack_utils import load_json
from datasets import load_from_disk, DatasetDict, Dataset
import os
import json

def str_to_json(s, single_line=True):
    '''
    parse gpt response to json
    '''
    s = s.strip()
    json_portion = s.split('\n')[-1] if single_line else s
    if not s.startswith('{'):
        json_start = s.find('{')
        json_portion = s[json_start:]
        json_portion.replace('```', '')
    return json.loads(json_portion.replace('Final Answer: ', '').replace("'", '"'))

def json_to_categories_str(j):
    return '-' + '-'.join([k for k in j.keys() if j[k]]) + '-'

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('labeled_prompts', type=str, help='Path to labeled prompts')
    parser.add_argument('--split_mapping', type=str, default='data_processing/split_mapping/beavertails.json')
    parser.add_argument('--spec_set', type=str, default=None, help='Path to spec set json')
    parser.add_argument('--min_count_to_include_spec', type=int, default=10, help='Minimum count of spec to include in the output')
    parser.add_argument('--output_dir', type=str, required=True, help='Path to output directory, should contain information about labeled prompts and spec_set')
    
    parser.add_argument('--max_test_size_per_spec', type=int, default=0)
    parser.add_argument('-seed', type=int, default=0)

    args = parser.parse_args()
    labeled_prompts = load_from_disk(args.labeled_prompts)
    split_mapping = load_json(args.split_mapping)
    spec_set = load_json(args.spec_set) if args.spec_set is not None else None
    assert not os.path.exists(args.output_dir), f'{args.output_dir} already exists'
    os.makedirs(args.output_dir)
    with open(os.path.join(args.output_dir, 'args.info'), 'w') as f:
        print(vars(args), file=f)
    
    for new_set_name, old_set_name in split_mapping.items():
        num_failed = 0
        split = labeled_prompts[old_set_name]
        collected_data = {}
        for ex in split:
            raw_gpt_response = ex['prompt_harm_categorization_response']
            try:
                response_json = str_to_json(raw_gpt_response)
            except:
                print(f'Failed to parse {raw_gpt_response}')
                num_failed += 1
                continue
            categories_str = json_to_categories_str(response_json)
            if spec_set is None or categories_str in spec_set['categories']:
                if categories_str not in collected_data:
                    collected_data[categories_str] = {'prompt': []}
                collected_data[categories_str]['prompt'].append(ex['prompt'])
        
        ddict = DatasetDict({k: Dataset.from_dict(v) for k, v in collected_data.items()})
        ddict = ddict.shuffle(seed=args.seed)
        if new_set_name == 'test' and args.max_test_size_per_spec > 0:
            ddict = DatasetDict({k: v.select(range(min(args.max_test_size_per_spec, len(v)))) for k, v in ddict.items()})

        # remove specs with small count
        ddict = DatasetDict({k: v for k, v in ddict.items() if len(v) >= args.min_count_to_include_spec})

        ddict.save_to_disk(os.path.join(args.output_dir, new_set_name))
        print('Total data:', len(split))
        print('Total selected:', sum([len(v) for v in ddict.values()]))
        print('Failed to parse:', num_failed)
        print(ddict)
        with open(os.path.join(args.output_dir, new_set_name + '.info'), 'w') as f:
            print(ddict, file=f)
        print('Saved to:', os.path.join(args.output_dir, new_set_name))