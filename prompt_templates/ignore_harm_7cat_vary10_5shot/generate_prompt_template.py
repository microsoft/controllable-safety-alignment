from prompt_templates.ignore_harm_7cat_vary10.generate_prompt_template import get_messages as get_messages_base
from prompt_templates.ignore_harm_7cat_vary10.generate_prompt_template import default_dataset_categories
import pickle
from src.produce_metrics import cat_str_to_list
import random
SHOTS = 5
SHOTS_DATA_PATH = 'data/speci2pr/V5_train_7cat.pkl'

with open(SHOTS_DATA_PATH, 'rb') as f:
    speci2promptresponse = pickle.load(f)

def get_messages(raw_spec_str: str, mode='exact_match', dataset_categories=default_dataset_categories, return_actual_specs=False, shots=SHOTS):
    base_return = get_messages_base(raw_spec_str, mode=mode, dataset_categories=dataset_categories, return_actual_specs=return_actual_specs)
    if return_actual_specs:
        messages, actual_specs = base_return
    else:
        messages = base_return
    
    new_messages = [messages[0]]
    current_speci = tuple(sorted(cat_str_to_list(raw_spec_str)))
    # breakpoint()
    if current_speci in speci2promptresponse:
        prompt_responses = speci2promptresponse[current_speci]
        real_shots = min(shots, len(prompt_responses))
        sampled_prompt_responses = random.sample(prompt_responses, real_shots)
        for prompt_response in sampled_prompt_responses:
            prompt, response = prompt_response
            new_messages.append({'role': 'user', 'content': prompt})
            new_messages.append({'role': 'assistant', 'content': response})
    else:
        raise ValueError(f'No prompt responses found for speci {current_speci}')
    new_messages.append(messages[-1])
    if return_actual_specs:
        return new_messages, actual_specs
    else:
        return new_messages
    


if __name__ == '__main__':
    from pprint import pprint as pp
    print('EXACT MATCH MODE')
    for raw_spec_str in ['-Sexual Misconduct_Exploitation_and Infidelity-']: # ['--', '-Discrimination and Verbal Abuse-', '-Financial Crime and Theft-Privacy Violations-']:
        print('='*50)
        print(raw_spec_str)
        for i in range(5):
            print(f'Example {i+1}\n')
            messages = get_messages(raw_spec_str)
            pp(messages)
            # print(messages[0]['content'])
            print('-'*50)
        # print(get_messages(raw_spec_str))
    breakpoint()
