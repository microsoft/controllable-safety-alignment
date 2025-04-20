'''
Version 1:
Given a dataset of 
    (spec, prompt, safe_response, harmful_response) 
tuples, this script will generate a dataset of 
    (system_prompt, prompt, chosen_response, rejected_response, chosen_idx, spec_i, spec_j) 
tuples, where spec_i is the actual spec of the system prompt, and spec_j is the spec of the prompt. chosen_idx is 1 if the chosen_response is the harmful_response, and 0 otherwise. The script will also balance the number of in-domain and out-of-domain examples if the balance_domain flag is set.


assume both --safe_generation and --helpful_generation are in the format of:

- each is a path to DatasetDict
- each DatasetDict has keys as spec, and values as a dataset of examples, each containing 'prompt' and 'response' columns

Version 2:
Given a dataset of 
    (spec, prompt, prompt2response)
tuple, generate the same dataset above.

prompt2response is a dict of {prompt: response_dict}. response_dict is a dict of {category: [response1, response2, ...]}. category is a string that specifies the harm category.
'''
import sys
import os
import argparse
from datasets import load_from_disk, Dataset, DatasetDict, concatenate_datasets
from src.jack_utils import load_json, import_module_from_path, convert_list_of_dicts_to_dict_of_lists
import random
import json
from collections import Counter
from src.produce_metrics import cat_str_to_list

def obtain_get_messages_func(prompt_template_file):
    prompt_template = load_json(prompt_template_file)
    assert prompt_template.get('meta_path') is not None
    # meta template
    # meta_path contains path to a python file that contains a function def get_messages(dataset_name: str) which returns a list of messages given from the dataset name (i.e. the spec)
    get_messages = import_module_from_path(prompt_template['name']+'_meta_module', prompt_template['meta_path']).get_messages
    return get_messages

'''
def get_messages(raw_spec_str: str, mode='exact_match', return_actual_specs=False):
get_messages have 4 modes: exact_match, safe, superset, not_superset

4 modes:
- exact_match: identify function that return exact what the input categories are, but with shuffled order
- safe: identify function that return no harmful categories (thus safe)
- superset: return a list of categories that at least contain the input categories
- not_superset: return a list of categories that do not contain the input categories

exact_match and superset produce in-domain examples (where prompt should be answered)
safe and not_superset produce out-of-domain examples (where prompt should not be answered)
'''

# def get_error_score(
#         dataset_categories: list[str], spec_sys: list[str], spec_response: list[str],
#         alpha=1, beta=3
#     ):
#     '''
#     the error score measures how well the response categories adheres to the system categories

#     for each category:
#     - if the category is allowed or disallowed by both the system and the response, the score is 0
#     - if the category is allowed by the system but not by the response, add *alpha* to total score
#     - if the category is disallowed by the system but allowed by the response, add *beta* to total score

#     NOTE: only consider the categories that are in the dataset_categories
#     '''
#     total_score = 0
#     for cat in dataset_categories:
#         if (cat in spec_sys and cat in spec_response) or (cat not in spec_sys and cat not in spec_response):
#             continue
#         if cat in spec_sys and cat not in spec_response:
#             total_score += alpha
#         if cat not in spec_sys and cat in spec_response:
#             total_score += beta
#     return total_score

def get_error_score(
        dataset_categories: list[str], spec_sys: str, spec_response: str,
        alpha=0.1, beta=3
    ):
    '''
    the error score measures how well the response categories adheres to the system categories

    the response should output allowed harm AS NEEDED in order to be more helpful

    error score:
    - if the response does not address the question, +1
    - +alpha=0.1 for each allowed harm
    - +beta=3 for each disallowed harm

    spec_response is a string render of tuple (harms, is_addressed)
    
    NOTE: only consider the categories that are in the dataset_categories. This means that all categories not in the dataset_categories will be aggregated into the same 'Other Harms' category.
    '''
    def parse_spec_response(spec_response):
        assert spec_response[0] == '(' and spec_response[-1] == ')'
        # need to handle cases such as '(-Financial Crime and Theft-Weapons, Explosives, Arson, and Illegal Firearm Transactions-, 1)'
        processed_response = spec_response[1:-1].split(', ')
        harms = ', '.join(processed_response[0:-1])
        is_addressed = processed_response[-1]
        # if spec_response == '(-Financial Crime and Theft-Weapons, Explosives, Arson, and Illegal Firearm Transactions-, 1)':
        #     breakpoint()
        harms_list = cat_str_to_list(harms.strip())
        is_addressed_int = int(is_addressed.strip())
        return harms_list, is_addressed_int

    total_score = 0
    allowed_harms = set(cat_str_to_list(spec_sys))
    response_harms, is_addressed = parse_spec_response(spec_response)
    # response_harms = [h for h in response_harms if h in dataset_categories]
    response_harms = set([h if h in dataset_categories else 'Other Harms' for h in response_harms])
    total_score += abs(is_addressed - 1)
    for harm in response_harms:
        if harm in allowed_harms:
            total_score += alpha
        else:
            total_score += beta
    
    # if 'Other Harms' in response_harms and 'Other Harms' not in spec_response:
    #     breakpoint()
    return total_score


# def is_spec_a_subset_of_spec_b(spec_a: str, spec_b: str):
#     def str_spec_to_set(spec):
#         return set([s for s in spec.split('-') if len(s) > 0])
#     return str_spec_to_set(spec_a).issubset(str_spec_to_set(spec_b))

def is_spec_a_subset_of_spec_b(spec_a: list[str], spec_b: list[str]):
    a_set = set(spec_a)
    b_set = set(spec_b)
    return a_set.issubset(b_set)

# def spec_str_to_list(spec_str: str):
#     return [s for s in spec_str.split('-') if len(s) > 0]
def spec_list_to_str(spec_list: list[str]):
    return '-' + '-'.join(spec_list) + '-'

def combine_dataset_dicts(dataset_dicts):
    # Initialize an empty dictionary to hold the combined splits
    combined_splits = {}

    # Iterate over each DatasetDict in the list
    for dataset_dict in dataset_dicts:
        for split_name, dataset in dataset_dict.items():
            # If the split is already in the combined_splits, concatenate the datasets
            if split_name in combined_splits:
                combined_splits[split_name] = concatenate_datasets([combined_splits[split_name], dataset])
            else:
                # Otherwise, initialize the split with the current dataset
                combined_splits[split_name] = dataset

    # Create a new DatasetDict with the combined splits
    return DatasetDict(combined_splits)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prompt_template', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    parser.add_argument('--modes', type=str, nargs='+', choices=['easy', 'hard', 'mixed', 'exact_match', 'safe', 'superset', 'not_superset'], required=True, help='easy: in-domain examples use exact_match, out-of-domain examples use safe; hard: in-domain examples use superset, out-of-domain examples use not_superset; mixed: in-domain examples use exact_match and superset, out-of-domain examples use safe and not_superset')
    parser.add_argument('--train_categories', type=str, default=None)

    #### safe/helpful generation
    parser.add_argument('--safe_generation', type=str, default=None)
    parser.add_argument('--helpful_generation', type=str, default=None)
    ### OR ###
    ### prompt2response
    parser.add_argument('--prompt_dataset', type=str, default=None, nargs='*')
    parser.add_argument('--prompt2response', type=str, default=None)
    parser.add_argument('--alpha', type=float, default=0.1)
    parser.add_argument('--beta', type=float, default=3)
    ### END ###

    parser.add_argument('-s', '--spec_j_prompt_start_idx', type=int, default=0)
    parser.add_argument('-m', '--max_prompt_per_spec_j', type=int, default=sys.maxsize)
    parser.add_argument('--seed', type=int, default=0)
    
    args = parser.parse_args()
    random.seed(args.seed)
    print(f'args: {vars(args)}')
    assert not os.path.exists(args.output)
    
    if args.safe_generation is not None and args.helpful_generation is not None:
        data_mode = 'safe_helpful'
    elif args.prompt_dataset is not None and args.prompt2response is not None:
        data_mode = 'prompt2response'
    else:
        raise ValueError('Must provide either safe_generation and helpful_generation, or prompt2response')

    get_messages = obtain_get_messages_func(args.prompt_template)
    if data_mode == 'safe_helpful':
        response_datasets = [load_from_disk(path) for path in [args.safe_generation, args.helpful_generation]]
        specs = response_datasets[0].keys()
    elif data_mode == 'prompt2response':
        prompt_datasets = [load_from_disk(path) for path in args.prompt_dataset]
        prompt_dataset = combine_dataset_dicts(prompt_datasets)
        prompt2response = load_json(args.prompt2response)
        specs = prompt_dataset.keys()
    
    if args.train_categories is not None:
        dataset_categories = load_json(args.train_categories)
    else:
        dataset_categories = list(set([c for s in specs for c in cat_str_to_list(s)]))
    print('CATEGORIES TO CONSIDER FOR TRAINING:', dataset_categories)

    if args.modes == ['easy']:
        modes = ['exact_match', 'safe']
    elif args.modes == ['hard']:
        modes = ['superset', 'not_superset']
    elif args.modes == ['mixed']:
        modes = ['exact_match', 'superset', 'safe', 'not_superset']
    else:
        modes = args.modes

    processed_data = []
    for mode in modes:
        for spec_j in specs:
            spec_j_list = cat_str_to_list(spec_j)
            # if there exists a spec_j that is not in the dataset_categories, skip
            if any([c not in dataset_categories for c in spec_j_list]):
                # breakpoint()
                continue
            if data_mode == 'safe_helpful':
                safe_responses = response_datasets[0][spec_j]
                helpful_responses = response_datasets[1][spec_j]
                assert len(safe_responses) == len(helpful_responses)
                len_j = len(safe_responses)
            elif data_mode == 'prompt2response':
                prompts = prompt_dataset[spec_j]
                len_j = len(prompts)
            for k in range(args.spec_j_prompt_start_idx, min(len_j, args.spec_j_prompt_start_idx+args.max_prompt_per_spec_j)):
                messages, spec_i_list = get_messages(spec_j, mode=mode, dataset_categories=dataset_categories, return_actual_specs=True)
                spec_i = spec_list_to_str(spec_i_list)
                system_prompt = messages[0]['content']

                if data_mode == 'safe_helpful':
                    # this is heuristics-based
                    assert safe_responses[k]['prompt'] == helpful_responses[k]['prompt']
                    prompt = safe_responses[k]['prompt']
                    safe_response = safe_responses[k]['response']
                    helpful_response = helpful_responses[k]['response']

                    if is_spec_a_subset_of_spec_b(spec_j_list, spec_i_list):
                        # spec_j is a subset of spec_i, in-domain, aim for helpfulness (index 1)
                        chosen_response = helpful_response
                        chosen_idx = 1
                        rejected_response = safe_response
                    else:
                        chosen_response = safe_response
                        chosen_idx = 0
                        rejected_response = helpful_response

                    datapoint = {
                        'system_prompt': system_prompt,
                        'prompt': prompt,
                        'chosen_response': chosen_response,
                        'rejected_response': rejected_response,
                        'chosen_idx': chosen_idx,
                        'spec_i': spec_i,
                        'spec_j': spec_j,
                        'mode': mode
                    }
                    processed_data.append(datapoint)

                elif data_mode == 'prompt2response':
                    prompt = prompts[k]['prompt']
                    response_dict = prompt2response[prompt]
                    response_categories = list(c for c in response_dict.keys() if c != 'INVALID')
                    response_cat_error_score = [get_error_score(dataset_categories, spec_i, c, alpha=args.alpha, beta=args.beta) for c in response_categories]
                    for i in range(len(response_categories)):
                        for j in range(i+1, len(response_categories)):
                            ### choose the category with lower error score; if the error score is the same, skip
                            if response_cat_error_score[i] == response_cat_error_score[j]:
                                continue
                            if response_cat_error_score[i] < response_cat_error_score[j]:
                                chosen_cat = response_categories[i]
                                rejected_cat = response_categories[j]
                            else:
                                chosen_cat = response_categories[j]
                                rejected_cat = response_categories[i]
                            chosen_category_error_score = response_cat_error_score[i] if chosen_cat == response_categories[i] else response_cat_error_score[j]
                            rejected_category_error_score = response_cat_error_score[j] if chosen_cat == response_categories[i] else response_cat_error_score[i]
                            if chosen_category_error_score >= args.beta:
                                # this means we could choose response that violates the system spec as the chosen response, which is not good, skip!
                                continue
                            chosen_response = random.choice(response_dict[chosen_cat])
                            rejected_response = random.choice(response_dict[rejected_cat])
                            datapoint = {
                                'system_prompt': system_prompt,
                                'prompt': prompt,
                                'chosen_response': chosen_response,
                                'rejected_response': rejected_response,
                                'spec_i': spec_i,
                                'spec_j': spec_j,
                                'mode': mode,
                                'chosen_cat': chosen_cat,
                                'rejected_cat': rejected_cat,
                                'chosen_category_error_score': chosen_category_error_score,
                                'rejected_category_error_score': rejected_category_error_score
                            }
                            processed_data.append(datapoint)
                
    
    print('total number of examples:', len(processed_data))
    dataset = Dataset.from_dict(convert_list_of_dicts_to_dict_of_lists(processed_data))
    print(Counter(dataset['spec_j']))
    breakpoint()
    dataset.save_to_disk(args.output)
    with open(os.path.join(args.output, 'args.json'), 'w') as f:
        f.write(json.dumps(vars(args), indent=4))
    with open(os.path.join(args.output, 'info.txt'), 'w') as f:
        f.write(f'args: {vars(args)}\n')
        f.write(f'new_dataset: {dataset}')
        # spec_j
        f.write(f'Counter(dataset[\'spec_j\']): {Counter(dataset["spec_j"])}')
        # spec_i
        f.write(f'Counter(dataset[\'spec_i\']): {Counter(dataset["spec_i"])}')
    print(f'Saved to {args.output}')
