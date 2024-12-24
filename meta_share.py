#Disclaimer: This is kind of a work in progress
#Some aspects are messy, and it really needs to use threading because it is slow
#But it works!

from bs4 import BeautifulSoup
import requests
from datetime import datetime
import re
import json
import argparse
import os
import calendar

set_names = ["mh1", "mh2", "ltr", "mh3"]
set_names_standard = set_names + ["standard"]

# This tracks "individual" cards, so if it appears one or more times in a deck
# And the "quantity" of cards, so how many times it appears
individual_monthly_data = {}
quantity_monthly_data = {}

def get_sets_as_sets():
  mh1 = set()
  mh2 = set()
  ltr = set()
  mh3 = set()
  sets = [mh1, mh2, ltr, mh3]
  for i in range(len(sets)):
    dataset_file_name = f"data/{set_names[i]}.txt"
    with open(dataset_file_name) as f:
      cards = f.readlines()
      for card in cards:
        sets[i].add(card.strip())
  return sets

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

def get_cards_from_deck(deck, is_individual, filter_cards):
  deck_cards = {}

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
    if is_individual:
      quantity = 1
    elif "qty" in card:
      quantity = int(card["qty"])
    card_type = None
    if "card_attributes" in card and "card_type" in card["card_attributes"]:
      card_type = card["card_attributes"]["card_type"]

    # filter should really take a function, but I kind of just manually adjusted this line based on what I was filtering
    # is_acceptable = (not filter_cards) or (filter_cards and card_type and "ISCREA" in card_type)
    is_acceptable = (not filter_cards) or (filter_cards and card_type and "LAND" not in card_type)
    if card_name and quantity and is_acceptable:
      if card_name not in deck_cards:
        deck_cards[card_name] = 0
      deck_cards[card_name] += quantity
  return deck_cards

def get_stored_challenge_data(link, cur_month, cur_year, cur_day):
  if cur_day:
    date_folder_name = f"./data/{cur_year}/{cur_month}/{'0' if cur_day < 10 else ''}{cur_day}"
    for _, _, files in os.walk(date_folder_name):
      for file in files:
        if link == file or (len(link) > 10 and link[0:10] == "/decklist/" and link[10:] == file):
          with open(f"{date_folder_name}/{file}", "r") as file:
            decklists = json.load(file)
            return decklists
  else:
    month_folder_name = f"./data/{cur_year}/{cur_month}"
    for _, dirs, _ in os.walk(month_folder_name):
      for dir in dirs:
        dir = f"{month_folder_name}/{dir}"
        for _, _, files in os.walk(dir):
          for file in files:
            if link == file or (len(link) > 10 and link[0:10] == "/decklist/" and link[10:] == file):
              with open(f"{dir}/{file}", "r") as file:
                decklists = json.load(file)
                return decklists
  return None

def get_remote_challenge_data(link, cur_month, cur_year):
  if link[0] != "/":
    link = f"/{link}"
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
    return decklists
  return None

def get_cards_from_challenge(link, is_individual, filter_cards, cur_month, cur_year, cur_day=None):
  challenge_cards = {}
  decklists = get_stored_challenge_data(link, cur_month, cur_year, cur_day)
  if not decklists:
    decklists = get_remote_challenge_data(link, cur_month, cur_year)    
  if decklists:
    for deck in decklists:
      deck_cards = get_cards_from_deck(deck, is_individual, filter_cards)
      for card_name in deck_cards:
        if card_name not in challenge_cards:
          challenge_cards[card_name] = 0
        challenge_cards[card_name] += deck_cards[card_name]
    return challenge_cards
  else:
    return None

def get_cards_for_month(cur_month, cur_year, is_individual, filter_cards):
  challenges = get_challenges(cur_month, cur_year)
  monthly_cards = {}
  for challenge_link in challenges:
    challenge_cards = get_cards_from_challenge(challenge_link, is_individual, filter_cards, cur_month, cur_year)      
    if challenge_cards:
      for card_name in challenge_cards:
        if card_name not in monthly_cards:
          monthly_cards[card_name] = 0
        monthly_cards[card_name] += challenge_cards[card_name]
  return monthly_cards

def get_cards_for_day(month, year, day, is_individual, filter_cards):
  daily_cards = {}
  folder = f'./data/{year}/{month}/{"0" if day < 10 else ""}{day}'
  for root, dirs, files in os.walk(folder):
    for file in files:
      challenge_cards = get_cards_from_challenge(file, is_individual, filter_cards, month, year, cur_day=day)  
      if challenge_cards:
        for card_name in challenge_cards:
          if card_name not in daily_cards:
            daily_cards[card_name] = 0
          daily_cards[card_name] += challenge_cards[card_name]
  return daily_cards
  
def get_cards_over_time_monthly(start_month, start_year, end_month, end_year, is_individual, filter_cards):
  month = start_month
  year = start_year
  all_cards = {}
  while True:
    month_str = f"{year}/{month}"
    all_cards[month_str] = get_cards_for_month(month, year, is_individual, filter_cards)

    month += 1
    if month == 13:
      month = 1
      year += 1
    if year > end_year or (month > end_month and year == end_year):
      break
  return all_cards

def get_cards_over_time_daily(start_month, start_year, end_month, end_year, is_individual, filter_cards):
  month = start_month
  year = start_year
  day = 1
  all_cards = {}
  while True:    
    daily_cards = get_cards_for_day(month, year, day, is_individual, filter_cards)
    date_str = f'{year}/{month}/{"0" if day < 10 else ""}{day}'
    all_cards[date_str] = daily_cards

    day += 1
    if day > calendar.monthrange(year, month)[1]:
      day = 1
      month += 1
    if month == 13:
      month = 1
      year += 1
    if year > end_year or (month > end_month and year == end_year):
      break
  return all_cards

def get_set_of_card(cardname):
  for i in range(len(sets)):
    if cardname in sets[i]:
      return set_names[i]
  return "standard"

def get_percents(cards):
  total = 0
  for key in cards:
    total += cards[key]
  if total == 0:
    return None
  for key in cards:
    cards[key] = int(100 * cards[key] / total)
  return cards

def convert_card_data_to_set_data(all_cards):
  set_data = []
  for key in all_cards:
    period_set_data = {set: 0 for set in set_names_standard}
    for card_name in all_cards[key]:
      card_set = get_set_of_card(card_name)
      period_set_data[card_set] += all_cards[key][card_name]
    percents = get_percents(period_set_data)
    if percents:
      line = key
      for set_name in percents:
        line += f",{percents[set_name]}"
      set_data.append(line)
  return set_data

def get_most_played_card(period_data):
  max_count = 0
  max_name = ""
  total_count = 0
  for key in period_data:
    total_count += period_data[key]
    if period_data[key] > max_count:
      max_count = period_data[key]
      max_name = key
  if max_count > 0:
    percent = round(100 * max_count / total_count, 2)
  return percent, max_name

def convert_card_data_to_most_played_data(all_cards):
  set_data = []
  for period in all_cards:
    percent, max_name = get_most_played_card(all_cards[period])
    if percent > 0:
      line = f"{period},{percent},{max_name}"
      set_data.append(line)
    return set_data

def export_data(processed_data, file_name, header):
  with open(file_name, "w") as file:
    file.write(header)
    file.write("\n")
    for line in processed_data:
      file.write(line)
      file.write("\n")

sets = get_sets_as_sets()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--start_month', default=5, type=int, help='1-12, inclusive')
    parser.add_argument('--start_year', type=int, default=2019, help='e.g. 2023, inclusive')
    parser.add_argument('--end_month', type=int, default=12, help='1-12, inclusive')
    parser.add_argument('--end_year', type=int, default=2024, help='e.g. 2023, inclusive')
    parser.add_argument('--is_individual', action="store_true")
    parser.add_argument('--filter_cards', action="store_true")
    parser.add_argument('--output_file', default="output/data.csv", type=str)
    parser.add_argument('--daily', action="store_true")
    parser.add_argument('--output_type', default="set_data", type=str)
    args = parser.parse_args()

    if args.daily:
      all_cards = get_cards_over_time_daily(args.start_month, args.start_year, args.end_month, args.end_year, args.is_individual, args.filter_cards)
    else:
      all_cards = get_cards_over_time_monthly(args.start_month, args.start_year, args.end_month, args.end_year, args.is_individual, args.filter_cards)
    if args.output_type == "set_data":
      processed_data = convert_card_data_to_set_data(all_cards)
      header = "Date,MH1,MH2,LTR,MH3,Standard"
    elif args.output_type == "most_played":
      processed_data = convert_card_data_to_most_played_data(all_cards)
      header = "Date,Percent,Name"
    export_data(processed_data, args.output_file, header)