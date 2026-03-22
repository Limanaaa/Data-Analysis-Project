#%%

import pickle as pkl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from extract_mda import main_analyzer
from scorer import good_bad_words, score_fun

# Dictionary based approach

# This code aims at providing a global pipeline

# 1 -> load a text

file = "/Users/alexandreviolleau/Documents/Code/Data-Analysis-Project/alex/sec-edgar-filings/0000320193/10-K/0000320193-22-000108/full-submission.txt"

analsis = main_analyzer(filepath = file)
results_1 = analsis["text"]

good, bad = good_bad_words(filepath="/Users/alexandreviolleau/Documents/Code/Data-Analysis-Project/data_words")

score_good, score_bad = score_fun(results_1, good, bad)

# %%

import ollama
response = ollama.chat(model='llama3.2', messages=[
    {'role': 'user', 'content': f'Summarize this text : {results_1}'}
])

print(response['message']['content'])

print("Prompt tokens:", response['prompt_eval_count'])
print("Response tokens:", response['eval_count'])
# %%
