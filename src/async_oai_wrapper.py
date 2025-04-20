'''
This is a wrapper for OpenAI API that allows for async calls to the API.

Support leaky bucket rate limiting and multiple endpoints.

Author: Jack Zhang, June 2024
Some code are adapted from https://github.com/JHU-CLSP/Cost-Effective-Experiment
'''
import openai
import httpx
from tqdm import tqdm
import asyncio
import sys
import random
from aiolimiter import AsyncLimiter
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
import re 
# from cachier import cachier

# can try adding this if weird async error occurs
# import nest_asyncio
# nest_asyncio.apply()

from openai import AsyncAzureOpenAI, AsyncOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
AZURE_OPENAI_ENDPOINT = 'https://example.openai.azure.com/' # TODO: swap this with your endpoint
TOKEN_PROVIDER = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")

# Those model cost numbers are current as of 2024-02-20
MODEL_COSTS = {
    "gpt-3.5-turbo": {"context": 0.0015, "generated": 0.002},
    "gpt-3.5-turbo-0301": {"context": 0.0015, "generated": 0.002},
    "gpt-3.5-turbo-0613": {"context": 0.0015, "generated": 0.002},
    "gpt-3.5-turbo-16k": {"context": 0.003, "generated": 0.004},
    "gpt-3.5-turbo-16k-0613": {"context": 0.003, "generated": 0.004},
    "gpt-4": {"context": 0.03, "generated": 0.06},
    "gpt-4-32k": {"context": 0.06, "generated": 0.12},
    "gpt-4-0314": {"context": 0.03, "generated": 0.06},
    "gpt-4-0613": {"context": 0.03, "generated": 0.06},
    "gpt-4-32k": {"context": 0.06, "generated": 0.12},
    "gpt-4-32k-0314": {"context": 0.06, "generated": 0.12},
    "gpt-4-32k-0613": {"context": 0.06, "generated": 0.12},
    "gpt-4-0125-preview": {"context": 0.01, "generated": 0.03},
    "gpt-4-1106-preview": {"context": 0.01, "generated": 0.03},
    "gpt-4-1106-vision-preview": {"context": 0.01, "generated": 0.03},
    "text-embedding-ada-002-v2": {"context": 0.0001, "generated": 0},
    "text-davinci:003": {"context": 0.03, "generated": 0.12},
    "whisper-1": {"context": 0.006 / 60, "generated": 0},
    "gpt-3.5-turbo-0125": {"context": 0.0005, "generated": 0.0015},
    "gpt-3.5-turbo-instruct": {"context": 0.0015, "generated": 0.002},
    "gpt-4-turbo": {"context": 0.01, "generated": 0.03},
    "gpt-4-turbo-2024-04-09": {"context": 0.01, "generated": 0.03},
}

@dataclass
class Endpoint:
    model: str = 'gpt-4-turbo'
    endpoint: str = AZURE_OPENAI_ENDPOINT # Azure endpoint or vLLM port
    rpm: int = 800 # REQUESTS (not tokens) per minute
    is_vllm: bool = False
    api_key: str = None # this is optional if using token provider

DEFAULT_ENDPOINTS = [
    Endpoint('gpt-4-turbo', AZURE_OPENAI_ENDPOINT, 800)
]

class AsyncOAIWrapper:
    def __init__(
        self,
        endpoints: List[Endpoint] = DEFAULT_ENDPOINTS,
        token_provider = TOKEN_PROVIDER,
        model_costs: dict = MODEL_COSTS,
        max_retries: int = 10, # Maximum number of retries
        retry_delay: float = 1.0, # Initial delay in seconds
        retry_delay_from_message: bool = False, # If True, use the delay by parsing the error message
        # rpm: int = 800, # request per minute
        batch_size: int = 500, # Number of requests to send in parallel

        # model and decoding
        # model: str = "gpt-4-turbo",
        **kwargs # decoding kwargs, see openai API doc
    ) -> None:
        self.clients = [
            (
                AsyncAzureOpenAI(
                    azure_endpoint=endpoint.endpoint,
                    api_key=endpoint.api_key,
                    azure_ad_token_provider=token_provider if endpoint.api_key is None else None, # only use token provider if api_key is not provided
                    api_version="2024-02-01",
                    http_client=httpx.AsyncClient(
                        timeout=httpx.Timeout(None), # TODO: no time out for now, decide what's the best timeout later
                        limits=httpx.Limits(
                            max_connections=10000,
                            max_keepalive_connections=3000
                        )
                    )
                ) if not endpoint.is_vllm else 
                    AsyncOpenAI(
                        base_url=f"http://localhost:{endpoint.endpoint}/v1",
                        api_key="token-abc123"
                    ), 
                endpoint.model) for endpoint in endpoints
        ]
        total_rpm = np.sum([endpoint.rpm for endpoint in endpoints])
        self.endpoint_probs = np.array([endpoint.rpm for endpoint in endpoints]) / total_rpm

        self.model_costs = model_costs
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_delay_from_message = retry_delay_from_message
        self.rate_limit = AsyncLimiter(total_rpm, 60) # default is 800+480 requests per minute
        self.batch_size = batch_size

        self.pbar = None
        self.pbar_cmp = None
        
        self.kwargs = kwargs

        self._printed_warning = False


    def get_price(self, model, response):
        # special case for fine-tuned model, assuming the base model is gpt-3.5-turbo 
        if model.startswith("ft"):
            model = "gpt-3.5-turbo"
        elif not (model in self.model_costs):
            if not self._printed_warning:
                self._printed_warning = True
                print(f"Model {model} not found in model_costs, assume it's gpt-4-turbo", file=sys.stderr)
            model = "gpt-4-turbo"
        price = response.usage.prompt_tokens / 1000 * self.model_costs[model]["context"] + response.usage.completion_tokens / 1000 * self.model_costs[model]["generated"]
        return price


    def get_client(self) -> Tuple[AsyncAzureOpenAI, str]:
        '''get a random client based on relative rate limit; also returns the model name'''
        return self.clients[np.random.choice(len(self.clients), p=self.endpoint_probs)]

    # @cachier()
    async def cached_api_call(self, client, model, messages, **kwargs):
        '''
        IMPORTANT: this function does not utilize self, a requirement of the cachier library!
        '''
        response = await client.chat.completions.create(
            model=model,
            messages=messages,  # Ensure messages is a list
            **kwargs
        )
        return response

    async def api_call_single(self, messages: list[dict]):
        for attempt in range(self.max_retries):
            try:
                async with self.rate_limit:
                    # Call the API
                    self.pbar.update(1) 
                    client, model = self.get_client()
                    # response = await client.chat.completions.create(
                    #     model=model,
                    #     messages=messages,  # Ensure messages is a list
                    #     **self.kwargs
                    # )
                    response = await self.cached_api_call(client, model, messages, **self.kwargs)
                # Calculate price based on model
                price = self.get_price(model, response)
                # Success, update progress bar and return response
                self.pbar_cmp.update(1) 
                return response, price

            # NOTE: for debugging
            # except (openai.AuthenticationError, openai.NotFoundError):
            #     breakpoint()
            
            except openai.RateLimitError as e:
                print(f"OpenAI API request exceeded rate limit [BASE_URL={client.base_url}, MODEL={model}]: {e}", file=sys.stderr)
                if attempt < self.max_retries - 1:
                    if self.retry_delay_from_message:
                        # example error message:
                        # 'Requests to the ChatCompletions_Create Operation under Azure OpenAI API version 2024-02-01 have exceeded call rate limit of your current OpenAI S0 pricing tier. Please retry after 7 seconds. Please go here: https://aka.ms/oai/quotaincrease if you would like to further increase the default rate limit.'
                        try:
                            wait = float(re.search(r"retry after (\d+) second", str(e)).group(1)) + 0.5 # add 0.5 second buffer
                        except AttributeError:
                            wait = self.retry_delay * (2 ** attempt) # didn't find the retry time, use exponential backoff
                        
                    else:
                        wait = self.retry_delay * (2 ** attempt)  # Exponential backoff formula
                    print(f"Rate limit reached, retrying in {wait:.2f} seconds...", file=sys.stderr)
                    await asyncio.sleep(wait)
                else:
                    print("Max retries reached, unable to complete request.", file=sys.stderr)
                    raise e  # Re-raise the last exception
            except openai.APIConnectionError as e:
                print(f"OpenAI API connection error: {e}, retrying in 10 seconds...", file=sys.stderr)
                await asyncio.sleep(10)
            except asyncio.exceptions.TimeoutError:
                print("Timeout error, retrying in 10 seconds...", file=sys.stderr)
                await asyncio.sleep(10)


    def apply_async(self, messages_list: list[list[dict]]):
        self.pbar = tqdm(total=len(messages_list), desc='Running API calls')
        self.pbar_cmp = tqdm(total=len(messages_list), desc='API calls complete')
        loop = asyncio.get_event_loop()
        # print('A')
        if loop.is_closed():
            asyncio.set_event_loop(asyncio.new_event_loop())
            loop = asyncio.get_event_loop()
        # print('B')
        tasks = [loop.create_task(self.api_call_single(messages)) for messages in messages_list]
        # print('C')
        result = loop.run_until_complete(asyncio.gather(*tasks))
        # print('D')
        # loop.close()
        # print('E')

        ### NON ASYNC VERSION
        # result = []
        # for messages in messages_list:
        #     res = asyncio.run(api_call_single(client, model, messages, pbar, pbar_cmp, **kwargs))
        #     result.append(res)
        ###

        total_price = sum([r[1] for r in result])
        response_list = [r[0] for r in result]
        return total_price, response_list


    def apply_async_batch(self, messages_list: list[list[dict]]):
        grand_total_price = 0
        grand_response_list = []
        for i in tqdm(range(0, len(messages_list), self.batch_size), desc='batches'):
            messages_list_batch = messages_list[i: i + self.batch_size]
            total_price, response_list = self.apply_async(messages_list_batch)
            grand_total_price += total_price
            grand_response_list += response_list
        return grand_total_price, grand_response_list


    def run(self, messages_list: list[list[dict]]):
        # do a test call on one instance to estimate the total cost
        random_number = random.randint(0, len(messages_list) - 1)
        print("Testing on message number " + str(random_number) + " to estimate cost...")
        # random_response_list = apply_async(client, args.model, [messages_list[random_number]], **kwargs)
        random_response_list = self.apply_async([messages_list[random_number]])
        price = random_response_list[0] * len(messages_list)
        print(f"Test messages: {messages_list[random_number]}")
        print(f"Test response: {[c.message.content for c in random_response_list[1][0].choices]}")
        print("Assuming you are running the same model across all endpoints, estimated cost: $" + str(round(price, 3)))

        # breakpoint()
        if price > 1000000 and price <= 10000000:
            input("Estimated cost is above $1000, are you sure you want to proceed? Press enter to continue.")
        # The script will continue after the user presses Enter.
        elif price > 10000000:
            raise ValueError("Estimated cost is above $10000, are you trying to bankrupt Daniel? Please contact him first before proceeding!")
        leftover_message_list = messages_list[0: random_number] + messages_list[random_number + 1:]
        print("Running leftover messages...")
        # response_list = apply_async_batch(client, args.model, leftover_message_list, **kwargs)
        response_list = self.apply_async_batch(leftover_message_list)
        print("Actual cost: " + str(round(response_list[0], 3)) + "$")
        # breakpoint()
        final_response_list = response_list[1][0: random_number] + random_response_list[1] + response_list[1][random_number:]
        return final_response_list