from datetime import datetime
from typing import List
import wordfreq as wf
import spacy
import numpy as np
import math

class PerformanceEvaluator():
    """ Class for quantifying interview chatbot performance in various dimensions."""

    # Based on paper: Han, X., Zhou, M., Turner, M. J., & Yeh, T. (2021, May). 
    # Designing effective interview chatbots: Automatic chatbot profiling and design suggestion 
    # generation for chatbot debugging. In Proceedings of the 2021 CHI Conference on Human Factors 
    # in Computing Systems (pp. 1-15).

    def __init__(self, vocabulary_size:str = "md"):
        self.nlp = spacy.load(f"en_core_web_{vocabulary_size}")
        self.total_informativeness = None
        self.total_response_length = None
        self.engagement_duration = None
    
    ### Information Elicitation Metrics:

    def _compute_response_informativeness(self, text_response:str) -> float:
        """ Compute informativeness of a text response by bits(shannons). (Xiao et al 2021)"""

        # "In other words, the more frequently a word (e.g., the common word “the”) appears
        #  in modern English communications, the less information it conveys."
        doc = self.nlp(text_response)
        I_response = 0

        for token in doc:
            if token.is_punct:
                continue

            word_frequency:float = wf.word_frequency(word=token.text, lang='en', minimum=pow(10, -8))
            I_response += math.log2(x=(1/word_frequency)) # sum of each of its word’s 'surprisal' 
            
        if isinstance(I_response, float):
            return I_response
        else:
            return 0

    def compute_participant_informativeness(self, text_responses: List[str]) -> float:
        """ Compute total informativeness for all responses of a participant. """
        I_total = 0
        for response in text_responses:
            I_total += self._compute_response_informativeness(response)

        self.total_informativeness = I_total
        return I_total

    def _compute_response_length(self, text_response: str) -> int:
        """ Compute response length of a text response by retrieving the word count. """

        doc = self.nlp(text_response)
        response_length = 0

        for token in doc:
            if token.is_punct:
                continue
            response_length += 1

        return response_length

    def compute_participant_response_length(self, text_responses: List[str]) -> int:
        """ Compute response length for a survey participant. """
        response_length_total = 0
        for response in text_responses:
            response_length_total += self._compute_response_length(response)

        self.total_response_length = response_length_total
        return response_length_total


    ### User Experience Metrics:

    def compute_chatbot_repetition_rate(self, chatbot_responses: List[str]) -> float:
        """ Computes the frequency an interview chatbot has to repeat itself during an interview. """
        # this computation deviates from papers
        from collections import Counter

        total = len(chatbot_responses)
        response_frequencies = dict(Counter(chatbot_responses))
        
        repetitions = 0
        for k,v in response_frequencies.items():
            repetitions += (v-1) # v = 2 would indicate 2 occurences, hence 1 repitition
        
        repetition_rate = repetitions/total

        return repetition_rate

    def compute_engagement_duration(self, start_time:datetime, end_time:datetime) -> float:
        """ Computes how long a user engaged with a chatbot. """
        duration = end_time - start_time
        duration_in_s = duration.total_seconds()
        duration_in_m:float = round((duration_in_s/60), 2)

        self.engagement_duration = duration_in_m
        return duration_in_m