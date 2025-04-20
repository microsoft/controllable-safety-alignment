from prompt_templates.ignore_harm_7cat_vary10_5shot.generate_prompt_template import get_messages as get_messages_base, default_dataset_categories

def get_messages(raw_spec_str: str, mode='exact_match', dataset_categories=default_dataset_categories, return_actual_specs=False):
    return get_messages_base(raw_spec_str, mode=mode, dataset_categories=dataset_categories, return_actual_specs=return_actual_specs, shots=15)
    

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
