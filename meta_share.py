from bs4 import BeautifulSoup
import requests
import re
import json
import argparse
import os
import calendar

# set_names = ["mh1", "mh2", "ltr", "mh3"]
# set_names_standard = set_names + ["standard"]

def get_sets_as_sets(separate_standard):
  if not separate_standard:
    set_names = ["MH1", "MH2", "LTR", "MH3", "ACR"]
  else:
    set_names = []
    with open("data/set_codes.csv", "r") as set_file:
      set_lines = set_file.readlines()
      for set_line in set_lines[1:]:
        set_line = set_line.strip()
        code = set_line.split(",")[0]
        set_names.append(code)
  sets = {}
  for set_name in set_names:
    sets[set_name] = set()
    dataset_file_name = f"data/sets/{set_name}.txt"
    with open(dataset_file_name) as f:
      cards = f.readlines()
      for card in cards:
        sets[set_name].add(card.strip())
  sets["Other"] = set()
  return sets

def add_card_sets(bigger, smaller):
  for card in smaller:
    if card not in bigger:
      bigger[card] = 0
    bigger[card] += smaller[card]
  return bigger

#TODO: FILTERING
def get_cards_from_deck(deck_file, is_individual, filter_cards):
  deck_cards = {}
  with open(deck_file, "r") as file:
    response = file.read()
    soup = BeautifulSoup(response, 'html.parser')
    
    card_elements = soup.find_all("div", onclick=lambda x: x and x.startswith("AffCard"))
    for card_element in card_elements:
      quantity = int(card_element.text.split(" ")[0])
      card_name = " ".join(card_element.text.split(" ")[1:])
      card_name = card_name.replace(",", "")
      if card_name not in deck_cards:
        deck_cards[card_name] = 0
        if is_individual:
          deck_cards[card_name] += 1
      if not is_individual:
        deck_cards[card_name] += quantity
  return deck_cards

def get_card_from_event(event_folder, is_individual, filter_cards, min_stars):
  star_file = f"{event_folder}/stars.txt"
  event_cards = {}
  with open(star_file, "r") as file:
    stars = int(file.readline())
    if stars < min_stars:
      return event_cards
  _, _, deck_files = os.walk(event_folder)
  for deck_file in deck_files:
    deck_cards = get_cards_from_deck(deck_file, is_individual, filter_cards)
    event_cards = add_card_sets(event_cards, deck_cards)
  return event_cards

def get_cards_for_day(cur_day, cur_month, cur_year, is_individual, filter_cards, format, min_stars):
  day_cards = {}
  day_folder = f"./data/top8/{format}/{cur_year}/{cur_month}/{cur_day}"
  _, event_dirs, _ = os.walk(day_folder)
  for event_id in event_dirs:
    event_folder = f"{day_folder}/{event_id}"
    event_cards = get_card_from_event(event_folder, is_individual, filter_cards, min_stars)
    day_cards = add_card_sets(day_cards, event_cards)
  return day_cards

def get_cards_for_month(cur_month, cur_year, is_individual, filter_cards, format, min_stars):
  month_cards = {}
  month_folder_name = f"./data/top8/{format}/{cur_year}/{cur_month}"
  _, day_dirs, _ = os.walk(month_folder_name)
  for day in day_dirs:
    day_cards = get_cards_for_day(cur_month, cur_year, day, is_individual, filter_cards, format, min_stars)
    month_cards = add_card_sets(month_cards, day_cards)
  return month_cards
  
def get_cards_over_time_monthly(start_month, start_year, end_month, end_year, is_individual, filter_cards, stored_only, format, min_stars):
  month = start_month
  year = start_year
  all_cards = {}
  while True:
    month_str = f"{year}/{month}"
    print(month_str)
    all_cards[month_str] = get_cards_for_month(month, year, is_individual, filter_cards, format, min_stars)

    month += 1
    if month == 13:
      month = 1
      year += 1
    if year > end_year or (month > end_month and year == end_year):
      break
  return all_cards

def get_cards_over_time_daily(start_day, start_month, start_year, end_month, end_year, is_individual, filter_cards, format, min_stars):
  month = start_month
  year = start_year
  day = start_day
  all_cards = {}
  while True:    
    daily_cards = get_cards_for_day(day, month, year, is_individual, filter_cards, format, min_stars)
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

def get_set_of_card(cardname, sets):
  for set_name in sets:
    if cardname in sets[set_name]:
      return set_name
  return "Other"

def get_percents(cards):
  total = 0
  for key in cards:
    total += cards[key]
  if total == 0:
    return None
  for key in cards:
    cards[key] = round(100 * cards[key] / total, 2)
  return cards

def convert_card_data_to_set_data(all_cards, sets):
  set_data = []
  for key in all_cards:
    period_set_data = {set: 0 for set in sets.keys()}
    for card_name in all_cards[key]:
      card_set = get_set_of_card(card_name, sets)
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
  percent = 0
  if max_count > 0:
    percent = round(100 * max_count / total_count, 2)
  max_name = max_name.replace(",", "")
  return percent, max_name

def convert_card_data_to_most_played_data(all_cards):
  set_data = []
  for period in all_cards:
    percent, max_name = get_most_played_card(all_cards[period])
    if percent > 0:
      line = f"{period},{percent},{max_name}"
      set_data.append(line)
  return set_data

def get_specific_card_percents(period_data, specific_cards):
  total = 0
  for card in period_data:
    total += period_data[card]
  specfic_card_data = []
  for card in specific_cards:
    if card in period_data:
      percent = str(round(100 * period_data[card] / total, 2))
    else:
      percent = str(0)
    specfic_card_data.append(percent)
  if total > 0:
    return specfic_card_data
  else:
    return None

def convert_card_data_to_specific_card_data(all_cards, specific_cards):
  specific_data = []
  for period in all_cards:
    percents = get_specific_card_percents(all_cards[period], specific_cards)
    if percents:
      line_data = ",".join(percents)
      line = f"{period},{line_data}"
      specific_data.append(line)
  return specific_data

def export_data(processed_data, file_name, header):
  with open(file_name, "w") as file:
    file.write(header)
    file.write("\n")
    for line in processed_data:
      file.write(line)
      file.write("\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--start_day', default=1, type=int, help='1-31, inclusive')
    parser.add_argument('--start_month', default=5, type=int, help='1-12, inclusive')
    parser.add_argument('--start_year', type=int, default=2017, help='e.g. 2023, inclusive')
    parser.add_argument('--end_month', type=int, default=12, help='1-12, inclusive')
    parser.add_argument('--end_year', type=int, default=2024, help='e.g. 2023, inclusive')
    parser.add_argument('--is_individual', action="store_true")
    parser.add_argument('--filter_cards', action="store_true")
    parser.add_argument('--output_file', default="output/data.csv", type=str)
    parser.add_argument('--daily', action="store_true")
    parser.add_argument('--output_type', default="set_data", type=str)
    parser.add_argument('--min_stars', default=2, type=int)
    parser.add_argument('--individual_cards', default="", type=str)
    parser.add_argument('--format', default="modern", type=str)
    parser.add_argument('--separate_standard', action="store_true")
    args = parser.parse_args()

    if args.daily:
      all_cards = get_cards_over_time_daily(args.start_day, args.start_month, args.start_year, args.end_month, args.end_year, args.is_individual, args.filter_cards, args.format, args.min_stars)
    else:
      all_cards = get_cards_over_time_monthly(args.start_month, args.start_year, args.end_month, args.end_year, args.is_individual, args.filter_cards, args.format,args.min_stars)
    
    if args.output_type == "set_data":
      sets = get_sets_as_sets(args.separate_standard)
      processed_data = convert_card_data_to_set_data(all_cards, sets)
      header = f"Date,{','.join(sets.keys())}"
    elif args.output_type == "most_played":
      processed_data = convert_card_data_to_most_played_data(all_cards)
      header = "Date,Percent,Name"
    elif args.output_type == "individual_cards":
      individual_cards = args.individual_cards.split(",")
      processed_data = convert_card_data_to_specific_card_data(all_cards, individual_cards)
      header = f"Date,{args.individual_cards}"
    
    export_data(processed_data, args.output_file, header)