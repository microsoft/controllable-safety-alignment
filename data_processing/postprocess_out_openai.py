'''
replace all "As an AI developed by OpenAI" by "As an AI" in the response field
'''
import argparse
from datasets import load_from_disk

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=str)
    parser.add_argument('output', type=str)
    args = parser.parse_args()

    dataset = load_from_disk(args.input)
    dataset = dataset.map(lambda ex: {'response': ex['response'].replace('As an AI developed by OpenAI', 'As an AI')})
    dataset.save_to_disk(args.output)