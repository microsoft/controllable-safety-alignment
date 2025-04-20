'''
written by chatgpt
'''
import json
import argparse
from datasets import Dataset
import os

def jsonl_to_dataset(jsonl_file):
    # Read the jsonl file and collect prompts
    prompts = []
    with open(jsonl_file, 'r') as f:
        for line in f:
            data = json.loads(line.strip())
            if 'prompt' in data:
                prompts.append({'prompt': data['prompt']})
    
    # Create a Hugging Face Dataset from the prompts list
    dataset = Dataset.from_list(prompts)
    return dataset

def save_dataset(dataset, save_path):
    # Save the dataset to disk
    dataset.save_to_disk(save_path)

def save_args_to_json(args, save_path):
    # Save the command-line arguments to an "args.json" file
    args_dict = vars(args)
    with open(os.path.join(save_path, 'args.json'), 'w') as f:
        json.dump(args_dict, f, indent=4)

def save_dataset_info(dataset, save_path):
    # Save the dataset information to an "info.txt" file
    with open(os.path.join(save_path, 'info.txt'), 'w') as f:
        f.write(str(dataset))

def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Convert a JSONL file to a Hugging Face Dataset.")
    parser.add_argument('input_jsonl', type=str, help="Path to the input JSONL file")
    parser.add_argument('output_path', type=str, help="Directory where the Hugging Face dataset will be saved")
    
    args = parser.parse_args()

    # Convert the JSONL file to a Hugging Face Dataset
    dataset = jsonl_to_dataset(args.input_jsonl)

    # Save the dataset
    save_dataset(dataset, args.output_path)

    # Save the command-line arguments to a JSON file
    save_args_to_json(args, args.output_path)

    # Save the dataset information to a text file
    save_dataset_info(dataset, args.output_path)

    print(f"Dataset saved to {args.output_path}")
    print(f"Arguments saved to {os.path.join(args.output_path, 'args.json')}")
    print(f"Dataset information saved to {os.path.join(args.output_path, 'info.txt')}")

if __name__ == "__main__":
    main()
