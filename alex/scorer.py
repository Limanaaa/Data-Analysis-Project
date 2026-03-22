#%%

import pickle as pkl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from extract_mda import main_analyzer


def good_bad_words(filepath: str):
    file_good = filepath + "/good_words.pkl"
    file_bad = filepath + "/bad_words.pkl"
    # Extract good
    with open(file_good, "rb") as f:
        good_words = pkl.load(f)
    # Extract bad
    with open(file_bad, "rb") as f:
        bad_words = pkl.load(f)
    return good_words, bad_words


def score_fun(text: str, good_words: list, bad_words: list):
    score_good = 0
    score_bad = 0
    for word in text.split():
        if word in good_words:
            score_good += 1
        elif word in bad_words:
            score_bad += 1
    return score_good, score_bad


if __name__ == "__main__":
    file = "/Users/alexandreviolleau/Documents/Code/Data-Analysis-Project/alex/sec-edgar-filings/0000320193/10-K/0000320193-22-000108/full-submission.txt"
    section = main_analyzer(filepath = file)
    res = section["text"]
    print(res)

    good_words, bad_words = good_bad_words(filepath = "/Users/alexandreviolleau/Documents/Code/Data-Analysis-Project/data_words")
# %%
