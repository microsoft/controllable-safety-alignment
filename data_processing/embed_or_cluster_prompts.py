import argparse
from src.oai_embed import batch_generate_embeddings
from src.clustering import cluster_umap
from datasets import Dataset, DatasetDict, load_dataset, load_from_disk
import os
import numpy as np

CLUSTERING_KWARGS = {
    'n_components': 512,
    'min_cluster_size': 5,
    'cluster_selection_epsilon': 0.25,
    'cluster_selection_method': 'leaf',
    # 'algorithm': 'kmeans',
    # 'n_clusters': 20
}

def embed_single_split(split):
    embd = batch_generate_embeddings(split['prompt'])
    split_emb = split.add_column('prompt_embedding', embd)
    return split_emb

def cluster_single_split(split):
    embd = np.array(split['prompt_embedding'])
    cluster, prob = cluster_umap(embd, **CLUSTERING_KWARGS)
    new_split = split.add_column('cluster', cluster).add_column('cluster_prob', prob)
    return new_split

def deduplicate_single_split(split):
    df = split.to_pandas()
    df = df.drop_duplicates(subset='prompt')
    new_split = Dataset.from_pandas(df).remove_columns(["__index_level_0__"])
    return new_split

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Embed or cluster prompts using OpenAI API')
    parser.add_argument('dataset_name', type=str)
    # parser.add_argument('--cluster', action='store_true', help='Cluster the prompts')
    parser.add_argument('--task', choices=['embed', 'cluster', 'dedup'], default='embed')
    parser.add_argument('--from_disk', action='store_true')
    args = parser.parse_args()

    output_dir = os.path.join(os.environ.get('DATA_DIR', 'data'), f'prompt{args.task}')
    output_ds_dir = os.path.join(output_dir, os.path.basename(args.dataset_name))
    if args.task == 'cluster':
        hyparams_str = '-'.join(f'{k}={v}' for k, v in CLUSTERING_KWARGS.items())
        output_ds_dir += f'-{hyparams_str}'
    print(f'Output directory: {output_ds_dir}')
    assert not os.path.exists(output_ds_dir), f"Output directory {output_ds_dir} already exists"

    dataset = load_from_disk(args.dataset_name) if args.from_disk else load_dataset(args.dataset_name)
    # if not isinstance(dataset, DatasetDict):
    #     dataset = DatasetDict({'default': dataset})

    if args.task == 'dedup':
        func = deduplicate_single_split
        name = 'Deduplicate'
    elif args.task == 'cluster':
        func = cluster_single_split
        name = 'Cluster'
    else:
        func = embed_single_split
        name = 'Embed'
    
    if isinstance(dataset, DatasetDict):
        new_dataset = {}
        for split_name, split in dataset.items():
            print(f'{name} {args.dataset_name}/{split_name}...')
            new_dataset[split_name] = func(split)
        new_dataset = DatasetDict(new_dataset)
    else:
        new_dataset = func(dataset)
    
    
    new_dataset.save_to_disk(output_ds_dir)