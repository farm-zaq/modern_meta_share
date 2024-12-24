import os
import requests
from bs4 import BeautifulSoup
import re
import json
import shutil


year = 2019
end_year = 2024
month = 5
end_month = 12

while True:    
  folder = f"./data/{year}/{month}"
  for root, dirs, files in os.walk(folder):
    for dir in dirs:
      if dir != "decklist":
        try:
          new_name = dir.split(" ")[0].split("-")[2]
        except:
          continue
        try:
          os.rename(f"./data/{year}/{month}/{dir}", f"./data/{year}/{month}/{new_name}")
        except OSError as e:
          if e.errno == 66:
            os.makedirs(f"./data/{year}/{month}/{new_name}", exist_ok=True)
            for item in os.listdir(f"./data/{year}/{month}/{dir}"):
                old_item_path = os.path.join(f"./data/{year}/{month}/{dir}", item)
                new_item_path = os.path.join(f"./data/{year}/{month}/{new_name}", item)
                
                if os.path.isdir(old_item_path):
                    shutil.move(old_item_path, new_item_path)
                else:
                    # Move files
                    shutil.move(old_item_path, f"./data/{year}/{month}/{new_name}")
            
            # Delete the now-empty old folder
            os.rmdir(f"./data/{year}/{month}/{dir}")
  month += 1
  if month == 13:
    month = 1
    year += 1
  if year > end_year or (month > end_month and year == end_year):
    break

# while True:    
#   folder = f"./data/{year}/{month}/decklist"
#   for root, dirs, files in os.walk(folder):
#     for file in files:
#       link = f"/decklist/{file}"
#       challenge_url = f"https://www.mtgo.com{link}"
#       response = requests.get(challenge_url)
#       print(response)
#       soup = BeautifulSoup(response.text, 'html.parser')
#       script_tag = soup.find('script', string=re.compile(r'window\.MTGO\.decklists\.data'))
#       print(script_tag)
#       if script_tag:
#         json_text = re.search(r'window\.MTGO\.decklists\.data\s*=\s*(\{.*?\});', script_tag.string)
#         data = json.loads(json_text.group(1))
#         day = data["starttime"].split(" ")[0].split("-")[2]
#         id = data["event_id"]
#         source = f"{folder}/{file}"
#         dest = f"./data/{year}/{month}/{day}/{file}"
#         os.makedirs(os.path.dirname(dest), exist_ok=True)
#         os.rename(source, dest)

#   month += 1
#   if month == 13:
#     month = 1
#     year += 1
#   if year > end_year or (month > end_month and year == end_year):
#     break