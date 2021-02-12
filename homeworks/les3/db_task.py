# 1. Развернуть у себя на компьютере / виртуальной машине / хостинге MongoDB и реализовать функцию, записывающую
# собранные вакансии в созданную БД.
# 2. Написать функцию, которая производит поиск и выводит на экран вакансии с заработной платой больше введённой суммы.
# 3. Написать функцию, которая будет добавлять в вашу базу данных только новые вакансии с сайта.

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from pprint import pprint
from hashlib import md5
import json
import os


class DB:

    db_name = 'db_job'
    ip_address = '127.0.0.1'
    port = 27017

    def __init__(self, ip_address: str = None, port: int = None, db_name: str = None):
        self.ip_address = ip_address if ip_address is not None else DB.ip_address
        self.port = port if port is not None else DB.port
        self.db_name = db_name if db_name is not None else DB.db_name

    @staticmethod
    def id_generate(link: str) -> str:
        """
        Формирует id записи на основе ссылки на вакансию.
        Используется алгоритм хеширование md5.
        :param link: ссылка на вакансию, на основе которой будет формироваться id записи
        :return: id записи
        """
        return md5(link.encode('utf-8')).hexdigest()

    @staticmethod
    def data_insert(collection_name: str, list_vacancies: list,
                    ip_address: str = None, port: int = None, db_name: str = None, ) -> dict:
        """
        Метод, осуществляющий вставку данных в БД.
        :param collection_name: наименование коллекции, куда требуется вставить документы
        :param list_vacancies: список документов для вставки
        :param ip_address: ip адрес сервера
        :param port: порт подключения
        :param db_name: наименование базы данных
        :return: возвращает словарь, содержащий информацию о результатах добавления данных в БД
        """
        ip = ip_address if ip_address is not None else DB.ip_address
        pt = port if port is not None else DB.port
        db_n = db_name if db_name is not None else DB.db_name

        client = MongoClient(ip, pt)
        db = client[db_n] if db_n is not None else client[DB.db_name]

        collect = db[collection_name]

        # Словарь содержит информацию о результатах добавления данных в БД.
        # Первый элемент: 'valid_records_count' - количество успешно добавленных документов.
        # Второй элемент: 'invalid_records' - представляет собой словарь, который содержит следующий элементы:
        # 'count' - количество документов, которые не получилось добавить в связи с повторением,
        # 'records' - список докумнтов, которые не получилось добавить.
        dict_result = {}
        dict_result['valid_records_count'] = 0
        dict_result['invalid_records'] = {}
        dict_result['invalid_records']['count'] = 0
        dict_result['invalid_records']['records'] = []
        for vacancy in list_vacancies:
            ident = DB.id_generate(vacancy['Link'])
            tmp = {**{'_id': ident}, **vacancy}
            try:
                collect.insert_one(tmp)
                dict_result['valid_records_count'] += 1
            except DuplicateKeyError as dke:
                dict_result['invalid_records']['count'] += 1
                dict_result['invalid_records']['records'].append(vacancy)

        return dict_result

    @staticmethod
    def salary_searching(collection_name: str, salary: int, valuta: str,
                         ip_address: str = None, port: int = None, db_name: str = None) -> list:
        """
        Поиск вакансий в базе данных по заданной з/п.
        :param collection_name: наименование коллекции, в которой необходимо осуществлять поиск
        :param salary: размер интересующей заработной платы
        :param valuta: валюта з/п
        :return: список словарей с информацией о вакансиях
        """
        ip = ip_address if ip_address is not None else DB.ip_address
        pt = port if port is not None else DB.port
        db_n = db_name if db_name is not None else DB.db_name

        client = MongoClient(ip, pt)
        db = client[db_n]

        collect = db[collection_name]

        result = collect.find({'Salary.Valuta': valuta,
                               '$or': [{'Salary.Min': {'$gte': salary}}, {'Salary.Max': {'$gte': salary}}]},
                              {'_id': False})

        return list(result)

    @staticmethod
    def db_drop(ip_address: str = None, port: int = None, db_name: str = None):
        """
        Удаляет указанную базу данных. В случае отсутствия параметров,
        удаляет БД согласно атрибутам класса.
        """
        ip = ip_address if ip_address is not None else DB.ip_address
        pt = port if port is not None else DB.port
        db_n = db_name if db_name is not None else DB.db_name

        client = MongoClient(ip, pt)
        client.drop_database(db_n)


if __name__ == "__main__":
    client = MongoClient(DB.ip_address, DB.port)
    db = client[DB.db_name]

    print(client.list_database_names())
    print(db.list_collection_names())
    print(db.vacancies.count_documents({}))

#    slr = 6600
#    vlt = 'USD'
#    list_result = DB.salary_searching('vacancies', slr, vlt)
#    pprint(list_result)
#    file_name = f'{os.getcwd()}\\vacancies_{slr}_{vlt}.json'
#    with open(file_name, 'w', encoding='utf-8') as f:
#        json.dump(list_result, f, ensure_ascii=False, indent=4)

    client.drop_database(DB.db_name)
