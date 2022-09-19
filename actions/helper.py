from typing import List, Optional, Text, Tuple
import yaml
import os
from actions.survey.survey import Survey, SurveyItem
from rasa_sdk import Tracker
import logging
import pandas as pd
import numpy as np
import pathlib
import textstat
import warnings
from time import sleep


def init_survey() -> Survey:
    """ Initializes Survey object from yaml file and returns it as output. """
    curr_path = pathlib.Path(__file__).parent
    filepath = curr_path.joinpath("survey", "survey.yaml")

    with open(filepath, 'r') as stream:
        data_loaded = yaml.safe_load(stream)

    survey_items:List[dict] = data_loaded["survey"]
    item_list = [SurveyItem(item_name=item["name"], kwargs=item) for item in survey_items]

    survey = Survey(nodes = item_list)

    return survey

def init_skills_df(filename:str="emsi_technology_skills.csv") -> pd.DataFrame:
    """ Returns skills from given file as DataFrame. """
    curr_path = pathlib.Path(__file__).parent
    filepath = curr_path.joinpath("edyoucated", filename)

    skills_df = pd.read_csv(filepath)

    return skills_df


def _find_latest_bot_question(tracker:Tracker):
    """ Finds the latest chatbot action that started with 'utter_ask' and returns its name. """
    latest_chatbot_question = None
    events = tracker.events
    for event in reversed(events):
        if event["event"] == "action":
            if str(event["name"]).startswith("utter_ask"):
                latest_chatbot_question = str(event["name"])
                break
    logging.info(f"Latest chatbot question was: {latest_chatbot_question}")

    return latest_chatbot_question

def find_last_chatbot_question_in_survey(tracker:Tracker, survey:Survey) -> Tuple[str, SurveyItem]:
    """ Returns latest question asked by chatbot and corresponding match in Survey. """

    # Find latest chatbot question
    latest_chatbot_question = _find_latest_bot_question(tracker)

    # find latest question in survey object
    latest_question = None
    if latest_chatbot_question:
        for survey_item in survey:
            if survey_item.item_name == latest_chatbot_question:
                latest_question:SurveyItem = survey_item
                break

    return latest_chatbot_question, latest_question

def delay_dispatcher_utterance(
    domain: Optional[Text] = None, text: Optional[Text] = None, 
    response: Optional[Text] = None, 
    latest_user_message: Optional[Text] = None
    ) -> None:
    """ Delays bot utterance based on the complexity of the given text/response (and latest user message, if provided). """
    # Perform chatbot response delay according to Gnewuch et al.(2018)

    if response and domain:
        responses:dict = domain["responses"]
        for k, v in responses.items():
            if k == response:
                text= {v[0]["text"]} 
                break
    elif text:
        pass
    elif latest_user_message:
        complexity:float = textstat.flesch_kincaid_grade(latest_user_message)
        delay_in_ms_user_message = ((0.5 * np.log(complexity+0.5) + 1.5) * 1000) if complexity >= 0 else 0
        sleep(delay_in_ms_user_message / 1000)
        return None
    else:
        warnings.warn("Couldn't perform delay.")
        return

    complexity = textstat.flesch_kincaid_grade(text)
    delay_in_ms = ((0.5 * np.log(complexity+0.5) + 1.5) * 1000) if complexity >= 0 else 0

    if latest_user_message:
        complexity = textstat.flesch_kincaid_grade(latest_user_message)
        delay_in_ms_user_message = ((0.5 * np.log(complexity+0.5) + 1.5) * 1000) if complexity >= 0 else 0
        delay_in_ms += delay_in_ms_user_message
    
    sleep(delay_in_ms / 1000)
    return None



