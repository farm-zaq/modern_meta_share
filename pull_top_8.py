from bs4 import BeautifulSoup
import requests
import re
from urllib.parse import parse_qs, urlparse
import os
from pprint import pprint

def read_deck(event_id, deck_id, date, is_individual):
  day, month, year = date.split("/")
  file_name = f"data/top8/{year}/{month}/{day}/{event_id}/{deck_id}"
  deck_cards = {}
  with open(file_name, "r") as file:
    response = file.read()
    soup = BeautifulSoup(response, 'html.parser')
    
    card_elements = soup.find_all("div", onclick=lambda x: x and x.startswith("AffCard"))
    for card_element in card_elements:
      quantity = int(card_element.text.split(" ")[0])
      card_name = " ".join(card_element.text.split(" ")[1:])
      if card_name not in deck_cards:
        deck_cards[card_name] = 0
        if is_individual:
          deck_cards[card_name] += 1
      if not is_individual:
        deck_cards[card_name] += quantity
  return deck_cards

def get_deck(event_id, deck_id, date):
  url = f"https://www.mtgtop8.com/event?e={event_id}&d={deck_id}"
  response = requests.get(url)

  day, month, year = date.split("/")
  file_name = f"data/top8/{year}/{month}/{day}/{event_id}/{deck_id}"
  os.makedirs(os.path.dirname(file_name), exist_ok=True)
  with open(file_name, "w") as file:
    file.write(response.text)

def get_event(event_id):
  url = f"https://www.mtgtop8.com/event?e={event_id}"
  response = requests.get(url)
  soup = BeautifulSoup(response.text, 'html.parser')

  relevant_column = soup.find_all(style="margin:0px 4px 0px 4px;")
  deck_ids = set()
  for element in relevant_column:
    links = [link["href"] for link in element.find_all("a", href=True) if link["href"].startswith("?e")]
    for link in links:
        parsed_link = parse_qs(urlparse(link).query)
        deck_id = parsed_link.get('d', [None])[0]
        deck_ids.add(deck_id)
  deck_ids = list(deck_ids)

  stars = len(soup.find_all("img", src="/graph/star.png")) - 2

  date_pattern = r'\d+/\d+/\d+'
  date_element = soup.find_all(string=re.compile(date_pattern))[0]
  if len(date_element.split(" - ")) > 1:
    date = date_element.split(" - ")[1]
  else:
    date = date_element
  day, month, year = date.split("/")
  print(day, month, year)

  file_name = f"data/top8/{year}/{month}/{day}/{event_id}/stars.txt"
  os.makedirs(os.path.dirname(file_name), exist_ok=True)
  with open(file_name, "w") as file:
    file.write(f"{stars}")

  for deck_id in deck_ids:
    get_deck(event_id, deck_id, date)

def get_page(page_num):
  url = f"https://www.mtgtop8.com/format?f=MO&meta=44&cp={page_num}"
  response = requests.get(url)
  soup = BeautifulSoup(response.text, 'html.parser')

  try:
    header_element = soup.find_all(string=re.compile(r"Events \d+ to \d+"))[0].find_parent()
  except:
    header_element = soup.find_all(string=re.compile(r"LAST \d+ EVENTS"))[0].find_parent()
  next_element = header_element.find_next_sibling()
  while next_element and next_element.find_parent() == header_element:
    next_element = next_element.find_next_sibling()
  deck_table = next_element

  event_ids = []
  links = deck_table.find_all('a', href=True)
  for link in links:
    parsed_link = parse_qs(urlparse(link['href']).query)
    event_id = parsed_link.get('e', [None])[0]
    event_ids.append(event_id)

  for event_id in event_ids:
    get_event(event_id)

for i in range(538,634):
  print(i)
  get_page(i)