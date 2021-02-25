# Написать программу, которая собирает «Хиты продаж» с сайта техники mvideo
# и складывает данные в БД. Магазины можно выбрать свои.
# Главный критерий выбора: динамически загружаемые товары.

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

import time
import json
import os
from datetime import datetime as dt

chrome_options = Options()
chrome_options.add_argument('start-maximized')
driver = webdriver.Chrome(executable_path='./chromedriver', options=chrome_options)

driver.get('https://www.mvideo.ru/')

# Находим все карусели.
uls = driver.find_elements_by_xpath("//div[contains(@class, 'accessories-carousel-wrapper ')]//ul")

elements_count = 0
block_number = 0
target_ul = None

# Перебираем карусели.
for i, ul in enumerate(uls, 1):
    ul_params = ul.get_attribute('data-init-param')
    tmp = ul_params.replace('\n', '')
    tmp_dict = json.loads(tmp)
    # Поиск нужной карусели либо по  слову "хиты", либо по параметру galleryid для хитов продаж.
    # Когда нашли нужный пункт, то запоминаем номер карусли, количество элементов,
    # а также ссылку на интересующую ul.
    # if tmp_dict['ajaxContentLoad']['title'].lower().find('хиты'):
    if tmp_dict['ajaxContentLoad']['contentUrl'].find('block5260655') != -1:
        elements_count = tmp_dict['ajaxContentLoad']['total']
        block_number = i
        target_ul = ul
        break

# Находим кнопку.
block = driver.find_element_by_xpath(f"//div[contains(@class, 'accessories-carousel-wrapper ')][{block_number}]")
button = block.find_element_by_class_name('next-btn')
lis = None
while True:
    button.click()
    time.sleep(1)
    lis = target_ul.find_elements_by_tag_name('li')
    if len(lis) == elements_count:
        break

hits = []
for li in lis:
    hit = {}
    info = li.find_element_by_class_name('fl-product-tile-title__link')
    hit['Link'] = info.get_attribute('href')
    info = json.loads(info.get_attribute('data-product-info'))
    hit['Name'] = info['productName']
    hit['Price'] = info['productPriceLocal']
    hit['Category'] = info['productCategoryName']
    hit['Vendor'] = info['productVendorName']
    hits.append(hit)

file_name = f"{os.getcwd()}/mvideo_hits_{dt.now().strftime('%Y-%m-%d_%H:%M')}.json"
with open(file_name, 'w', encoding='utf-8') as f:
    json.dump(hits, f, ensure_ascii=False, indent=4)
print(f"Хиты продаж М.Видео были сохранены в файл: {file_name}")

driver.close()
