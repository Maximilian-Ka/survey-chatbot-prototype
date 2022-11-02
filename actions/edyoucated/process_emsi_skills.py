# #%%
# import pathlib
# import logging
# from typing import List
# import pandas as pd
# import sys
# import os
# sys.path.insert(1, os.path.join(sys.path[0], '..'))
# from extraction.extractor import extract_strings_from_text
# from extraction.preprocessing import preprocess_text

# #%%
# curr_path = pathlib.Path(__file__).parent
# #filepath = curr_path.joinpath("dim_emsi_skill.csv")
# filepath = curr_path.joinpath("emsi_skills.csv")
# df = pd.read_csv(filepath )
# df.columns = [x.lower() for x in df.columns]
# # %%
# TECHNOLOGY_SKILL_CATEGORIES = ["Information Technology", "Design", "Engineering", 
# "Media and Writing", "Business", "Human Resources", "Finance", 
# "Manufacturing and Production", "Marketing and Public Relations", 
# "Customer and Client Support", "Education and Training", "Science and Research", 
# "Analysis", "Administration", "Sales"]

# #%%
# df_filtered = df.loc[df["category_name"].isin(TECHNOLOGY_SKILL_CATEGORIES)]
# # -> 13952 instead of full 34214 skills
# #%%
# df.drop(columns=["emsi_skill_id", "created_at"], inplace=True)
# df_filtered.drop(columns=["emsi_skill_id", "created_at"], inplace=True)

# #%%
# # Skill to add
# skills_to_add = ["UX design", "Scientific Writing", "Excel", "SQL", "UI design"]
# for skill_to_add in skills_to_add:
#     if skills_to_add not in df["emsi_skill_title"].values:
#         df = df.append({"emsi_skill_title":skill_to_add}, ignore_index=True)
# # skill to kick out
# skills_to_omit = ["Nice (Unix Utility), RExcel"]
# df = df[~df['emsi_skill_title'].isin(skills_to_omit)]
# #%%
# import re
# df_filtered["emsi_skill_title_normalized"] = df_filtered["emsi_skill_title"].map(
#     lambda x: re.sub("\((.*?)\)", " ", x).strip().lower())
# df["emsi_skill_title_normalized"] = df["emsi_skill_title"].map(
#     lambda x: re.sub("\((.*?)\)", " ", x).strip().lower())



# #%%
# df_filtered.to_csv("emsi_technology_skills.csv")
# df.to_csv("emsi_skills.csv")
# # %%
# import re 
# x = "This is a sentence (Blender)"
# re.sub("[\(\[].*?[\)\]]", "", x).strip()
# # %%
