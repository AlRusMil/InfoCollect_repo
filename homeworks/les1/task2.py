# Изучить список открытых API (https://www.programmableweb.com/category/all/apis). Найти среди них любое,
# требующее авторизацию (любого типа). Выполнить запросы к нему, пройдя авторизацию. Ответ сервера записать в файл.

# Если нет желания заморачиваться с поиском, возьмите API вконтакте (https://vk.com/dev/first_guide). Сделайте запрос,
# чтобы получить список всех сообществ на которые вы подписаны.

import requests
import json
import os

# APP_ID: 7743931

path = os.getcwd()
# !!! Введите токен.
access_token = ''
url = f'https://api.vk.com/method/groups.get?v=5.52&extended=1&' \
      f'access_token={access_token}&' \
#      f'filter=groups,publics,events'

response = requests.get(url)
groups = response.json()

# Вывод на экран основной информации на экран
print('Список сообществ:')
print('*' * 20)
for item in enumerate(groups['response']['items'], 1):
      print(f"{item[0]}. Наименование: {item[1]['name']}")
      print(f"Screen name: {item[1]['screen_name']}")
      print(f"Тип сообщества: {item[1]['type']}")
      print('*' * 20)

# Вывод в файл полной информации о сообществах пользователя
with open(f'{path}\\group_list.json', 'w', encoding='utf-8') as f:
    json.dump(groups, f, ensure_ascii=False, indent=4)