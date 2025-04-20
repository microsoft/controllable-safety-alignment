from src.jack_utils import load_state_dict, path_no_ext
import argparse
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('model_name', type=str)
    parser.add_argument('checkpoint_path', type=str)
    parser.add_argument('--not_load_in_bf16', action='store_true')
    args = parser.parse_args()

    kwargs = {}
    if not args.not_load_in_bf16:
        # dtype = torch.bfloat16
        print('Loading in bfloat16')
        kwargs['torch_dtype'] = torch.bfloat16

    model = AutoModelForCausalLM.from_pretrained(args.model_name, trust_remote_code=True, **kwargs) # , device_map="auto"
    model = load_state_dict(model, args.checkpoint_path)
    model.save_pretrained(path_no_ext(args.checkpoint_path))
    tokenizer = AutoTokenizer.from_pretrained(args.model_name, trust_remote_code=True)
    tokenizer.save_pretrained(path_no_ext(args.checkpoint_path))
