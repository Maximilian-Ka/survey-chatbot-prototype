# Author: Julian Rasch
# Co-auhtor: Maximilian Kania
from copy import copy
from rapidfuzz import fuzz
from typing import List, Tuple, Union
from nltk import ngrams
from nltk.tokenize import word_tokenize
from collections import deque, Counter

from .preprocessing import preprocess_text


def _compute_match_score(string: str, target_string: str, cutoff: int) -> dict:
    """Computes a matching score between two strings and returns the match, if the score is above a cutoff."""
    if " " in string and " " in target_string:
        f_score = fuzz.token_sort_ratio(string, target_string)
    else:
        f_score = fuzz.ratio(string, target_string)

    if f_score >= cutoff:
        res = {
            "title": string,
            "match": target_string, 
            "score": round(f_score, 2)
        }
    else:
        res = None
    
    return res

def match(string: str, target_string_list: Union[List[str], str], cutoff: int=90) -> List[dict]:
    """ Try to match a string to another string or list of strings. Return all matches with sufficient matching score. """
    if isinstance(target_string_list, str):
        target_string_list = [target_string_list]
    
    matches: List[str] = []

    for target_string in target_string_list:
        match = _compute_match_score(string=string, target_string=target_string, cutoff=cutoff)
        if match: 
            matches.append(match)
    
    matches = sorted(matches, key=lambda x: -x["score"])
    return matches

def best_match(string: str, target_string_list: Union[List[str], str], cutoff: int) -> dict:
    """ Return the best matching word (out of a list of words or single word) for a given input word."""
    if isinstance(target_string_list, str):
        target_string_list = [target_string_list]
    matches = match(string, target_string_list, cutoff)
    try: 
        res = matches[0]
    except IndexError:
        res = None
    return res

def match_and_cut(string: str, target_string_list: List[str], n_gram_size: int, cutoff: int=90) -> Tuple[List[dict], List[str]]:
    """Greedily tries to find matches of certain gram-size between a string and a target string list.
    If a match is found, the remainder of the string is separated into substrings that can be futher processed."""
    matches:List = []
    remainder = []
    processed_string = string
    string = string.lower()

    # create n-grams 
    n_grams = deque(list(ngrams(string.split(" "), n_gram_size)))

    # check for matches greedily
    while len(n_grams) > 0:
        n_gram = n_grams.popleft()
        n_gram_joined = " ".join(n_gram)
        m = best_match(n_gram_joined, target_string_list, cutoff=cutoff)
        if m: 
            matches.append(m)
            # skip next overlapping n-grams
            for _ in range(n_gram_size-1):
                if n_grams:
                    n_grams.popleft()

            # split string at match to find remainder
            spl = [x.strip() for x in processed_string.split(n_gram_joined, maxsplit=1)]
            processed_string = spl[1]
            if spl[0] != "":
                remainder.append(spl[0])
    
    # add back the last bit to the remainder
    if processed_string != "":
        remainder.append(processed_string)

    return matches, remainder

def process_string_list(string_list: List[str], target_string_list: List[str], cutoff: int=90):
    """Matches a list of strings to a list of target strings, using the <match_and_cut> function.
    It starts trying to match longer n-grams and tries smaller ones if no matches could be found and for the remainder.
    """
    strings_to_process = copy(string_list)
    matches:List[dict] = []
    target_string_list = [s.lower() for s in target_string_list]

    for n_gram_size in [4, 3, 2, 1]:
        
        remainders = []
        filtered_ts_list = [s for s in target_string_list if len(s.split(" ")) == n_gram_size] 

        for string in strings_to_process:
            
            match, remainder = match_and_cut(string, filtered_ts_list, n_gram_size, cutoff)
            if match:
                matches.extend(match)
            remainders.extend(remainder)

        strings_to_process = remainders

    return matches, remainders

def process_string_list_test(string_list: List[str], target_string_list: List[str], high_ngram_cutoff: int=85, low_ngram_cutoff=95):
    """Matches a list of strings to a list of target strings, using the <match_and_cut> function.
    It starts trying to match longer n-grams and tries smaller ones if no matches could be found and for the remainder.
    """
    strings_to_process = copy(string_list)
    matches:List[dict] = []
    target_string_list = [s.lower() for s in target_string_list]

    for n_gram_size in [4, 3, 2, 1]:
        if n_gram_size > 2:
            cutoff = high_ngram_cutoff
        else:
            cutoff = low_ngram_cutoff
            
        remainders = []
        filtered_ts_list = [s for s in target_string_list if len(s.split(" ")) == n_gram_size] 

        for string in strings_to_process:
            
            match, remainder = match_and_cut(string, filtered_ts_list, n_gram_size, cutoff)
            if match:
                matches.extend(match)
            remainders.extend(remainder)

        strings_to_process = remainders

    return matches, remainders

def extract_strings_from_text(text: str, target_string_list: List[str], cutoff: int) -> List[List[dict]]:
    """ Extracts all expressions (phrase or word) from the text that match an expression in target list. """
    preprocessed_text = preprocess_text(text)
    extraction, _ = process_string_list(preprocessed_text, target_string_list, cutoff)
    return extraction
    
def cprint(text: str, words_to_highlight: Union[str, List[str]]) -> None:
    """Prints a text into the console while highlighting some words of the text in colors."""
    if isinstance(words_to_highlight, str):
        words_to_highlight = [words_to_highlight]
    for word in words_to_highlight:
        if len(word) > 1:
            if word in text:
                text = text.replace(word, '\033[44;33m{}\033[0;0;0m'.format(word))
            elif word[-1] == "s" and word[:-1] in text: # account for singular vs. plural in English 
                text = text.replace(word[:-1], '\033[44;33m{}\033[0;0;0m'.format(word[:-1]))
    print(text)
