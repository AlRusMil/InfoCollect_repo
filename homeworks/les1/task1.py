# 1. Посмотреть документацию к API GitHub, разобраться как вывести список репозиториев для конкретного пользователя,
# сохранить JSON-вывод в файле *.json.

import requests
import json
import os

path = os.getcwd()
# !!! Введите имя пользователя.
user_name = ''
url = f'https://api.github.com/users/{user_name}/repos'

response = requests.get(url)
repositories = response.json()

# Вывод информации в консоль
print(f"Repo owner: {repositories[0]['owner']['login']}")
print('Repositories list:')
repo_list = []
for item in enumerate(repositories, 1):
    print(f"{item[0]}. {item[1]['html_url']}/{item[1]['name']}")
    repo_list.append(item[1]['name'])

# Вывод в файл полной информации о репозиториях пользователя
with open(f'{path}\\repo_list_info.json', 'w', encoding='utf-8') as f:
    json.dump(repositories, f, ensure_ascii=False, indent=4)

# Вывод в файл только наименований репозиториев.
with open(f'{path}\\repo_list.json', 'w', encoding='utf-8') as f:
    json.dump({user_name: repo_list}, f, ensure_ascii=False, indent=4)
