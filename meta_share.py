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

def get_card_from_event(event_id, date, is_individual, filter_cards, format, min_stars):
  day, month, year = date.split("/")
  event_folder = f"data/top8/{format}/{year}/{month}/{day}/{event_id}"
  star_file = f"{event_folder}/stars.txt"
  with open(star_file, "r") as file:
    stars = int(file.readline())
    if stars < min_stars:
      return {}
  _, _, deck_files = os.walk(event_folder)
  for deck_file in deck_files:
    deck_cards = get_cards_from_deck(deck_file, is_individual, filter_cards)

def get_stored_challenge_data(link, cur_month, cur_year, cur_day, format):
  if cur_day:
    date_folder_name = f"./data/top8/{format}/{cur_year}/{cur_month}/{'0' if cur_day < 10 else ''}{cur_day}"
    for _, _, files in os.walk(date_folder_name):
      for file in files:
        if link == file:
          with open(f"{date_folder_name}/{file}", "r") as file:
            decklists = json.load(file)
            return decklists
  else:
    month_folder_name = f"./data/top8/{format}/{cur_year}/{cur_month}"
    for _, dirs, _ in os.walk(month_folder_name):
      for dir in dirs:
        dir = f"{month_folder_name}/{dir}"
        for _, _, files in os.walk(dir):
          for file in files:
            if link == file or (file == link[-len(file):]) or (len(link) > 10 and link[0:10] == "/decklist/" and link[10:] == file):
              with open(f"{dir}/{file}", "r") as file:
                decklists = json.load(file)
                return decklists
  return None

def get_remote_challenge_data(link, cur_month, cur_year, format):
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
    clean_link = link.split("/")[-1]    
    file_name = f"./data/top8/{format}/{cur_year}/{cur_month}/{day}/{clean_link}"
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    with open(file_name, "w") as file:
      json.dump(decklists, file, indent=4)
    return decklists
  return None

def get_cards_from_challenge(link, is_individual, filter_cards, cur_month, cur_year, format, cur_day=None):
  challenge_cards = {}
  decklists = get_stored_challenge_data(link, cur_month, cur_year, cur_day, format)
  if not decklists:
    decklists = get_remote_challenge_data(link, cur_month, cur_year, format)    
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

def get_cards_for_month(cur_month, cur_year, is_individual, filter_cards, stored_only, format):
  if stored_only:
    challenges = []
    month_folder_name = f"./data/top8/{format}/{cur_year}/{cur_month}"
    for _, dirs, _ in os.walk(month_folder_name):
      for dir in dirs:
        dir = f"{month_folder_name}/{dir}"
        for _, _, files in os.walk(dir):
          for file in files:
            challenges.append(file)
  else:
    challenges = get_challenges(cur_month, cur_year, format)
  monthly_cards = {}
  for challenge_link in challenges:
    challenge_cards = get_cards_from_challenge(challenge_link, is_individual, filter_cards, cur_month, cur_year, format)      
    if challenge_cards:
      for card_name in challenge_cards:
        if card_name not in monthly_cards:
          monthly_cards[card_name] = 0
        monthly_cards[card_name] += challenge_cards[card_name]
  return monthly_cards

def get_cards_for_day(month, year, day, is_individual, filter_cards, format):
  daily_cards = {}
  folder = f'./data/top8/{format}/{year}/{month}/{"0" if day < 10 else ""}{day}'
  for root, dirs, files in os.walk(folder):
    for file in files:
      challenge_cards = get_cards_from_challenge(file, is_individual, filter_cards, month, year, format, cur_day=day)  
      if challenge_cards:
        for card_name in challenge_cards:
          if card_name not in daily_cards:
            daily_cards[card_name] = 0
          daily_cards[card_name] += challenge_cards[card_name]
  return daily_cards
  
def get_cards_over_time_monthly(start_month, start_year, end_month, end_year, is_individual, filter_cards, stored_only, format):
  month = start_month
  year = start_year
  all_cards = {}
  while True:
    month_str = f"{year}/{month}"
    print(month_str)
    all_cards[month_str] = get_cards_for_month(month, year, is_individual, filter_cards, stored_only, format)

    month += 1
    if month == 13:
      month = 1
      year += 1
    if year > end_year or (month > end_month and year == end_year):
      break
  return all_cards

def get_cards_over_time_daily(start_day, start_month, start_year, end_month, end_year, is_individual, filter_cards, format):
  month = start_month
  year = start_year
  day = start_day
  all_cards = {}
  while True:    
    daily_cards = get_cards_for_day(month, year, day, is_individual, filter_cards, format)
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
    parser.add_argument('--stored_only', action="store_true")
    parser.add_argument('--individual_cards', default="", type=str)
    parser.add_argument('--format', default="modern", type=str)
    parser.add_argument('--separate_standard', action="store_true")
    args = parser.parse_args()

    if args.daily:
      all_cards = get_cards_over_time_daily(args.start_day, args.start_month, args.start_year, args.end_month, args.end_year, args.is_individual, args.filter_cards, args.format)
    else:
      all_cards = get_cards_over_time_monthly(args.start_month, args.start_year, args.end_month, args.end_year, args.is_individual, args.filter_cards, args.stored_only, args.format)
    
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