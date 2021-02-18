# 1. Написать приложение, которое собирает основные новости с сайтов
# mail.ru, lenta.ru, yandex-новости. Для парсинга использовать XPath.
# Структура данных должна содержать:
# название источника;
# наименование новости;
# ссылку на новость;
# дата публикации.
# 2. Сложить собранные данные в БД.

from datetime import date, timedelta, datetime as dt

from pprint import pprint
import requests
from lxml import html

import os
import json

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from hashlib import md5

import re


class NewsInfo:

    # Словарь соответствия для замены названий месяцев их числовыми эквивалентами.
    months = {'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04', 'мая': '05',
              'июня': '06', 'июля': '07', 'августа': '08', 'сентября': '09', 'октября': '10',
              'ноября': '11', 'декабря': '12'}

    def __init__(self, header: str = None,
                 ip_address: str = '127.0.0.1', port: int = 27017,
                 db_name: str = 'db_news', collect_name: str = 'news'):
        self.header = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) '
                                     'AppleWebKit/537.36 (KHTML, like Gecko) '
                                     'Chrome/88.0.4324.182 Safari/537.36'} if header is None else header

        self.ip_address = ip_address
        self.port = port
        self.db_name = db_name
        self.collect_name = collect_name

        # Список, содержащий информацию о событиях с трех новостных ресурсов.
        # Список содержит словари, которые имеют следующую структуру: 'Source' - источник, 'Site' - наименование сайта,
        # 'Text' - наименование новости, 'Link' - ссылка на новость, 'Date' - дата публикации
        self.news = []

    def dom_get(self, url: str, header=None):
        """
        Возвращает dom полученной страницы.
        :param url: куда нужно отправить запрос
        :param header: словарь заголовков
        :return: возвращает dom
        """
        response = requests.get(url, headers=self.header if header is None else header)
        dom = html.fromstring(response.text)
        return dom

    def lenta_news(self):
        """
        Запрос новостей с ресура 'Lenta.ru'. Запрашиваются новости из центральной части страницы и
        из рубрики "Главное".
        :return: None
        """
        dom = self.dom_get(url='https://lenta.ru/')

        for item in dom.xpath("//h2 | //div[@class='item']"):
            novelty = {}

            novelty['Site'] = 'Lenta.ru'
            novelty['Source'] = 'Lenta.ru'

            text = item.xpath('./a/text()')
            novelty['Text'] = text[0].replace('\xa0', ' ')

            link = item.xpath('./a/@href')
            novelty['Link'] = link[0] if link[0].find('lenta.ru') != -1 else f'https://lenta.ru{link[0]}'

            cur_date = item.xpath('.//time/@title')
            if len(cur_date) != 0:
                temp = cur_date[0].split(' ')
                novelty['Date'] = f'{temp[2]}-{NewsInfo.months[temp[1]]}-{temp[0]}'
            else:
                temp = self.dom_get(url=novelty['Link'])
                temp = temp.xpath("//div[@class='b-topic__info']/time/@datetime")
                temp = temp[0].split('T')
                novelty['Date'] = temp[0]

            self.news.append(novelty)
        pprint(self.news)

    def yandex_news(self):
        """
        Запрос новостей с ресура 'Yandex.ru/news/'. Запрашиваются главыне новости
        и региональные новости.
        Текст пути возможно сделать проще, но сделано в соответствии с разделением главных и региональных
        новостей.
        :return: None
        """
        dom = self.dom_get('https://yandex.ru/news/')

        path_main_news = "//div[contains(@class , 'news-top-flexible-stories news-app__top')]" \
                         "/div[contains(@class, 'mg-grid__col mg-grid__col_xs_')]"
        path_region_news = "//div[contains(@class, 'news-top-rubric-flexible-stories')][1]" \
                           "//div[contains(@class, 'mg-grid__col mg-grid__col_xs_4')] | " \
                           "//div[contains(@class, 'news-top-rubric-flexible-stories')][1]" \
                           "//div[contains(@class, 'mg-grid__col mg-grid__col_xs_6')]"

        res_news = f'{path_main_news} | {path_region_news}'
        for item in dom.xpath(res_news):
            novelty = {}

            novelty['Site'] = 'Yandex.ru'
            novelty['Source'] = item.xpath(".//span[@class='mg-card-source__source']/a/text()")[0]

            text = item.xpath(".//h2[@class='mg-card__title']/text()")
            novelty['Text'] = text[0].replace('\xa0', ' ')

            link = item.xpath(".//a[@class='mg-card__link']/@href")
            novelty['Link'] = link[0]

            cur_date = item.xpath(".//span[@class='mg-card-source__time']/text()")
            novelty['Date'] = str(date.today()) if cur_date[0].find('чера') == -1 \
                                                else str(date.today() - timedelta(days=1))

            self.news.append(novelty)
        pprint(self.news)

    def mail_news(self):
        """
        Запрос новостей с ресура 'news.mail.ru'.
        :return: None
        """
        dom = self.dom_get('https://news.mail.ru/')

        path_image_news = "//div[contains(@class, 'daynews__item')]"
        path_text_news = "//ul[contains(@class, 'list_half')]/li[@class='list__item']"

        res_news = f'{path_image_news}|{path_text_news}'
        for item in dom.xpath(res_news):
            link = item.xpath('./a/@href')
            novelty_dom = self.dom_get(link[0])

            source = novelty_dom.xpath("//span[@class='note']//span[@class='link__text']/text()")

            text = novelty_dom.xpath("//h1/text()")
            text = text[0].replace('\xa0', ' ')

            date_news = novelty_dom.xpath("//span[@class='note']/span[contains(@class, 'js-ago')]/@datetime")
            date_news = date_news[0]
            date_news = date_news.split('T')

            novelty = {"Site": "Mail.ru", "Source": source[0], "Text": text, "Link": link[0], "Date": date_news[0]}
            self.news.append(novelty)
        pprint(self.news)

    def save_file(self, path: str) -> str:
        """
        Сохраняет имеющиеся новости в файл в указанную директорию.
        :param path: путь до файла, в который требуется сохранить полученные новости.
        :return: возвращается полное имя файла.
        """
        file_name = f"{path}/news_{dt.now().strftime('%Y-%m-%d_%H:%M')}.json"
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(self.news, f, ensure_ascii=False, indent=4)
        return file_name

    @staticmethod
    def id_generate(info: str) -> str:
        """
        Формирует id записи на основе информации о новости.
        Используется алгоритм хеширование md5.
        :param info: информация о новости, на основе которой будет формироваться id записи
        :return: id записи
        """
        return md5(info.encode('utf-8')).hexdigest()

    def save_db(self):
        """
        Сохраняет имеющуюся информацию в БД.
        :return: возвращает словарь с информацией о результатах добавления данных в БД.
        """
        client = MongoClient(self.ip_address, self.port)
        db = client[self.db_name]

        collect = db[self.collect_name]

        # Словарь содержит информацию о результатах добавления данных в БД.
        # Первый элемент: 'valid_records_count' - количество успешно добавленных новостей.
        # Второй элемент: 'invalid_records' - представляет собой словарь, который содержит следующие элементы:
        # 'count' - количество новостей, которые не получилось добавить в связи с повторением,
        # 'records' - список новостей, которые не получилось добавить.
        dict_result = {}
        dict_result['valid_records_count'] = 0
        dict_result['invalid_records'] = {}
        dict_result['invalid_records']['count'] = 0
        dict_result['invalid_records']['records'] = []
        for item in self.news:
            ident = NewsInfo.id_generate(f"{item['Site']}{item['Source']}{item['Text']}{item['Date']}")
            tmp = {**{'_id': ident}, **item}
            try:
                collect.insert_one(tmp)
                dict_result['valid_records_count'] += 1
            except DuplicateKeyError:
                dict_result['invalid_records']['count'] += 1
                dict_result['invalid_records']['records'].append(item)
        return dict_result

    def drop_db(self):
        """
        Удаляет базу данных.
        :return: None
        """
        for_drop = MongoClient(self.ip_address, self.port)
        for_drop.drop_database(self.db_name)


if __name__ == '__main__':
    news_info = NewsInfo()

    # news_info.drop_db()

    news_info.lenta_news()
    news_info.yandex_news()
    news_info.mail_news()

    print(f"Данные в количестве {len(news_info.news)} новостей сохранены в файле {news_info.save_file(os.getcwd())}")
    print('*' * 20)

    print('\nИнформация по добавлению новостей в БД.')
    dict_result = news_info.save_db()
    print(f"Всего добавлено новостей в БД: {dict_result['valid_records_count']}")
    print(f"Количество новостей, которые не получилось добавить в БД: {dict_result['invalid_records']['count']}")
    if(len(dict_result['invalid_records']['records']) != 0):
        fn = f"{os.getcwd()}/invalid_news_{dt.now().strftime('%Y-%m-%d_%H:%M')}.json"
        with open(fn, 'w', encoding='utf-8') as f:
            json.dump(dict_result['invalid_records']['records'], f, ensure_ascii=False, indent=4)
        print(f"Новости, которые не поучилось добавить в БД сохранены в файле {fn}")
    print('*' * 20)

    print('\nИнформация о БД')
    print(f'IP адрес: {news_info.ip_address}')
    print(f'Порт: {news_info.port}')
    print(f'Наименование БД: {news_info.db_name}')
    print(f'Наименование коллекции: {news_info.collect_name}')
    client = MongoClient(news_info.ip_address, news_info.port)
    db = client[news_info.db_name]
    collect = db[news_info.collect_name]
    print(f'Количество записей в БД: {collect.count_documents({})}')
    print('*' * 20)

    print('\nТестовый вывод:')

    tmp = list(collect.find({'Source': re.compile('^[Ll]enta')}, {'_id': False, 'Text': True, 'Date': True}).limit(3))
    print(f"Три записи из источника 'Lenta.ru':")
    pprint(tmp)

    print(f"Количество записей с сайта 'Yandex.ru': {collect.count_documents({'Site': 'Yandex.ru'})}")

    tmp = list(collect.find({'Site': 'Mail.ru'},
                            {'_id': False, 'Source': True, 'Text': True, 'Date': True}).limit(2))
    print(f"Две записи с сайта 'Mail.ru':")
    pprint(tmp)
