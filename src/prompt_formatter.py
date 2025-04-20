from jack_utils import load_json, import_module_from_path

class PromptFormatter:
    def __init__(
            self, 
            prompt_template_file: str, 
            dataset_template_mapping: dict = None
        ):
        self.prompt_template = load_json(prompt_template_file)
        self.dataset_template_mapping = { 'prompt': 'question', 'response': 'response' } # default
        if 'dataset_template_mapping' in self.prompt_template:
            self.dataset_template_mapping = self.prompt_template['dataset_template_mapping']
            if dataset_template_mapping is not None:
                print('Warning: dataset_template_mapping is provided in both prompt_template and PromptFormatter constructor. The one in the constructor will be used.')
        if dataset_template_mapping is not None:        
            self.dataset_template_mapping = dataset_template_mapping

        self.is_meta = False
        self.get_messages = None
        if self.prompt_template.get('meta_path') is not None:
            # meta template
            # meta_path contains path to a python file that contains a function def get_messages(dataset_name: str) which returns a list of messages given from the dataset name
            self.is_meta = True
            self.get_messages = import_module_from_path(self.prompt_template['name']+'_meta_module', self.prompt_template['meta_path']).get_messages

    def get_template(self, dataset_name, example):
        '''return a list of messages'''
        if self.is_meta:
            requires_example = self.prompt_template.get('requires_example')
            if requires_example:
                return self.get_messages(dataset_name, example=example)
            else:
                return self.get_messages(dataset_name)
        else:
            # regular template
            return self.prompt_template['messages']

    def str_format_strict(self, s: str, **kwargs) -> str:
        for k, v in kwargs.items():
            s = s.replace('{' + k + '}', v)
        return s

    def format(self, dataset_name, example, **kwargs):
        formatted_messages = []
        for message in self.get_template(dataset_name, example):
            # message['content'] = message['content'].format(**kwargs)
            new_message = {k: self.str_format_strict(v, **kwargs) if k=='content' else v for k, v in message.items()}
            formatted_messages.append(new_message)
        return formatted_messages
    
    def format_from_dataset_example(self, example, dataset_name):
        # e.g. a dataset example is {'prompt': 'how are you?', 'response': 'I am fine.'}
        # and the mapping is {'prompt': 'question', 'response': 'response'}
        # then kwargs = {'question': 'how are you?', 'response': 'I am fine.'}
        kwargs = {v: example[k] for k, v in self.dataset_template_mapping.items() if k in example}
        return self.format(dataset_name, example, **kwargs)

