
import os
import requests
from bs4 import BeautifulSoup
import re
import json
import shutil
import calendar



year = 2015
end_year = 2024
month = 5
end_month = 12
day = 1

while True:    
  folder = f"./data/legacy/{year}/{month}/{'0' if day < 10 else ''}{day}"
  print(folder)
  for root, dirs, files in os.walk(folder):
    for dir in dirs:
      if dir == "decklist":
        for file_name in os.listdir(f"{folder}/{dir}"):
          source_path = os.path.join(f"{folder}/{dir}", file_name)
          destination_path = os.path.join(folder, file_name)

          if os.path.isfile(source_path):
              shutil.move(source_path, destination_path)
        try:
          os.rmdir(f"{folder}/{dir}")
          shutil.rmtree(f"{folder}/{dir}")
        except:
          pass

  day += 1
  if day > calendar.monthrange(year, month)[1]:
    day = 1
    month += 1
  if month == 13:
    month = 1
    year += 1
  if year > end_year or (month > end_month and year == end_year):
    break