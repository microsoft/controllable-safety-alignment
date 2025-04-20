from openai import AzureOpenAI
from src.async_oai_wrapper import AZURE_OPENAI_ENDPOINT, TOKEN_PROVIDER
from typing import List
import numpy as np
from tqdm import tqdm
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
import openai

client = AzureOpenAI(
    azure_endpoint = AZURE_OPENAI_ENDPOINT,
    azure_ad_token_provider=TOKEN_PROVIDER,
    api_version = "2024-02-01",
)

# retry if openai.RateLimitError or openai.APIConnectionError
# exponetial backoff with jitter
# max 5 retries
@retry(stop=stop_after_attempt(5), wait=wait_random_exponential(multiplier=1, max=60), retry=retry_if_exception_type(openai.RateLimitError) | retry_if_exception_type(openai.APIConnectionError))
def generate_embeddings(texts: List[str], model="text-embedding-ada-002"): # model = "deployment_name"
    result = client.embeddings.create(input = texts, model=model)
    # breakpoint()
    return [emb.embedding for emb in result.data]

def batch_generate_embeddings(texts: List[str], model="text-embedding-ada-002", batch_size=1024):
    embeddings = []
    for i in tqdm(range(0, len(texts), batch_size), desc="batches"):
        embeddings.extend(generate_embeddings(texts[i:i+batch_size], model))
    return embeddings

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

if __name__ == "__main__":
    texts = ["Once upon a time...", "How are you doing today?", "How are you doing now?", "你好吗？", "wtf", "dog"]
    embedding = generate_embeddings(texts)
    print(embedding)

    print('a\\b,' + ','.join(texts))
    for emb_a, text_a in zip(embedding, texts):
        print(f"{text_a},", end="")
        for emb_b, text_b in zip(embedding, texts):
            print(f"{cosine_similarity(emb_a, emb_b):.2f},", end="")
        print()