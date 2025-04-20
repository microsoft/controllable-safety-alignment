import argparse
from datasets import load_from_disk, DatasetDict
from collections import defaultdict
from src.jack_utils import save_json

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Summarize the data')
    parser.add_argument('input', type=str, help='Path to the input data')
    parser.add_argument('-o', '--output_examples_path', type=str, default=None, help='Path to the output examples file')
    parser.add_argument('--lim', type=int, default=100, help='Limit the number of examples to print')
    args = parser.parse_args()

    ds_dict = load_from_disk(args.input)
    assert isinstance(ds_dict, DatasetDict), 'Expected a DatasetDict'

    examples_d = defaultdict(list)
    print('name;num_examples')
    for k, ds in ds_dict.items():
        print(f'{k};{len(ds)}')
        for i, ex in enumerate(ds):
            if args.lim is not None and i >= args.lim:
                break
            examples_d[k].append(ex)
    
    if args.output_examples_path is not None:
        save_json(examples_d, args.output_examples_path)
        print(f'Saved examples to {args.output_examples_path}')