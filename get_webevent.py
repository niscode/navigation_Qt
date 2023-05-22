# -*- config:utf-8 -*-

import requests
from bs4 import BeautifulSoup

response = requests.get('https://startupside.jp/tokyo/event/')
soup = BeautifulSoup(response.text, 'html.parser')
## サイトのタイトルを取得
# title = soup.find('title').get_text()
# print(title)

## イベント名を取得
event_title = soup.find('h3', attrs={'class':'eventBox_title'}).get_text()
print(event_title)

## 日時を取得
event_date = soup.find('span', attrs={'class':'eventBox_en'}).get_text()
print(event_date)

## イベントの種類を取得
event_type = soup.find('li', attrs={'class':'eventBox_type'}).get_text()
print(event_type)