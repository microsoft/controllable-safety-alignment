import sklearn.cluster
import umap # pip install umap umap-learn
import numpy as np
import pandas as pd
import hdbscan
import time
import sklearn

def umap_embeddings(embeddings, **kwargs):
    # first, perform dimensionality reduction from 768 to 15
    n_components = kwargs.get('n_components', 15)
    if n_components == 0:
        print("Skipping UMAP dimensionality reduction.")
        return embeddings
    reducer_15 = umap.UMAP(n_components=n_components)
    print(f"Fitting UMAP with {n_components} dimensions...")
    time1 = time.time()
    reducer_15.fit(embeddings)
    time2 = time.time()
    print("Done with UMAP fitting.")
    print("Time taken for UMAP fitting:", time2 - time1, "seconds")

    print(f"Transforming embeddings to {n_components} dimensions...")
    time1 = time.time()
    embeddings_umap = reducer_15.transform(embeddings)
    time2 = time.time()
    assert np.all(embeddings_umap == reducer_15.embedding_)
    print("Time taken for UMAP transformation:", time2 - time1, "seconds")
    print("Done with UMAP fitting and transformation.\n")
    return embeddings_umap

def cluster_umap_hdbscan(embeddings_umap, **kwargs):
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=kwargs.get('min_cluster_size', 5), 
        cluster_selection_epsilon=kwargs.get('cluster_selection_epsilon', 0.0),
        gen_min_span_tree=True)
    clusterer.fit(embeddings_umap)

    return clusterer

def cluster_umap_kmeans(embeddings_umap, **kwargs):
    clusterer = sklearn.cluster.KMeans(n_clusters=kwargs.get('n_clusters', 8), random_state=0)
    clusterer.fit(embeddings_umap)

    return clusterer

def cluster_umap(embeddings, **kwargs):
    embeddings_umap = umap_embeddings(embeddings, **kwargs)

    algorithm = kwargs.get('algorithm', 'hdbscan')
    if algorithm == 'hdbscan':
        func = cluster_umap_hdbscan
        name = 'HDBSCAN'
    elif algorithm == 'kmeans':
        func = cluster_umap_kmeans
        name = 'KMeans'
    else:
        raise ValueError(f"Invalid algorithm: {algorithm}")

    # second, perform clustering
    print(f"Fitting {name}...")
    time1 = time.time()
    clusterer = func(embeddings_umap, **kwargs)
    time2 = time.time()
    print(f"Done with {name} fitting.")
    print("Number of examples:", len(embeddings))
    print(f"Time taken for {name} fitting:", time2 - time1, "seconds\n")

    print("\nCluster value counts:\n")
    pd.Series(clusterer.labels_).value_counts()
    print("Number of clusters:", len(set(clusterer.labels_)))

    probs = clusterer.probabilities_ if hasattr(clusterer, 'probabilities_') else np.zeros(len(embeddings))

    return clusterer.labels_, probs