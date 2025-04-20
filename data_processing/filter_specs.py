'''
filter a datasets to only consider the top specs. Also, group the data by specs

produce a ''filtered dataset'' i.e. a dataset dict where each key is a spec and the value is a dataset of examples with that spec
each dataset will have columns 'prompt' and 'response'
- the response is original response labeled as the corresponding harm category in beavertails

python data_processing/filter_specs.py PKU-Alignment/BeaverTails --output_dir data/by_spec --split 330k_train --lower_bound 1000 --dedup_prompt
'''

import argparse
from datasets import load_dataset, load_from_disk, Dataset, DatasetDict
from collections import Counter, defaultdict
import os
import json

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input_dataset', type=str) # PKU-Alignment/BeaverTails
    parser.add_argument('--output_dir', type=str, default='data/by_spec')
    parser.add_argument('--split', type=str, default='330k_train')
    parser.add_argument('--lower_bound', type=int, default=10, help='minimum number of examples for a spec to be considered')
    parser.add_argument('--dedup_prompt', action='store_true', help='deduplicate prompts')
    parser.add_argument('--force', action='store_true', help='overwrite output dir')
    parser.add_argument('--prompt_only', action='store_true', help='in this mode, only the prompt is saved, and category key is "response"')

    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    output_name = f'{args.input_dataset.split("/")[-1]}-{args.split}-{args.lower_bound}'
    if args.dedup_prompt:
        output_name += '-dedupprompt'
    output_path = os.path.join(args.output_dir, output_name)
    if not args.force:
        assert not os.path.exists(output_path), f'{output_path} already exists'

    if os.path.exists(args.input_dataset):
        # input_dataset is a path
        dataset = load_from_disk(args.input_dataset)
    else:
        dataset = load_dataset(args.input_dataset)
    datasplit = dataset[args.split]
    # assume data split is in beavertails format: columns used are 'prompt', 'response', 'category', where 'category' is a dict[str, bool] of safety category names and binary values
    # in prompt_only model, 'response' is category and 'prompt' is the prompt
    category_key = 'response' if args.prompt_only else 'category'

    def str_to_json(s):
        return json.loads(s.replace("'", '"'))
    harm_cat = list(str_to_json(datasplit[0][category_key]).keys())
    def dict_to_spec(harm_dict):
        # convert beavertails dictionary to tuple i.e. binary specs
        return tuple([harm_dict[k] for k in harm_cat])
    def spec_to_text(tup):
        # convert binary specs to text (only do so for the 1s)
        return '-'+'-'.join([harm_cat[i] for i in range(len(tup)) if tup[i] == 1])+'-'
    
    spec_counts = Counter()
    grouped_examples = defaultdict(list)
    included_prompts = defaultdict(set) # if there are two QA pairs with the same prompt but labeled different specs, can keep both of them
    for elt in datasplit:
        spec = dict_to_spec(str_to_json(elt[category_key]))
        if args.dedup_prompt and elt['prompt'] in included_prompts[spec]:
            continue
        included_prompts[spec].add(elt['prompt'])
        spec_counts[spec] += 1
        grouped_examples[spec].append({'prompt': elt['prompt'], 'response': elt['response']})
    def convert_to_ds(examples):
        if args.prompt_only:
            return Dataset.from_dict({'prompt': [ex['prompt'] for ex in examples]})
        else:
            return Dataset.from_dict({'prompt': [ex['prompt'] for ex in examples], 'response': [ex['response'] for ex in examples]})

    # filter out specs with less than lower_bound examples
    filtered_specs = [spec for spec, _ in spec_counts.most_common() if spec_counts[spec] >= args.lower_bound]
    ddict = DatasetDict({
        spec_to_text(spec): convert_to_ds(grouped_examples[spec])
        for spec in filtered_specs})
    
    breakpoint()
    ddict.save_to_disk(output_path)
    print(ddict)
    print(f'saved to {output_path}')