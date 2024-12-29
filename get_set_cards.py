import requests

added_cards = set()

def filter_cards(all_cards):
  basics = ["Forest", "Island", "Swamp", "Mountain", "Plains"]
  unique_cards_dict = list({card["name"]: card for card in all_cards}.values())
  card_names = [card["name"] for card in unique_cards_dict]
  non_alchemy_cards = [card for card in card_names if not card.lower().startswith("a-")]
  non_basic_cards = [card for card in non_alchemy_cards if card not in basics]
  return non_basic_cards

def get_set(code):
  url = "https://api.scryfall.com/cards/search"
  params = {
    "q": f"set:{code}",
    "unique": "prints"
  }

  all_cards = []

  while url:
    response = requests.get(url, params=params)
    if response.status_code == 200:
      data = response.json()
      all_cards.extend(data["data"])
      url = data.get("next_page")
      params = None
    else:
      print(f"Failed to fetch cards: {response.status_code}")
      break
      
  filtered_cards = filter_cards(all_cards)
  with open(f"data/sets/{code}.txt", "w") as file:
    for card in filtered_cards:
      card = card.replace(",", "")
      card = card.split(" // ")[0]
      if card not in added_cards:
        added_cards.add(card)
        file.write(f"{card}\n")

url = "https://api.scryfall.com/sets"
response = requests.get(url)
sets_data = response.json()["data"]
symbols = [(s["name"], s["icon_svg_uri"]) for s in sets_data if "icon_svg_uri" in s]
sets_and_symbols = {
  s["code"]: s["icon_svg_uri"]
  for s in sets_data if "icon_svg_uri" in s
}
with open("data/set_codes.csv", "r") as set_file:
  sets = set_file.readlines()
  for set in sets[1:]:
    set = set.strip()
    code = set.split(",")[0]
    # print(code)
    # get_set(code)
    # print(f'https://images1.mtggoldfish.com/mtg_sets/{code.lower()}_common.png')
    # print(f"https://www.mtgpics.com/graph/sets/symbols/{code}-C.png")
    print(sets_and_symbols[code.lower()])