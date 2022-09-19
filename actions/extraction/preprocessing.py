# Author: Julian Rasch
# Co-auhtor: Maximilian Kania
from typing import List
import itertools
import re
from nltk.corpus import stopwords
from string import punctuation


def split_text_into_sentences(text: str) -> List[str]:
    '''Split text into sentences at given characters.'''
    split_text = re.split('\. |! |\? |\• |\n', text)
    return list(filter(None, split_text))

def preprocess_sentence(text: str, stop_words: List[str]) -> str:
    no_special_chars = remove_special_chars(text=text)
    text_stopwords_removed = remove_stopwords(text=no_special_chars, stop_words=stop_words)
    return text_stopwords_removed

def split_sentence_at_punctuation(sentence: str) -> List[str]:
    """ Splits a sentence into chunks at punctuation. """
    punctuation_tokens = re.split("\, | \; | \:", sentence)
    punctuation_tokens = [remove_special_chars(token) for token in punctuation_tokens]
    return punctuation_tokens

def split_sentence_at_stopwords(sentence: str, stop_words: List[str]) -> List[str]:
    """ Splits a sentence into chunks at stopwords. """
    sentence_split = sentence.split(" ")
    tokens = [list(y) for x, y in itertools.groupby(sentence_split, lambda z: z.lower() in stop_words) if not x]
    split_tokens = [" ".join(token) for token in tokens] 
    return split_tokens

def remove_special_chars(text: str, and_digits:bool = False) -> str:
    """ Remove special characters, punctuation and whitespace larger than 1 (and digits if needed). """
    special_chars = re.escape(punctuation) + '•'
    if and_digits:
        special_chars = special_chars + '1234567890'
    no_special_chars = re.sub(r'['+special_chars+']', '', text)
    no_special_chars = re.sub(' +', ' ', no_special_chars)
    return no_special_chars

def remove_stopwords(text: str, stop_words: List[str])-> str:
    """ Returns input strings without stopwords. """
    no_stopwords = [
        token for token in text.split(" ") if token not in stop_words and len(token) > 1
    ]
    return " ".join(no_stopwords)

def preprocess_text(text: str)-> List[str]:
    """Splits a text in form of a string into meaningful, connected tokens and cleans them:
    1. The text is split into the different sentences.  
    2. The sentences are split at punctuation (,;:), as skills typically do not cross punctuation.
    3. The resulting tokens are further split at stop words, as skills typically do not contain crosswords.
    4. White spaces are removed and everything is transformed to lower case.
    """
    stop_words = stopwords.words('english')
    sentences_list = split_text_into_sentences(text=text)
    punctuation_tokens = [
        split_sentence_at_punctuation(sentence) for sentence in sentences_list
    ]
    punctuation_tokens_flat = [x for elem in punctuation_tokens for x in elem]
    token_without_stopwords_list = [
        split_sentence_at_stopwords(token, stop_words) for token in punctuation_tokens_flat
    ]
    token_without_stopwords_list_flat = [x for elem in token_without_stopwords_list for x in elem]
    res = [x.strip().lower() for x in token_without_stopwords_list_flat]

    return res

def _replace_symbols(sym_list: list, input: str, repl_sym: str=" "):
    res = input
    for sym in sym_list:
        res = re.sub(sym, repl_sym, res)
    return res