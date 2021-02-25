# Написать программу, которая собирает входящие письма из своего или тестового почтового ящика
# и сложить данные о письмах в базу данных (от кого, дата отправки, тема письма, текст письма полный).
# Логин тестового ящика: study.ai_172@mail.ru
# Пароль тестового ящика: NextPassword172

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from selenium.webdriver.common.action_chains import ActionChains

import json
import os
from datetime import date, timedelta, datetime as dt


months = {'01': 'января', '02': 'февраля', '03': 'марта', '04': 'апреля', '05': 'мая', '06': 'июня',
          '07': 'июля', '08': 'августа', '09': 'сентября', '10': 'октября', '11': 'ноября', '12': 'декабря'}


def date_converter(param: str) -> str:
    """
    Функция, которая приводит даты к единому представлению.
    :param param: исходная дата, представленная в виде строки
    :return: дата, приведенная к единому представлению
    """
    tmp = param.lower()
    tmp_list = tmp.split(',')
    if tmp_list[0].find('сегодня') != -1:
        date_list = str(date.today()).split('-')
        tmp = f'{date_list[2]} {months[date_list[1]]} {date_list[0]},{tmp_list[1]}'
    elif tmp_list[0].find('вчера') != -1:
        date_list = str(date.today() - timedelta(days=1)).split('-')
        tmp = f'{date_list[2]} {months[date_list[1]]} {date_list[0]},{tmp_list[1]}'
    elif len(tmp_list[0].split(' ')) == 2:
        tmp = f'{tmp_list[0]} {date.today().year},{tmp_list[1]}'
    return tmp


chrome_options = Options()
chrome_options.add_argument('start-maximized')
driver = webdriver.Chrome(executable_path='./chromedriver', options=chrome_options)

driver.get('https://mail.ru/')

# Вводим логин
input_login = driver.find_element_by_name('login')
input_login.send_keys('study.ai_172')

# Выбираем домен
domain = driver.find_element_by_name('domain')
select = Select(domain)
select.select_by_value('@mail.ru')

# Снимаем галочку с "запомнить меня"
checkbox = driver.find_element_by_id('saveauth')
if checkbox.is_selected():
    checkbox.click()

# Нажимаем кнопку перехода к вводу пароля
button = driver.find_element_by_class_name('button')
button.click()

try:
    # Вводим пароль
    input_password = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.NAME, 'password'))
    )
    input_password.send_keys('NextPassword172')

    # Входим в почту
    button2 = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, 'second-button'))
    )
    button2.click()
except:
    print('ERROR! Не удается получить доступ к полю ввода пароля! Возможно проблемы с соединением!')

container = None
try:
    # Получаем контейнер, содержащий ссылки на письма
    container = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'dataset__items'))
    )
except:
    print('ERROR! Не удается получить доступ к письмам после прохождения авторизации!')

# Сбор ссылок на письма. Представляет собой словарь,
# где ключ представляет собой id ссылки (атрибут data-uidl-id),
# а значение - ссылка на письмо.
links_dict = {}
# Флаг выхода из цикла.
flag = False
while not flag:
    flag = True
    links = container.find_elements_by_class_name('llc')
    for link in links:
        data_uidl_id = link.get_attribute('data-uidl-id')
        if data_uidl_id not in links_dict:
            links_dict[data_uidl_id] = link.get_attribute('href')
            flag = False

    action = ActionChains(driver)
    action.move_to_element(links[-1])
    action.perform()

# Перебор всех писем

# !!!!!!!!!!!!!!!!!!!!!!!!!
# Для проверки работоспособности перебирается только некоторая часть писем
i = 0
mail_count = 20
# !!!!!!!!!!!!!!!!!!!!!!!!!

# Список писем, который содержит в себе словари.
# В каждом словаре содержатся следующие поля:
# 'From' - от кого, 'Date' - дата, 'Subject' - тема письма, 'Content' - содержимое письма.
mails_list = []
for link in links_dict.values():
    driver.get(link)

    mail = {}
    try:
        from_elem = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH,
                                            "//div[contains(@class, 'letter__author')]/span[@class='letter-contact']"))
        )
        mail['From'] = {'Name': from_elem.text, 'Address': from_elem.get_attribute('title')}

        date_elem = driver.find_element_by_class_name('letter__date')
        mail['Date'] = date_converter(date_elem.text)

        subject_elem = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'thread__subject-line'))
        )
        mail['Subject'] = subject_elem.find_element_by_tag_name('h2').text

        content_elem = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@id, 'BODY')]"))
        )
        mail['Content'] = content_elem.text

        mails_list.append(mail)
    except:
        print(f"ERROR! Проблемы при чтении {i+1}го письма.")

    i += 1
    if i == mail_count:
        break

driver.close()

# Запись в файл
print(f'Всего было считано {len(links_dict)} писем.\n')
file_name = f"{os.getcwd()}/mails_{dt.now().strftime('%Y-%m-%d_%H:%M')}.json"
with open(file_name, 'w', encoding='utf-8') as f:
    json.dump(mails_list, f, ensure_ascii=False, indent=4)
print(f"Информация из писем в количестве {len(mails_list)} была записана в файл: {file_name}")
