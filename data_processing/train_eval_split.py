'''
split a filtered dataset into train and eval sets

eval set will only have specs where total examples >= eval_size+min_train_size

those specs will be split into train and eval sets with eval_size examples in eval set

train set will have the rest of data for eval specs and all data for the remaining specs

python data_processing/train_eval_split.py /scratch/jzhan237/repos/safety-control/data/by_spec/BeaverTails-330k_train-1000-dedupprompt --eval_size 500 --min_train_size 500 --seed 0
'''

import argparse
from datasets import load_dataset, Dataset, DatasetDict
from collections import Counter, defaultdict
import os

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('filtered_dataset', type=str) # PKU-Alignment/BeaverTails
    # parser.add_argument('--output_dir', type=str, default='data/by_spec')
    parser.add_argument('--eval_size', type=int, default=100, help='number of examples in eval set')
    parser.add_argument('--min_train_size', type=int, default=1000, help='minimum number of examples in train set')
    parser.add_argument('--max_train_size', type=int, default=2000, help='maximum number of examples in train set')
    parser.add_argument('--no_safe', action='store_true', help='do not include safe examples in train/eval set')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--force', action='store_true', help='overwrite output')

    args = parser.parse_args()
    filtered_dataset = DatasetDict.load_from_disk(args.filtered_dataset)
    output_path = args.filtered_dataset + f'-split-eval{args.eval_size}-train{args.min_train_size}to{args.max_train_size}'
    if args.no_safe:
        output_path += '-no_safe'
    if args.seed != 0:
        output_path += f'-seed{args.seed}'
    if not args.force:
        assert not os.path.exists(output_path), f'{output_path} already exists'
    os.makedirs(output_path, exist_ok=True)
    
    train_dict = {}
    eval_dict = {}
    for spec, ds in filtered_dataset.items():
        ds = ds.shuffle(seed=args.seed)
        if args.no_safe and spec == '--':
            continue
        if len(ds) >= args.eval_size + args.min_train_size:
            train_eval_split = ds.train_test_split(test_size=args.eval_size, shuffle=False) # already shuffled before
            train_dict[spec] = train_eval_split['train'].select(range(min(args.max_train_size, len(train_eval_split['train']))))
            eval_dict[spec] = train_eval_split['test']
        # else:
        #     train_dict[spec] = ds
        # if there are not enough examples for eval, just throw out the spec

    train_dict = DatasetDict(train_dict)
    eval_dict = DatasetDict(eval_dict)
    train_dict.save_to_disk(os.path.join(output_path, 'train'))
    eval_dict.save_to_disk(os.path.join(output_path, 'eval'))
    print('train:')
    print(train_dict)
    with open(os.path.join(output_path, 'train', 'info.txt'), 'w') as f:
        f.write(str(train_dict))
    print('eval:')
    print(eval_dict)
    with open(os.path.join(output_path, 'eval', 'info.txt'), 'w') as f:
        f.write(str(eval_dict))
    print(f'number of specs in train: {len(train_dict)}, number of specs in eval: {len(eval_dict)}')
    print('saved to ', output_path)