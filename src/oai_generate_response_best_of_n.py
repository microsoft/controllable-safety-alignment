'''
this is a specialized version of oai_inference that can handle labeling best of n responses
'''

import argparse
from src.oai_inference import model_name_to_endpoints, get_final_response_list
from async_oai_wrapper import AsyncOAIWrapper
from prompt_formatter import PromptFormatter
from datasets import Dataset, DatasetDict, load_from_disk
from datasets.features import Value, Sequence
from src.jack_utils import load_json
import os

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bon_dataset', type=str, required=True, help='path to dataset from bon generation; must contain prompt and response, where response is a list of items')
    parser.add_argument('--prompt_template', type=str, required=True, help='path to prompt template file')
    parser.add_argument('--model', type=str, required=True, help='model name')
    parser.add_argument('--kwargs', type=str, default=None, help='json file that loads as a dict that contains kwargs for the model')
    
    # oai call setup
    parser.add_argument('-r', '--rate_limit_multiplier', type=float, default=1, help='rate limit multiplier for async calls (<1 for slower than default to avoid over limit)')
    # SPECIAL
    parser.add_argument('--fake_response', type=str, default=None, help='if not none, use the same fake response for all examples. helpful to skip the addressed labeling of unsafe model')
    parser.add_argument('--rule_based_sorry_detect', action='store_true', help='if true, use rule based sorry detection')
    
    args = parser.parse_args()
    dataset = load_from_disk(args.bon_dataset)
    assert isinstance(dataset, DatasetDict)

    prompt_formatter = PromptFormatter(args.prompt_template)
    outpath = args.bon_dataset + f'_model-{args.model}_{prompt_formatter.prompt_template["name"]}'
    if args.fake_response is not None:
        outpath += f'_fake-response{args.fake_response}'
    if args.rule_based_sorry_detect:
        outpath += '_rulebasedsorry'
    assert not os.path.exists(outpath), f'{outpath} already exists'

    endpoints = model_name_to_endpoints(args.model, args.rate_limit_multiplier)
    
    # kwargs = {
    # 'temperature': 0,
    #     'max_tokens': 1024,
    #     'top_p': 1,
    #     'frequency_penalty': 0,
    #     'presence_penalty': 0
    # } if args.kwargs is None else load_json(args.kwargs)
    if args.kwargs is not None:
        kwargs = load_json(args.kwargs)
    elif 'kwargs' in prompt_formatter.prompt_template:
        kwargs = prompt_formatter.prompt_template['kwargs']
    else:
        kwargs = {
            'temperature': 0,
            'max_tokens': 1024,
            'top_p': 1,
            'frequency_penalty': 0,
            'presence_penalty': 0
        }
    print(f'kwargs: {kwargs}')

    
    async_caller = AsyncOAIWrapper(endpoints, **kwargs)

    new_ddict = {}
    for split_name, split in dataset.items():
        assert isinstance(split.features['prompt'], Value) and isinstance(split.features['response'], Sequence)
        messages_list = []
        messages_lengths = []
        for ex in split:
            messages_example = []
            for response in ex['response']:
                # create a fake example with a single response
                messages = prompt_formatter.format_from_dataset_example({'prompt': ex['prompt'], 'response': response}, split_name)
                messages_example.append(messages)
            messages_list.extend(messages_example)
            messages_lengths.append(len(messages_example))
        
        if args.fake_response is not None:
            final_response_list = [args.fake_response] * len(messages_list)
        elif args.rule_based_sorry_detect:
            final_response_list = []
            for messages in messages_list:
                response_to_judge = messages[-1]['content']
                if 'sorry' in response_to_judge.lower():
                    final_response_list.append('[[NO]]')
                else:
                    final_response_list.append('[[YES]]')

        else:
            raw_final_response_list = async_caller.run(messages_list)
            final_response_list = get_final_response_list(raw_final_response_list)
        assert len(final_response_list) == len(messages_list)
        final_response_by_example = []
        i = 0
        for length in messages_lengths:
            final_response_by_example.append(final_response_list[i:i+length])
            i += length
        assert len(final_response_by_example) == len(split)
        if 'response_key' in prompt_formatter.prompt_template:
            response_key = prompt_formatter.prompt_template['response_key']
        else:
            response_key = 'response_best_of_n' #f'response_{args.model}'
        new_split = split.add_column(response_key, final_response_by_example)
        new_ddict[split_name] = new_split
    new_ddict = DatasetDict(new_ddict)
    new_ddict.save_to_disk(outpath)
    print('Example:')
    print(new_split[0])
    print(f'saved to {outpath}')
    