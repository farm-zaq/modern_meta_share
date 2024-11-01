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

set_names = ["mh1", "mh2", "ltr", "mh3"]
set_names_standard = set_names + ["standard"]

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
  response = requests.get(url)
  soup = BeautifulSoup(response.text, 'html.parser')
  decklists = soup.find_all('li', class_='decklists-item')
  challenge_urls = []
  for deck in decklists:
    link_tag = deck.find('a')
    if link_tag:
        link = link_tag.get('href')
        if "modern-challenge" in link:
          challenge_urls.append(link)
  return challenge_urls

def get_set_of_card(cardname):
  for i in range(len(sets)):
    if cardname in sets[i]:
      return set_names[i]
  return "standard"

def get_cards_from_deck(deck, filter_cards=False):
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

def get_cards_from_challenge(link, filter_cards=False):
  challenge_individual_cards, challenge_quantity_cards = generate_sets()
  url = f"https://www.mtgo.com{link}"
  response = requests.get(url)
  soup = BeautifulSoup(response.text, 'html.parser')
  script_tag = soup.find('script', string=re.compile(r'window\.MTGO\.decklists\.data'))
  decklists = None
  if script_tag:
      json_text = re.search(r'window\.MTGO\.decklists\.data\s*=\s*(\{.*?\});', script_tag.string)
      if json_text:
          data = json.loads(json_text.group(1))
          decklists = data["decklists"]
  if decklists:
    for deck in decklists:
      deck_individual_cards, deck_quantity_cards = get_cards_from_deck(deck, filter_cards=filter_cards)
      for key in challenge_individual_cards:
        challenge_individual_cards[key] += deck_individual_cards[key]
        challenge_quantity_cards[key] += deck_quantity_cards[key]
  return challenge_individual_cards, challenge_quantity_cards
  
def get_cards_over_time(start_month, start_year, end_month, end_year, filter_cards=False):
  month = start_month
  year = start_year
  individual_cards, quantity_cards = generate_sets()
  individual_monthly_data = {}
  quantity_monthly_data = {}
  while True:
    print(month)
    challenges = get_challenges(month, year)
    for challenge_link in challenges:
      challenge_individual_cards, challenge_quantity_cards = get_cards_from_challenge(challenge_link, filter_cards=filter_cards)
      individual_monthly_data[f"{year}/{month}"] = {}
      quantity_monthly_data[f"{year}/{month}"] = {}
      for key in individual_cards:
        individual_cards[key] += challenge_individual_cards[key]
        quantity_cards[key] += challenge_quantity_cards[key]
        individual_monthly_data[f"{year}/{month}"][key] = challenge_individual_cards[key]
        quantity_monthly_data[f"{year}/{month}"][key] = challenge_quantity_cards[key]

    month += 1
    if month == 13:
      month = 1
      year += 1
    if year > end_year or (month > end_month and year == end_year):
      break
  return individual_cards, quantity_cards, individual_monthly_data, quantity_monthly_data

def get_percents(cards):
  total = 0
  for key in cards:
    total += cards[key]
  for key in cards:
    cards[key] = int(100 * cards[key] / total)
  return cards

def print_overall_results(indivual_card_percents, quantity_card_percents):
  first_line = "\t\t"
  second_line = "By Single Appearance"
  third_line = "By Each Appearance"
  for set_name in set_names_standard:
    first_line += f"\t{set_name}"
    second_line += f"\t{indivual_card_percents[set_name]}"
    third_line += f"\t{quantity_card_percents[set_name]}"
  print(first_line)
  print(second_line)
  print(third_line)
  
def export_monthly_data(monthly_data, file_name):
  with open(file_name, "w") as file:
    file.write("month,mh1,mh2,ltr,mh3,standard\n")
    for month in monthly_data:
      file.write(month)
      percents = get_percents(monthly_data[month])
      for set_name in set_names_standard:
        file.write(f",{percents[set_name]}")
      file.write("\n")

sets = get_sets_as_sets()

end_month = datetime.now().month
end_year = datetime.now().year
month = 7
year = 2024

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

    # This tracks "individual" cards, so if it appears one or more times in a deck
    # And the "quantity" of cards, so how many times it appears
    individual_cards, quantity_cards,individual_monthly_data, quantity_monthly_data = get_cards_over_time(args.start_month, args.start_year, args.end_month, args.end_year, filter_cards=args.filter_cards)
    indivual_card_percents = get_percents(individual_cards)
    quantity_card_percents = get_percents(quantity_cards)
    print_overall_results(individual_cards, quantity_cards)
    export_monthly_data(individual_monthly_data, args.individual_output_file)
    export_monthly_data(quantity_monthly_data, args.quantity_output_file)
