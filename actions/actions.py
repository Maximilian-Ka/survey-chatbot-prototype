# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


import logging
from typing import Any, Text, Dict, List, Tuple
import os
import pandas as pd

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, UserUtteranceReverted, ConversationPaused

from actions.helper import init_survey, find_last_chatbot_question_in_survey, init_skills_df, delay_dispatcher_utterance, _find_latest_bot_question

from actions.NLG.gpt3_connector import GPT3Connector
from actions.evaluation.metrics import PerformanceEvaluator

from time import sleep
from copy import copy
import spacy
import re
from datetime import datetime
import random

def init_skills_and_extract(
    user_input:str, 
    filename:str="emsi_technology_skills.csv", 
    skill_domain:str="emsi",
    cutoff:int=90
    ) -> Tuple[List[str], pd.DataFrame, List[str], List[str]]:
    """ Initializes a dataframe with relevant skills to extract skills from the latest user message.
    
    Args:
        filename: Default, 'edyoucated_skills.csv', or 'onet_alternate_titles_normalized.csv'
        skill_domain: Either 'emsi' or 'edyoucated' or 'onet'
    """
    from actions.extraction.extractor import extract_strings_from_text
    from copy import copy

    skills_df, skills = None, None
    if skill_domain=="emsi":
        skills_df = init_skills_df(filename=filename)
        skills = skills_df["emsi_skill_title_normalized"].tolist()

    elif skill_domain=="onet":
        skills_df = init_skills_df(filename=filename)
        skills = skills_df["title_normalized"].tolist()

    elif skill_domain=="edyoucated":
        skills_df = init_skills_df(filename=filename)
        skills = skills_df["skill_titles_normalized"].tolist()
        abbreviations = skills_df["skill_title_abbreviation"].tolist()
        abbreviations = [x for x in abbreviations if x is not None]
        skills.extend(abbreviations)
        # eliminate np.nan values
        skills = [x for x in skills if x == x]

    # Preprocess latest user input and extract skills
    results = extract_strings_from_text(user_input, skills, cutoff=cutoff)

    # put identified skills in list
    identified_skills = []
    while results:
        match = results.pop(0)
        identified_skills.append(match["match"]) # append the matched target skill
    logging.info(f"--- Found {len(identified_skills)} matching skills ---")

    # Bring identified skills into nice format
    identified_skills_normalized = copy(identified_skills)
    if identified_skills:
        if skill_domain=="emsi":
            # get the unnormalized version of each skill
            identified_skills = skills_df[skills_df['emsi_skill_title_normalized'].isin(identified_skills)]["emsi_skill_title"].tolist()
            # Remove information in parentheses and trailing whitespace
            identified_skills = [re.sub("[\(\[].*?[\)\]]", "", skill).strip() for skill in identified_skills]

        elif skill_domain=="onet":
            identified_skills = skills_df[skills_df['title_normalized'].isin(identified_skills)]["title"].tolist()
            identified_skills = [re.sub("[\(\[].*?[\)\]]", "", skill).strip() for skill in identified_skills]

        elif skill_domain=="edyoucated":
            # get the unnormalized version of each skill (prevent duplicates just in case)
            identified_skills_v1 = skills_df[skills_df['skill_titles_normalized'].isin(identified_skills)]["skill_titles"].tolist()
            identified_skills_v2 = skills_df[skills_df['skill_title_abbreviation'].isin(identified_skills)]["skill_titles"].tolist()
            identified_skills = list(set(identified_skills_v1.extend(identified_skills_v2)))
    else:
        pass

    return identified_skills, skills_df, skills, identified_skills_normalized

def _is_any_skill_in_tags(tags:str, skills:List[str]) -> bool:
    """ Helper function for ActionProcessLearningGoals. 
    
    Args:
        tags: string with skill tags seperated by comma
    """
    for skill in skills:
        if skill in str(tags):
            return True
    return False

def tracker_latest_user_message(tracker:Tracker) -> str:
    """ Substitute for 'tracker.latest_message["text"]'. Ignores messages that start with / """
    events = tracker.events
    latest_user_input = tracker.latest_message["text"]

    for event in reversed(events):
        if event["event"] == "user":
            if not str(event["text"]).startswith("/"):
                latest_user_input = str(event["text"])
                break

    return latest_user_input

def _contains_skip_intent_keyword(tracker:Tracker) -> bool:
    """ Check if latest user message contains keywords that indicates intent to skip. """
    user_message = tracker_latest_user_message(tracker)
    user_message = user_message.lower()
    skip_keywords = ["skip", "don't want", "next"]

    if any(skip_keyword in user_message for skip_keyword in skip_keywords):
        return True
    else:
        return False

def _contains_no_information_intent_keyword(tracker:Tracker) -> bool:
    """ Check if latest user message contains keywords that indicates intent to skip. """
    user_message = tracker_latest_user_message(tracker)
    user_message = user_message.lower()

    skip_keywords = ["dont have", "don't have", "havent got", "haven't got", "there arent any", "there aren't any",
    "i'm not interested", "i am not interested", "nothing"]

    if any(skip_keyword in user_message for skip_keyword in skip_keywords):
        return True
    else:
        return False

class ActionHelloWorld(Action):
    """ Custom Action template. """
    # make link to domain file
    def name(self) -> Text:
        return "action_hello_world"

    # handle the logic
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text="Hello World!")

        return []
class ActionLogStartTime(Action):
    """ Store Start Time of survey in slot for evaluation later on. """

    def name(self) -> Text:
        return "action_log_start_time"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        start = str(datetime.now())

        return [SlotSet(key="survey_start_time", value=start)]


class ActionIdentifyUserName(Action):
    """ Handle user name identification (with help of spacy NER). """
    
    def name(self) -> Text:
        return "action_identify_name"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        chatbot_names = ["Eddy", "eddy", "Edy", "edy", "ed", "Ed"]

        user_message = tracker_latest_user_message(tracker)

        # try to get name from DIETClassifier output
        name = next(tracker.get_latest_entity_values("user_name"), None)
        if name and name not in chatbot_names:
            name = name.title()
            return [SlotSet(key = "user_name", value = name), SlotSet(key = "user_name_identified", value = True)]

        # extract all person-entities from the last user message
        nlp = spacy.load("en_core_web_md")
        doc = nlp(user_message)
        ents = [(e.label_, e.text, e.start_char, e.end_char) for e in doc.ents]
        persons = [entity for entity in ents if entity[0]=="PERSON"]
        
        # extract the user's name
        if persons:
            names = [person[1] for person in persons]

            if len(names) == 1:
                user_name = names[0]
                if user_name in chatbot_names:
                    logging.info("Only found chatbot's name in user meesage.")
                    return [SlotSet(key = "user_name_identified", value = False)]
                else:
                    logging.info(f"Identified name {user_name}")
                    user_name = user_name.title()
                    return [SlotSet(key = "user_name", value = user_name), SlotSet(key = "user_name_identified", value = True)]

            elif len(names) > 1:
                names = [name for name in names if name not in chatbot_names]

                name = names[0].title()
                logging.info(f"Identified name {name}")
                return [SlotSet(key = "user_name", value = name), SlotSet(key = "user_name_identified", value = True)]
        
        else:
            logging.info("Found 0 names or person-entities in user message -> could not identify a name")
            return [SlotSet(key = "user_name_identified", value = False)]


class ActionIdentifyTechnologyInterest(Action):
    """ Extract (technology-related) EMSI Skills from user input. """
    
    def name(self) -> Text:
        return "action_identify_technology_interests"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        sleep(3)
        latest_user_intent = tracker.get_intent_of_latest_message()

        if latest_user_intent == "deny" or latest_user_intent == "no_information":
            if latest_user_intent == "deny" and _contains_skip_intent_keyword(tracker):
                dispatcher.utter_message(response="utter_skipping_question")
            else:
                dispatcher.utter_message(text = "No particular technology interests? No problem 👌")
            return [SlotSet(key = "technology_skill_interests", value = [])]
        else:
            identified_skills, _, _, identified_skills_normalized = init_skills_and_extract(
                tracker_latest_user_message(tracker), filename="emsi_skills.csv")
            
            # Sad path - no skills could be identified -> try lower cutoff (experimental)
            if not identified_skills:
                identified_skills, _, _, identified_skills_normalized = init_skills_and_extract(
                    tracker_latest_user_message(tracker), filename="emsi_skills.csv", skill_domain="emsi", cutoff=87)
            # if still no skills identified
            if not identified_skills:
                identified_skills, _, _, identified_skills_normalized = init_skills_and_extract(
                    tracker_latest_user_message(tracker), filename="edyoucated_skills.csv", skill_domain="edyoucated", cutoff=90) 
            # Happy path - skills could be identified
            if identified_skills:
                skills_copy = identified_skills.copy()
                # Comment on one of the identified skills using GPT-3
                more_than_one = True if len(identified_skills) >= 2 else False
                conn = GPT3Connector()
                comment = conn.gpt3_comment_technology_skill(skills_copy[0], more_than_one_skill=more_than_one)
                comment_on_skill = "If you ask me, " + comment

                tech_savvy = "You seem to be quite tech-savvy 😎\n"
                if len(identified_skills) == 1:
                    text_message = f"You're interested in {identified_skills[0]}?😯\n" + comment_on_skill #I should get into that too 😀"
                elif len(identified_skills) == 2:
                    text_message = f"I see that you're interested in {identified_skills[0]} and {identified_skills[1]} 🤓\n" + tech_savvy + comment_on_skill
                else:
                    last_skill = identified_skills.pop()
                    skills = ', '.join(identified_skills)
                    text_message = f"I see that you're interested in {skills} and {last_skill}. You might be more tech-savvy than me... a robot 🤯\n" + comment_on_skill

                dispatcher.utter_message(text=text_message)
                # TODO: Integrate business integration capability by also mapping to edyoucated ontology
                return [SlotSet(key = "technology_skill_interests", value = identified_skills_normalized)]

            # Unhappy path - no skills could be identified
            else:
                text="Thanks for sharing!😇\nThat doesn't ring a bell with me right now, but I'll make sure to read up this and get back to you! 🤓 "
                dispatcher.utter_message(text=text)
                return [SlotSet(key = "technology_skill_interests", value = [])]
        

class ActionIdentifyGeneralInterests(Action):
    """ Extract interests and reply by generating a response with GPT-3. """

    def name(self) -> Text:
        return "action_identify_general_interests"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        delay_dispatcher_utterance(domain, latest_user_message=tracker_latest_user_message(tracker))
        
        latest_user_intent = tracker.get_intent_of_latest_message()
        tech_interests = tracker.get_slot(key="technology_skill_interests")

        # If intent is deny, 
        # create customized response based on keywords and information stored in slot
        if latest_user_intent == "deny":
            if _contains_skip_intent_keyword(tracker):
                dispatcher.utter_message(response="utter_skipping_question")
            elif _contains_no_information_intent_keyword(tracker):
                if tech_interests:
                    dispatcher.utter_message(text = "You're more of a tech-person anyway, I see 😀")
                else:
                    dispatcher.utter_message(text = "No interests at all? Lame 😝")
            elif tech_interests:
                dispatcher.utter_message(text = "Alright then, keep your secrets 🧙")
            else:
                dispatcher.utter_message(text = "Alright, but you should tell me a bit more about you if you want to get more personalized recommendations 👀")
            return [SlotSet(key = "other_skill_interests", value = [])]

        else:
            identified_skills, _, _, identified_skills_normalized = init_skills_and_extract(
                tracker_latest_user_message(tracker), filename="emsi_skills.csv")
            
            # Sad path - no skills could be identified -> try lwoer cutoff (experimental)
            if not identified_skills:
                identified_skills, _, _, identified_skills_normalized = init_skills_and_extract(
                    tracker_latest_user_message(tracker), filename="emsi_skills.csv", skill_domain="emsi", cutoff=87)
            # if still no skills identified
            if not identified_skills:
                identified_skills, _, _, identified_skills_normalized = init_skills_and_extract(
                    tracker_latest_user_message(tracker), filename="edyoucated_skills.csv", skill_domain="edyoucated", cutoff=90) 
            # Happy path - skills could be identified
            if identified_skills:
                skills_copy = identified_skills.copy()
                # dispatcher.utter_message(text = "Oh yeah, I know some of these 😯")
                if len(identified_skills) == 1:
                    text_message = f"You're interested in {identified_skills[0]}? Sounds cool, maybe I should get into that too 😄"
                elif len(identified_skills) == 2:
                    text_message = f"You're interested in {identified_skills[0]} and {identified_skills[1]}? That sounds cool, maybe I should get into these too 😄"
                else:
                    last_skill = identified_skills.pop()
                    skills = ', '.join(identified_skills)
                    text_message = f"You're interested in {skills} and {last_skill}? That sounds like you're an interesting person 😀"

                text_message = text_message + "\nBy the way, I'll try to find some nice recommendations fitting your interests while we continue the interview. I'll tell you about the results once we're done 😀"
                dispatcher.utter_message(text=text_message)
                # TODO: Integrate business integration capability by also mapping to edyoucated ontology
                return [SlotSet(key = "other_skill_interests", value = identified_skills_normalized)]
                
            # Unhappy path - no skills could be identified
            else:
                text="Interesting!\nI don't think I can recommend any of our learning content related to that to you right away but maybe in the future 😄"
                dispatcher.utter_message(text=text)
                # TODO: Ask the user to rephrase?
                return [SlotSet(key = "other_skill_interests", value = [])]

class ActionIdentifyTasks(Action):
    """ Extract tasks from user input (with GPT-3) as bullet pointed list. """

    def name(self) -> Text:
        return "action_identify_tasks"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        latest_user_intent = tracker.get_intent_of_latest_message()
        if latest_user_intent == "deny":
            if _contains_skip_intent_keyword(tracker):
                dispatcher.utter_message(response="utter_skipping_question")
            else:
                dispatcher.utter_message(text="Don't want to tell me about your tasks? Alright 😄")
            return [SlotSet(key="tasks_user_input", value=""),
            SlotSet(key="tasks_gpt3", value="")]

        conn = GPT3Connector()
        latest_user_message = tracker_latest_user_message(tracker)

        tasks = conn.gpt3_summarize_tasks(latest_user_message)
        

        return [SlotSet(key="tasks_user_input", value=tracker_latest_user_message(tracker)),
        SlotSet(key="tasks_gpt3", value=tasks)]

class ActionGuessJobTitle(Action):
    """ Guess job title based on tasks at work (with GPT-3). """

    def name(self) -> Text:
        return "action_guess_job_title"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        tasks = tracker.get_slot(key="tasks_user_input")
        
        sleep(3)

        # in case user didn't give any tasks (deny, skip)
        if not tasks:
            return [SlotSet(key="job_title_guessed", value=False)]

        text = "Thanks for telling me a bit about your job 🙂\nI have an idea. Let me try to guess your job title based on that! 😁"

        conn = GPT3Connector()
        job_title_guess:str = conn.gpt3_guess_job_title(tasks)

        # TODO: Validate Job Title with O*NET list?

        if job_title_guess:
            #dispatcher.utter_message("That's was a though one, but I think I've got it 💡")
            vowels = ["a","e","i","o","u"]
            article = "an" if job_title_guess[0].lower() in vowels else "a"

            text = text + "\n...\n" + f"I think you might be {article} {job_title_guess}!"
            dispatcher.utter_message(text=text)

            return [SlotSet(key="job_title_guessed", value=True), SlotSet(key="job_title_guess", value=job_title_guess)]

        # Either None response from GPT3 or failed validation
        else:
            text = text + "\n...\n" + "Phew, that's a though one...sorry, I have no idea🙈"
            dispatcher.utter_message(text=text)
            return [SlotSet(key="job_title_guessed", value=False)]

class ActionProcessFeedbackJobTitle(Action):
    """ Checks the user input (button for giving feedback) and acts accordingly.
    (Influences the dialogflow/story). """

    def name(self) -> Text:
        return "action_process_feedback_job_title"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        job_title_guess = tracker.get_slot(key="job_title_guess")

        # accuracy levels: perfect, good, okay, bad
        guess_accuracy_level = next(tracker.get_latest_entity_values("guess_accuracy_level"), None)
        
        if guess_accuracy_level =="perfect":
            dispatcher.utter_message(text="Really? Nice 😎 I'm sure we can use that to make your edyoucated experience more personalized 🦾")
            return [SlotSet(key="guessed_correctly", value=True), SlotSet(key="job_title", value=job_title_guess)]
        elif guess_accuracy_level =="good":
            dispatcher.utter_message(text="Almost then, hehe 😁")
        elif guess_accuracy_level =="okay":
            dispatcher.utter_message(text="Yeah, I thought so 😅")
        elif guess_accuracy_level =="bad":
            dispatcher.utter_message(text="Well, I tried 🙈")
        elif not guess_accuracy_level:
            pass

        return [SlotSet(key="guessed_correctly", value=False)]

class ActionProcessJobTitle(Action):
    """ Extract user's job title from input and comment it with GPT-3. """

    def name(self) -> Text:
        return "action_process_job_title"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        sleep(2)
        logging.info("Processing job title...")
        latest_user_intent = tracker.get_intent_of_latest_message()

        if latest_user_intent == "deny" or latest_user_intent == "no_information":
            if latest_user_intent == "deny" and _contains_skip_intent_keyword(tracker):
                dispatcher.utter_message(response="utter_skipping_question")
            else:
                dispatcher.utter_message(text = "Alright then, keep your secrets 🧙")
            return [SlotSet(key = "job_title", value = "")]
        else:
            job_title = next(tracker.get_latest_entity_values("job_title"), None)

            # If NER failed, try fuzzy lookup in O*NET titles
            if not job_title:
                identified_jobs, _, _, _ = init_skills_and_extract(
                    tracker_latest_user_message(tracker), 
                    filename="onet_alternate_titles_normalized.csv", 
                    skill_domain="onet", 
                    cutoff=92)
                if identified_jobs:
                    job_title = identified_jobs[0]
                else:
                    pass

            # Make nice comment on job title with help of GPT-3
            if job_title:
                job_title = job_title.title()
                vowels = ["a","e","i","o","u"]
                article = "an" if job_title[0].lower() in vowels else "a"

                conn = GPT3Connector()
                positive_comment:str = conn.gpt3_comment_job_title(job_title)

                text = f"You're {article} {job_title}? Awesome! {positive_comment}"

                dispatcher.utter_message(text)
                return [SlotSet(key="job_title", value=job_title)]
            else:
                # Just walk it off (or implement boolean slot return to again ask for job title)
                dispatcher.utter_message(text="Alright, got it 😀")
                return [SlotSet(key="job_title", value="")]

class ActionCommentExperience(Action):
    """ NOT IMPLEMENTED YET """

    def name(self) -> Text:
        return "action_comment_experience"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        delay_dispatcher_utterance(latest_user_message=tracker_latest_user_message(tracker))

        latest_user_intent = tracker.get_intent_of_latest_message()

        if latest_user_intent == "deny" or latest_user_intent == "no_information":
            if latest_user_intent == "deny" and _contains_skip_intent_keyword(tracker):
                dispatcher.utter_message(response="utter_skipping_question")
            else:
                dispatcher.utter_message(text = "Alright then, keep your secrets 🧙")
            return [SlotSet(key = "work_experience", value = None)]
        else:
            # TODO: Use Duckling to get experience
            logging.info("===Logic for ActionCommentExperience is yet to be implemented===s")
            return [SlotSet(key = "work_experience", value = tracker_latest_user_message(tracker))]

class ActionProcessLearningGoals(Action):
    """ Extract Skills from user input and 
    try to recommend suitable Learning Paths. """

    def name(self) -> Text:
        return "action_process_learning_goals"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        sleep(2)
        logging.info("Processing learning goals...")

        latest_user_intent = tracker.get_intent_of_latest_message()

        if latest_user_intent == "deny" or latest_user_intent == "no_information":
            if latest_user_intent == "deny" and _contains_skip_intent_keyword(tracker):
                dispatcher.utter_message(response="utter_skipping_question")
            else:
                dispatcher.utter_message(text = "No learning goals yet? No problem! I'll try my best to find some learing content you might be interested in based on our conversation 😇")
            return [SlotSet(key = "learning_goals", value = [])]

        else:
            identified_skills, _, _, identified_skills_normalized = init_skills_and_extract(
                tracker_latest_user_message(tracker), filename="emsi_skills.csv", skill_domain="emsi")
            logging.info(f"Identified skills: {identified_skills_normalized}")

            # Try to map edyoucated skill titles to the identified skills
            skills_df = init_skills_df(filename="edyoucated_skills.csv")
            df_filtered = skills_df[skills_df.apply(
                lambda x: _is_any_skill_in_tags(tags=x["skill_tags"], 
                skills=identified_skills_normalized), axis=1)]

            skill_recommendations = df_filtered["skill_titles"].unique().tolist()
            logging.info(f"Found skill recommendations: {skill_recommendations}")

            # Tell user about recommendations
            if skill_recommendations:
                bullet_list = ""
                skill_recommendations_copy = skill_recommendations.copy()
                # Limit to 5 recommendations
                if len(skill_recommendations) > 5:
                    skill_recommendations = random.sample(skill_recommendations, 5)
                # Build bullet point list and bot utterances
                for skill in skill_recommendations:
                    bullet_list += f"- {skill}\n"
                if len(identified_skills) == 1:
                    dispatcher.utter_message(text=f"Learning {identified_skills[0]} is a great goal 😇\nI'm pretty sure we can support you with that!")
                if len(identified_skills) > 1:
                    dispatcher.utter_message(text="These are great learning goals 😇\nI'm pretty sure we can support you with that!")
                dispatcher.utter_message(text="For example, you might be interested in our following learning path(s)")
                dispatcher.utter_message(text=bullet_list)
            else:
                dispatcher.utter_message(text="Great that you already have something in mind 😇\n I couldn't find any recommendations for that right away, but I'm pretty sure we can support you with that!")
                identified_skills=[]

            return [SlotSet(key = "learning_goals", value = identified_skills), 
                SlotSet(key="learning_goal_skill_recommendations", value=skill_recommendations_copy)]

class ActionProcessCareerGoals(Action):
    """ Tries to respond adequately to the user's response and 
    stores the user's answer. """

    def name(self) -> Text:
        return "action_process_career_goals"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        sleep(2)
        latest_user_intent = tracker.get_intent_of_latest_message()

        if latest_user_intent == "deny":
            if latest_user_intent == "deny" and _contains_skip_intent_keyword(tracker):
                dispatcher.utter_message(response="utter_skipping_question")
            elif latest_user_intent == "deny" and _contains_no_information_intent_keyword(tracker):
                dispatcher.utter_message(text = "You don't have any career goals at the moment? I see. I'm sure you're doing great where you are 🦾")
            else:
                dispatcher.utter_message(text = "Alright then, keep your secrets 🧙")
            return [SlotSet(key = "career_goals", value = [])]
        else:
            dispatcher.utter_message(text="Sounds good! I believe in you 😎")

        return [SlotSet(key="career_goals", value=tracker_latest_user_message(tracker))]

class ActionCheckChatbotUsedBefore(Action):
    """ Checks whether a user has used a chatbot before and 
    gives tips on what the chatbot can do. """
    
    def name(self) -> Text:
        return "action_check_chatbot_used_before"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        sleep(3)
        logging.info("Checking whether the learner used a chatbot before.")
        latest_user_intent = tracker.get_intent_of_latest_message()

        #hint_1 = "- our interview will be more fun if you take the time to think about the questions and give me some input to work with 🤓"
        hint_1 = "- answering in whole sentences helps me understand you better. I hope you don't mind 😄"
        hint_2 = "- just tell me if you want to skip a question or don't want to answer. No hard feelings 🙂"
        hint_3 = "- if a question seems too vague, you can ask me for more information or an explanation"
        hints = f"Also, here are some hints for talking with me:\n{hint_1}\n{hint_2}\n{hint_3}"
        if latest_user_intent=="affirm":
            dispatcher.utter_message(text="Awesome. I don't think you need any instructions then 😉")#.\nJust keep in mind that I'm still a prototype and we all learn from mistakes. 🙏")
            dispatcher.utter_message(text=hints)
            return [SlotSet(key = "chatbot_used_before", value = True)]

        elif latest_user_intent=="deny":
            dispatcher.utter_message(text="No problem. You're doing great! 😉")
            dispatcher.utter_message(text=hints)
            return [SlotSet(key = "chatbot_used_before", value = False)]
        else:
            return []

class ActionStartSurvey(Action):
    """ React to the check whether the user is ready to start 
    (does not influence story) """
    
    def name(self) -> Text:
        return "action_start_survey"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        sleep(3)

        latest_intent = tracker.get_intent_of_latest_message()
        
        if latest_intent == "affirm":
            dispatcher.utter_message(text="Nice to have you on board! 💪")
        elif latest_intent == "deny":
            dispatcher.utter_message(text="Ah, come on. Might as well try, since you're already here 👀\nIf you really don't want to, you can exit and come back anytime 😉")
        else:
            dispatcher.utter_message(text="Let's get back to that later. I'll assume you're ready for now 🤠")
        
        return []

class ActionRespondMood(Action):
    """ (Dynamically) respond to the user's mood. """

    def name(self) -> Text:
        return "action_respond_mood"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        sleep(3)
        latest_intent = tracker.get_intent_of_latest_message()
        user_input = tracker_latest_user_message(tracker)

        if latest_intent == "mood_great":
            if "?" in user_input or "you" in str(user_input).lower():   # let's assume the user also asked the question back for now
                dispatcher.utter_message(response="utter_happy_thanks")
            else:
                dispatcher.utter_message(response="utter_happy")
        elif latest_intent == "affirm":
            dispatcher.utter_message(response="utter_happy")

        elif latest_intent == "mood_unhappy":
            # TODO: improve this...
            if "?" in user_input:   # let's assume the user also asked the question back for now
                dispatcher.utter_message(text="I'm doing good. Thanks for asking 😇")
            dispatcher.utter_message(response="utter_cheer_up")
        else:
            dispatcher.utter_message(response="utter_happy")
        return []


class ActionContinueSurvey(Action):
    """ Action for resuming the survey at the last chatbot question.
    To be used when the user interrupted the survey with 
    1. small talk, 2. (tbd) ... 
    """

    def name(self) -> Text:
        return "action_continue_survey"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        latest_chatbot_question = _find_latest_bot_question(tracker)
        logging.info(f"Latest chatbot question was: {latest_chatbot_question}")

        if latest_chatbot_question:
            latest_intent = tracker.get_intent_of_latest_message()
            if latest_intent == "tell_repeat_question":
                dispatcher.utter_message(text="Sure, I'll repeat my last question:")
            dispatcher.utter_message(response=latest_chatbot_question)
        else:
            dispatcher.utter_message(text="I actually forgot where we left off 😳 You need to check it yourself 🙏")
        
        return []


class ActionExplainWhy(Action):
    """ Explain to a user why a specific question was asked.
    
    Requires explanation in survey.yaml file.
    """

    def name(self) -> Text:
        return "action_explain_why"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Init survey structure
        survey = init_survey()

        _, latest_question = find_last_chatbot_question_in_survey(tracker, survey)

        if latest_question:
            if latest_question.explain_why:
                dispatcher.utter_message(text=latest_question.explain_why)
            else:
                dispatcher.utter_message(text="It seems like I can't explain why we ask this question yet 🙁 We will work on an explanation for future uses!")
                dispatcher.utter_message(text="If you want to skip this question, just let me know.")
        else:
            dispatcher.utter_message(text="There is nothing to explain here 🤔 I think you should just try to answer the question")

        return []
class ActionRephraseLastQuestion(Action):
    """ Rephrase the last question in case the user did not understand it
    or doesn't know how to answer. 
    
    Requires rephrased question in survey.yaml file.
    """

    def name(self) -> Text:
        return "action_rephrase_last_question"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        survey = init_survey()

        _, latest_question = find_last_chatbot_question_in_survey(tracker, survey)
        logging.info(f"Latest survey question was: {latest_question}")

        if latest_question:
            if latest_question.rephrased_question:
                dispatcher.utter_message(text="Okay, I will rephrase the question:")
                dispatcher.utter_message(text=latest_question.rephrased_question)
            else:
                dispatcher.utter_message(text="Sorry, but I can't rephrase this question or have any more information 🤔")
                dispatcher.utter_message(text="If you want to skip this question, just let me know.")
        else:
            dispatcher.utter_message(text="I can't find anything to rephrase 🤔")

        return []

class ActionHandleReciprocalQuestion(Action):
    """ Rule Action to handle reciprocol questions.
    E.g. user input simply is 'What about you?' as answer to a chatbot question. 
    
    Identifies last question uttered by bot and finds corresponding response template.
    """
    
    def name(self) -> Text:
        return "action_handle_reciprocal_question"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # utter_ask_...
        latest_question = _find_latest_bot_question(tracker)
        
        # response templates for chitchat start with utter_chitchat/ask_....
        if latest_question:
            latest_question = "utter_chitchat/" + str(latest_question.replace('utter_', ''))
            responses:dict = domain["responses"]
            is_in_domain = False

            for k, _ in responses.items():
                if k == latest_question:
                    is_in_domain = True
                    break
            
            # special treatment for interests, as there is only 1 intent for both kinds of interests
            if "interest" in latest_question:
                dispatcher.utter_message(response="utter_chitchat/ask_interests")
                return []
            if is_in_domain:
                dispatcher.utter_message(response=latest_question)
            else:
                dispatcher.utter_message(text="I don't know what you're' referring to 😳")
        else:
            dispatcher.utter_message(text="I don't know what you're' referring to 😳")

        return []

class ActionEndConversation(Action):
    """ Give skill recommendations matching the user's interests (if any), 
    calculate metrics, and utter goodbye. """
    def name(self) -> Text:
        return "action_end_conversation"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Last bot utterance: "You've done it! The survey is now complete. Thank you for participating and happy learning! 😇"

        # Calculate Survey Metrics for Conversation
        start_time:str = tracker.get_slot(key="survey_start_time")
        start_time:datetime = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S.%f')
        end_time = datetime.now()
        evaluator = PerformanceEvaluator()
        engagement_duration = evaluator.compute_engagement_duration(start_time, end_time)

        
        tech_interests:List = tracker.get_slot(key="technology_skill_interests")
        other_interests:List = tracker.get_slot(key="other_skill_interests")
        learning_goal_skill_recommendations = tracker.get_slot(key="learning_goal_skill_recommendations")
        logging.info(f"Found tech interests {tech_interests}")
        logging.info(f"Found other interests {other_interests}")
        if tech_interests:
            if other_interests:
                interests = tech_interests + other_interests
            else:
                interests = tech_interests
        elif other_interests:
            interests = other_interests
        else:
            # no skills/interests were identified
            dispatcher.utter_message(response="utter_goodbye")  # "Have a nice day :) "
            return [SlotSet(key="engagement_duration", value=engagement_duration)]

        # Try to map edyoucated skill titles to the identified skills
        # 'interests' variable is List of normalized skill titles (which are also used to tag edyoucated skills)
        skills_df = init_skills_df(filename="edyoucated_skills.csv")
        df_filtered = skills_df[skills_df.apply(
            lambda x: _is_any_skill_in_tags(tags=x["skill_tags"], 
            skills=interests), axis=1)]

        skill_recommendations:List[str] = df_filtered["skill_titles"].unique().tolist()
        logging.info(f"Found skill recommendations: {skill_recommendations}")

        # Tell user about recommendations
        if skill_recommendations:
            # remove duplicates (don't recommend learning paths that were already recommended)
            if learning_goal_skill_recommendations:
                skill_recommendations = list(set(skill_recommendations) - set(learning_goal_skill_recommendations))

            # no recommendations left
            if not skill_recommendations:
                text = "By the way, next up the information you provided will be used by our platform to make personalized learning content recommendations for you! 🙌\nStay tuned for them appearing on your home screen 🤠"
                dispatcher.utter_message(text=text)
                return [SlotSet(key="engagement_duration", value=engagement_duration)]

            # Limit to 5 recommendations
            if len(skill_recommendations) > 5:
                    skill_recommendations = random.sample(skill_recommendations, 5)
            bullet_list = ""
            for skill in skill_recommendations:
                bullet_list += f"- {skill}\n"

            text = "But before you leave, you might want to have a look at the learning path "
            text += "recommendations I found based on your interests from earlier 👇"
            dispatcher.utter_message(text=text)
            dispatcher.utter_message(text=bullet_list)

        return [SlotSet(key="engagement_duration", value=engagement_duration)]



### Modification of default actions
class ActionLowActionConfidenceFallback(Action):
    """ Handles incoming messages with low action confidence. """

    def name(self) -> Text:
        return "action_nlu_fallback"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # ask the user to rephrase
        dispatcher.utter_message(response="utter_nlu_fallback")

        # Revert user message which led to fallback.
        return [UserUtteranceReverted()]

class ActionDefaultFallback(Action):
    """ Executes the fallback action and goes back to the previous state
    of the dialogue.
    
    or, if enabled: Ultimate Fallback action for Two-Stage-Fallback. (low NLU confidence).
    """

    def name(self) -> Text:
        return 'action_default_fallback'

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        latest_intent = tracker.get_intent_of_latest_message()

        # If user selected out-of-scope intent in default_ask_affirmation
        if latest_intent == "out_of_scope":
            dispatcher.utter_message(response="utter_out_of_scope_fallback")
        else:
            dispatcher.utter_message(response="utter_simple_fallback")

        # Revert user message which led to fallback.
        return [UserUtteranceReverted()]


class ActionDefaultAskAffirmation(Action):
    """ Workaround for bugged Two-Stage-Fallback in Rasa 3.1.x
    
    Basically an enhanced One-Stage-Fallback
    """
    def name(self) -> Text:
            return "action_default_ask_affirmation"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        # select the top three intents from the tracker        
        # ignore the first one -- nlu fallback
        predicted_intents:List[dict] = tracker.latest_message["intent_ranking"][1:4]

        # A prompt asking the user to select an option
        message = "Sorry, I got a bit confused! Did you want to..."

        retrieval_intents = ("chitchat")

        # a mapping between intents and user friendly wordings
        # It's best if all intents are covered here
        intent_mappings = {
            "greet": "Say Hi",
            "goodbye": "Say goodbye",
            "affirm": "Affirm the question",
            "deny":"Deny the question",
            "no_information": "Don't give information",
            "mood_great": "Tell me about your great mood",
            "mood_unhappy": "Tell me about your bad mood",
            "bot_challenge": "Ask whether I'm a bot",
            "chitchat": "Ask me a personal question",
            "tell_name":"Tell me your name",
            "ask_reciprocal_question": "Ask me a question back",
            "tell_interests": "Tell me about your interests",
            "tell_tasks": "Tell me about your tasks",
            "tell_job_title":"Tell me your job title",
            "tell_goals":"Tell me about your goals",
            "tell_goals_interests_tasks":"Tell me about yourself",
            "skip_question":"Skip to the next question",
            "confusion":"Ask for me to rephrase the question",
            "explain_why":"Ask for an explanation"
        }

        full_intent = str((tracker.latest_message.get("response_selector", {}).get("chitchat", {}).get("response", {}).get("intent_response_key", {})))
        # result looks like 'chitchat/ask_interests
        logging.info(f"Full retrieval intent: {full_intent}")
        if full_intent:
            topic = full_intent.split("/")[1]            # e.g. 'ask_interests'
            retrieval_intent = full_intent.split("/")[0] # e.g. 'chitchat'
        else:
            topic = None

        # show the top three intents as buttons to the user - Retrieval Intent version
        buttons = []
        for intent in predicted_intents:
            
            # If retrieval intent in predicitions -> build complex payload
            if str(intent["name"]).startswith(retrieval_intents):
                intent_name = str(intent['name']).split('/')[0] # e.g. /chitchat/ask_goals -> chitchat
                if topic:
                    payload = intent_name + "/" + topic
                    payload = 'trigger_response_selector{"retrieval_intent":"'+ payload + '"}'
                else:
                    payload = intent['name']
                logging.info(f"Retrieval intent ask_affirmation payload: {payload}")
                buttons.append(
                    {
                        "title": intent_mappings[intent_name],
                        "payload": "/{}".format(payload)
                    }
                )
            else:
                buttons.append(
                    {
                        "title": intent_mappings[intent['name']],
                        "payload": "/{}".format(intent['name'])
                    }
                )
        
        # add a "none of these button", if the user doesn't
        # agree when any suggestion
        buttons.append({
            "title": "None of these",
            "payload": "/out_of_scope"
        })
        
        dispatcher.utter_message(text=message, buttons=buttons)

        return []

class ActionTriggerResponseSelector(Action):
    """Returns the chitchat utterance dependent on the intent"""

    def name(self) -> Text:
        return "action_trigger_response_selector_customized"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        retrieval_intent = next(tracker.get_latest_entity_values("retrieval_intent"), None)
        if retrieval_intent:
            dispatcher.utter_message(response = f"utter_{retrieval_intent}")

        return []


# TODO: Override default ActionUnlikelyIntent?
# class ActionUnlikelyIntent(Action):

#     def name(self) -> Text:
#         return "action_unlikely_intent"

#     async def run(
#         self, dispatcher, tracker: Tracker, domain: Dict[Text, Any],
#     ) -> List[Dict[Text, Any]]:

#         # Implement custom logic here
#         return []