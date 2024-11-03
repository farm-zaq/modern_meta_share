#Disclaimer: This is kind of a work in progress
#Some aspects are messy, and it really needs to use threading because it is slow
#But it works!

from bs4 import BeautifulSoup
import requests
from datetime import datetime
import re
import json
from pprint import pprint
import argparse
import threading

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

def generate_sets():
  individual_cards = {key: 0 for key in set_names_standard}
  quantity_cards = {key: 0 for key in set_names_standard}
  return individual_cards, quantity_cards

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
  print(month, year)
  return challenge_urls

def get_set_of_card(cardname):
  for i in range(len(sets)):
    if cardname in sets[i]:
      return set_names[i]
  return "standard"

def get_cards_from_deck(deck, filter_cards):
  deck_individual_cards, deck_quantity_cards = generate_sets()
  in_deck = set()

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
    card_type = None
    if "card_attributes" in card and "card_type" in card["card_attributes"]:
      card_type = card["card_attributes"]["card_type"]
    # filter should really take a function, but I kind of just manually adjusted this line based on what I was filtering
    # is_acceptable = (not filter_cards) or (filter_cards and card_type and "LAND" not in card_type)
    is_acceptable = (not filter_cards) or (filter_cards and card_type and "ISCREA" in card_type)
    if card_name and quantity and is_acceptable:
      set_name = get_set_of_card(card_name)
      if card_name not in in_deck:
        in_deck.add(card_name)
        deck_individual_cards[set_name] += 1
      deck_quantity_cards[set_name] += int(quantity)
  return deck_individual_cards, deck_quantity_cards

def get_cards_from_challenge(link, filter_cards):
  challenge_individual_cards, challenge_quantity_cards = generate_sets()
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
    for deck in decklists:
      deck_individual_cards, deck_quantity_cards = get_cards_from_deck(deck, filter_cards)
      for key in challenge_individual_cards:
        challenge_individual_cards[key] += deck_individual_cards[key]
        challenge_quantity_cards[key] += deck_quantity_cards[key]
    return challenge_individual_cards, challenge_quantity_cards
  else:
    return None, None

def get_cards_for_month(cur_month, cur_year, filter_cards):
  challenges = get_challenges(cur_month, cur_year)
  individual_monthly_data[f"{cur_year}/{cur_month}"] = {}
  quantity_monthly_data[f"{cur_year}/{cur_month}"] = {}
  for set_name in set_names_standard:
    individual_monthly_data[f"{cur_year}/{cur_month}"][set_name] = 0
    quantity_monthly_data[f"{cur_year}/{cur_month}"][set_name] = 0
  for challenge_link in challenges:
    challenge_individual_cards, challenge_quantity_cards = get_cards_from_challenge(challenge_link, filter_cards)
    if challenge_quantity_cards:
      for key in challenge_individual_cards:
        individual_monthly_data[f"{cur_year}/{cur_month}"][key] += challenge_individual_cards[key]
        quantity_monthly_data[f"{cur_year}/{cur_month}"][key] += challenge_quantity_cards[key]
  
  print(individual_monthly_data[f"{cur_year}/{cur_month}"])

  
def get_cards_over_time(start_month, start_year, end_month, end_year, filter_cards):
  month = start_month
  year = start_year
  threads = []
  while True:    
    thread = threading.Thread(target=get_cards_for_month, args=(month, year, filter_cards))
    threads.append(thread)
    thread.start()

    month += 1
    if month == 13:
      month = 1
      year += 1
    if year > end_year or (month > end_month and year == end_year):
      break
  for thread in threads:
    thread.join()

def get_percents(cards):
  total = 0
  for key in cards:
    total += cards[key]
  for key in cards:
    cards[key] = int(100 * cards[key] / total)
  return cards
  
def export_monthly_data(monthly_data, file_name, start_month, start_year, end_month, end_year):
  month = start_month
  year = start_year
  with open(file_name, "w") as file:
    file.write("month,mh1,mh2,ltr,mh3,standard\n")
    while True:    

      month_str = f"{year}/{month}"
      try:
        percents = get_percents(monthly_data[month_str])
        file.write(month_str)
        for set_name in set_names_standard:
          file.write(f",{percents[set_name]}")
        file.write("\n")
      except:
        print(month_str)
      month += 1
      if month == 13:
        month = 1
        year += 1
      if year > end_year or (month > end_month and year == end_year):
        break

sets = get_sets_as_sets()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--start_month', default=5, type=int, help='1-12, inclusive')
    parser.add_argument('--start_year', type=int, default=2019, help='e.g. 2023, inclusive')
    parser.add_argument('--end_month', type=int, default=10, help='1-12, inclusive')
    parser.add_argument('--end_year', type=int, default=2024, help='e.g. 2023, inclusive')
    parser.add_argument('--filter_cards', default=False, type=bool)
    parser.add_argument('--individual_output_file', default="individual.csv", type=str)
    parser.add_argument('--quantity_output_file', default="quantity.csv", type=str)
    args = parser.parse_args()

    get_cards_over_time(args.start_month, args.start_year, args.end_month, args.end_year, args.filter_cards)
    export_monthly_data(individual_monthly_data, args.individual_output_file, args.start_month, args.start_year, args.end_month, args.end_year)
    export_monthly_data(quantity_monthly_data, args.quantity_output_file, args.start_month, args.start_year, args.end_month, args.end_year)
