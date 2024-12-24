import os
import json
import requests
from bs4 import BeautifulSoup
import re

def get_cards_from_deck(deck, months_cards):
  card_list = []
  if "main_deck" in deck:
      card_list += deck["main_deck"]
  if "sideboard_deck" in deck:
      card_list += deck["sideboard_deck"]
  
  for card in card_list:
    card_name = None
    if "card_attributes" in card and "card_name" in card["card_attributes"]:
        card_name = card["card_attributes"]["card_name"]
    quantity = 0
    if "qty" in card:
        quantity = card["qty"]
    if card_name and quantity:
      if card_name not in months_cards:
        months_cards[card_name] = 0
      months_cards[card_name] += int(quantity)
  return months_cards

def get_cards_from_challenge(link, filter_cards, cur_month, cur_year, months_cards):
  month_folder_name = f"./data/{cur_year}/{cur_month}"
  found_list = False
  for _, dirs, _ in os.walk(month_folder_name):
    for dir in dirs:
      dir = f"{month_folder_name}/{dir}"
      for _, _, files in os.walk(dir):
        for file in files:
          if link == file or (len(link) > 10 and link[0:10] == "/decklist/" and link[10:] == file):
            with open(f"{dir}/{file}", "r") as file:
              decklists = json.load(file)
              found_list = True
  if not found_list:
    challenge_url = f"https://www.mtgo.com{link}"
    response = requests.get(challenge_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    script_tag = soup.find('script', string=re.compile(r'window\.MTGO\.decklists\.data'))
    decklists = None
    if script_tag:
      json_text = re.search(r'window\.MTGO\.decklists\.data\s*=\s*(\{.*?\});', script_tag.string)
      if json_text:
          data = json.loads(json_text.group(1))
          if "decklists" in data:
            decklists = data["decklists"]
          else:
            decklists = None
    if decklists:
      day = data["starttime"].split(" ")[0].split("-")[2]
      id = data["event_id"]
      file_name = f"./data/{cur_year}/{cur_month}/{day}/{id}"
      os.makedirs(os.path.dirname(file_name), exist_ok=True)
      with open(file_name, "w") as file:
        json.dump(decklists, file, indent=4)
  if decklists:
    for deck in decklists:
      months_cards = get_cards_from_deck(deck, months_cards)
    return months_cards
  else:
    return None
  
def get_challenges(month, year):
  url = f"https://www.mtgo.com/decklists/{year}/{0 if month < 10 else ''}{month}?filter=Modern+Challenge"
  decklist_urls = None
  while not decklist_urls:
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    decklist_urls = soup.find_all('li', class_='decklists-item')
  challenge_urls = []
  for deck_url in decklist_urls:
    link_tag = deck_url.find('a')
    if link_tag:
        link = link_tag.get('href')
        if "modern-challenge" in link:
          challenge_urls.append(link)
  return challenge_urls

def get_cards_for_month(cur_month, cur_year, filter_cards):
  challenges = get_challenges(cur_month, cur_year)
  months_data = {}
  months_cards = None
  for challenge_link in challenges:
    months_cards = get_cards_from_challenge(challenge_link, filter_cards, cur_month, cur_year, months_data) 
  if months_cards:     
    total_count = 0
    max_count = 0
    max_name = ""
    for key in months_cards:
      total_count += months_cards[key]
      if months_cards[key] > max_count:
        max_count = months_cards[key]
        max_name = key
    return max_name, round(100 * max_count / total_count, 2)
  return "", 0

def get_cards_over_time(start_month, start_year, end_month, end_year, filter_cards):
  month = start_month
  year = start_year
  
  all_cards = {}


  while True:    
    date_str = f'{year}/{month}'
    name, percent = get_cards_for_month(month, year, filter_cards)
    print((f"{date_str}, {percent}, {name}"))
    if name:
      all_cards[date_str] = (name, percent)
    
    month += 1
    if month == 13:
      month = 1
      year += 1
    if year > end_year or (month > end_month and year == end_year):
      break
  
  return all_cards

def export_monthly_data(month, year, end_month, end_year, all_cards):
  with open("output/top_cards.csv", 'w') as file:
    file.write("month, percent, name\n")
    while True:    
      date_str = f'{year}/{month}'
      name, percent = all_cards[date_str]
      
      file.write(f"{date_str}, {percent}, {name}")
      
      month += 1
      if month == 13:
        month = 1
        year += 1
      if year > end_year or (month > end_month and year == end_year):
        break

start_month = 11
start_year = 2015
end_month = 12
end_year = 2024
export_monthly_data(start_month, start_year, end_month, end_year, get_cards_over_time(start_month, start_year, end_month, end_year, False))