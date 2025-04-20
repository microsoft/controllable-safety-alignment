import argparse
from datasets import load_from_disk, DatasetDict, Dataset
from src.jack_utils import convert_list_of_dicts_to_dict_of_lists
from collections import defaultdict
import os

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('dataset', type=str)
    parser.add_argument('output', type=str)
    args = parser.parse_args()

    dataset = load_from_disk(args.dataset)
    ddict = defaultdict(list)
    for ex in dataset:
        split = ex['mode'] + '' + ex['spec_j']
        ddict[split].append(ex)
    converted_ddict = {k: Dataset.from_dict(convert_list_of_dicts_to_dict_of_lists(v)) for k, v in ddict.items()}
    dataset_dict = DatasetDict(converted_ddict)
    assert not os.path.exists(args.output), f'{args.output} already exists'
    
    # print(dataset_dict)
    dataset_dict.save_to_disk(args.output)
    # print info to dataset dir
    with open(os.path.join(args.output, 'info.txt'), 'w') as f:
        f.write(f'{dataset_dict}\n')

