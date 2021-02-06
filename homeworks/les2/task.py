# Необходимо собрать информацию о вакансиях на вводимую должность (используем input или через аргументы) с сайтов
# Superjob и HH. Приложение должно анализировать несколько страниц сайта (также вводим через input или аргументы).
# Получившийся список должен содержать в себе минимум:
# * Наименование вакансии.
# * Предлагаемую зарплату (отдельно минимальную, максимальную и валюту).
# * Ссылку на саму вакансию.
# * Сайт, откуда собрана вакансия.
#
# По желанию можно добавить ещё параметры вакансии (например, работодателя и расположение).
# Структура должна быть одинаковая для вакансий с обоих сайтов.
# Общий результат можно вывести с помощью dataFrame через pandas.

from bs4 import BeautifulSoup as bs
import requests
import re
import json
import os
import pandas as pd
from tabulate import tabulate

# HeadHunter
# https://www.hh.ru/
# https://www.hh.ru/search/vacancy?L_save_area=true&clusters=true&enable_snippets=true&text={query}&showClusters=true

# Superjob
# https://www.superjob.ru/
# https://www.superjob.ru/vacancy/search/?keywords={query}&noGeo=1


class IncorrectAction(Exception):

    def __init__(self, message: str):
        self.message = message


class RequestProblem(Exception):

    def __init__(self, message: str):
        self.message = message


class UnknownData(Exception):

    def __init__(self, message: str):
        self.message = message


class WorkSearching:

    # Информация по доступным сайтам
    __list_sites = [('HeadHunter', {'Url': 'https://hh.ru', 'Additional': '/search/vacancy'}),
                    ('Superjob', {'Url': 'https://superjob.ru', 'Additional': '/vacancy/search/'})]

    def __init__(self):
        self.__current_site_number = -1     # Номер выбранного сайта согласно __list_sites
        self.__url = ""

        self.__query = ""
        self.__page_count = 0

        self.__query_headers = {}
        self.__query_params = {}
        # Элементом списка является словарь.
        # Содержит следующие поля: Name - наименование вакансии; Link - ссылка на вакансию;
        # Salary - зарплата, представляющая собой словарь, содержащий поля Min, Max, Valuta
        # Site - наименование сайта, откуда взята вакансия
        # Company - информация о компании
        # Company Link - ссылка на компанию
        self.list_result = []

        # DataFrame
        self.df_result = pd.DataFrame(columns=['Name', 'Link', 'Min Salary', 'Max Salary', 'Valuta', 'Site name',
                                               'Company', 'Company Link'])

    def menu(self):
        print("Сайты для поиска:")
        for point, site in enumerate(self.__list_sites, 1):
            print(f'{point}. {site[0]}')
        print('q. Выйти ')

    @property
    def site_name(self):
        return WorkSearching.__list_sites[self.__current_site_number][0]

    @property
    def url(self):
        return self.__url

    @url.setter
    def url(self, param: int):
        self.__current_site_number = param - 1    # Выбор сайта в меню на единицу больше, чем номер в списке сайтов.
        # Проверяем, что выбран существующий номер.
        if (self.__current_site_number < 0) or (self.__current_site_number >= len(WorkSearching.__list_sites)):
            raise IncorrectAction("ERROR! Вы выбрали несуществующий пункт меню!")
        else:
            # Формируем url
            self.__url = WorkSearching.__list_sites[self.__current_site_number][1]['Url'] + \
                         WorkSearching.__list_sites[self.__current_site_number][1]['Additional']

    @property
    def query(self):
        return self.__query

    @query.setter
    def query(self, param: str) -> None:
        """
        Сеттер, получающий поисковый запрос, а также формирующий заголовки и параметры hhtp-запроса
        :param param: поисковый запрос
        :return: None
        """
        if self.__current_site_number == -1:
            raise IncorrectAction("ERROR! Не выбран сайт для осуществления поиска вакансий!")

        self.__query = param

        # Формируем список заголовков и параметров запроса
        self.__headers_list()
        self.__params_list()

    @property
    def pages(self):
        return self.__page_count

    @pages.setter
    def pages(self, page_count):

        if page_count == '':
            self.__page_count = 'max'
        else:
            tmp = int(page_count)
            if tmp <= 0:
                raise IncorrectAction("ERROR! Количество страниц должно быть больше нуля!")
            self.__page_count = tmp

    def __headers_list(self) -> None:
        """
        Метод, формирующий список заголовков запроса.
        :return: None
        """
        self.__query_headers["User-Agent"] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' \
                                             'AppleWebKit/537.36 (KHTML, like Gecko) ' \
                                             'Chrome/88.0.4324.104 ' \
                                             'Safari/537.36'
        self.__query_headers["Accept"] = '*/*'
        return

    def __params_list(self) -> None:
        """
        Метод, формирующий список параметров для отправки запроса.
        :return: None
        """
        # https://www.hh.ru/search/vacancy?L_save_area=true&clusters=true&enable_snippets=true&text={query}&showClusters=true
        if WorkSearching.__list_sites[self.__current_site_number][0] == 'HeadHunter':
            self.__query_params["L_save_area"] = 'true'
            self.__query_params["clusters"] = 'true'
            self.__query_params["enable_snippets"] = 'true'
            self.__query_params["showClusters"] = 'true'

            self.__query_params["text"] = self.query
        # https://www.superjob.ru/vacancy/search/?keywords={query}&noGeo=1
        elif WorkSearching.__list_sites[self.__current_site_number][0] == 'Superjob':
            self.__query_params["noGeo"] = '1'

            self.__query_params["keywords"] = self.query
        return

    def __link_complete(self, link: str) -> str:
        """
        Метод, который, при необходимости, дополняет ссылку до полноценной.
        :param link: ссылка, которую требуется проверить на завершенность
        :return: полная ссылка (вместе с сайтом).
        """

        full_link = link if link.find(WorkSearching.__list_sites[self.__current_site_number][1]["Url"]) != -1 \
            else f'{WorkSearching.__list_sites[self.__current_site_number][1]["Url"]}{link}'

        return full_link

    def http_request(self, url_param: str = None):
        """
        Метод отправляет запрос к серверу.
        Если ошибка, то генерируется исключение.
        В случае успеха возвращается "распарсенный" результат запроса.
        :param url_param: содержит url, по которому необходимо отправить запрос, если он отсутствует,
                          то используется url, который содержится внутри экземпляра класса.
        :return: результат запроса к серверу
        """

        if isinstance(url_param, str):
            response = requests.get(self.__link_complete(url_param), headers=self.__query_headers)
        else:
            response = requests.get(self.url, params=self.__query_params, headers=self.__query_headers)

        if not response.ok:
            raise RequestProblem(f'ERROR. Problem with request. Status code: {response.status_code}')

        return bs(response.text, "html.parser")

    @staticmethod
    def __salary_parsing(salary: str) -> dict:
        """
        Метод, который обрабатывает строку с информацией о з/п
        :param salary: строка, содержащая информацию о з/п
        :return: словарь, содержащий поля 'Min', 'Max', 'Valuta' или 'Salary', 'Valuta'
        """

        dict_result = {}
        tmp = salary.replace('\xa0', '')     # убираем неразрывный пробел
        tmp = tmp.replace(' ', '')      # убираем пробел
        tmp = tmp.replace('.', '')      # убираем точку в конце валюты

        tmp_digits = re.findall(r'\d+', tmp)
        # маска: sum-sum...valuta
        if len(tmp_digits) == 2:
            dict_result['Min'] = tmp_digits[0]
            dict_result['Max'] = tmp_digits[1]
            dict_result['Valuta'] = re.search(r'[a-zA-Zа-яА-ЯеЁ]+$', tmp).group()
        # маска: sum...valuta
        elif re.search(r'([оО][тТ])|([дД][оО])', tmp) is None:
            dict_result['Salary'] = tmp_digits[0]
            # dict_result['Min'] = tmp_digits[0]
            # dict_result['Max'] = tmp_digits[0]
            dict_result['Valuta'] = re.search(r'[a-zA-Zа-яА-ЯеЁ]+$', tmp).group()
        # маска: от...sum...valuta
        elif re.search(r'[оО][тТ]', tmp) is not None:
            dict_result['Min'] = tmp_digits[0]
            dict_result['Max'] = 'not specified'
            dict_result['Valuta'] = re.search(r'[a-zA-Zа-яА-ЯеЁ]+$', tmp).group()
        # маска: до...sum...valuta
        elif re.search(r'[дД][оО]', tmp) is not None:
            dict_result['Min'] = 'not specified'
            dict_result['Max'] = tmp_digits[0]
            dict_result['Valuta'] = re.search(r'[a-zA-Zа-яА-ЯеЁ]+$', tmp).group()
        else:
            raise UnknownData("ERROR! Неизвестный формат представления з/п!")

        return dict_result

    def result_processing(self, pr: bs) -> None:
        """
        Обрабатывает и сохраняет в словарь полученную информацию о вакансиях.
        :param pr: Содержит в себе "распарсенный" response
        :return: None
        """
        parsed_response = pr

        if WorkSearching.__list_sites[self.__current_site_number][0] == 'HeadHunter':
            # Количество вакансий на HeadHunter
            numb = parsed_response.find('h1', {'class': 'bloko-header-1'})
            print(f'Всего найдено вакансий  на {self.__list_sites[self.__current_site_number][0]}: {numb.text}')

            # Подготовка информации о классах, по которым будет осуществляться поиск.
            div_class_items = 'vacancy-serp'     # класс тэга div, содержащего  информацию о вакансих
            div_class_item = 'vacancy-serp-item'    # класс тэга div, содержащего информацию о вакансии

            div_class_name = 'vacancy-serp-item__info'  # класс тэга div, содержащего информацию о названии вакансии
            a_class_name = 'bloko-link'  # класс тэга a, содержащего ссылку и название вакансии

            div_class_salary = 'vacancy-serp-item__sidebar'  # класс тэга div, содержащего информацию о з/п
            span_class_salary = 'bloko-section-header-3 bloko-section-header-3_lite'  # класс тэга span с з/п

            site_name = WorkSearching.__list_sites[self.__current_site_number][0]

            div_class_company = 'vacancy-serp-item__meta-info-company'  # класс тэга div, содержащего инф-ю о компании
            a_class_company = 'bloko-link bloko-link_secondary'     # класс тэга a, содержащего инф. о компании + ссылка

            # Информация по кнопке "дальше"
            a_class_button_next = 'bloko-button HH-Pager-Controls-Next HH-Pager-Control'    # кнопка дальше

            # Перебор найденных вакансий
            i_page_counter = 0
            i_vacancy_counter = 0
            while True:
                print(f'Обрабатывается {i_page_counter + 1} страница из {self.__page_count}.')

                # Элементом списка является словарь.
                # Содержит следующие поля: Name - наименование вакансии; Link - ссылка на вакансию;
                # Salary - зарплата, представляющая собой словарь, содержащий поля Min, Max, Valuta
                # Site - наименование сайта, откуда взята вакансия
                # Company - информация о компании
                # Company Link - ссылка на компанию

                # Получение списка вакансий
                vacancies_container = parsed_response.find('div', {'class': div_class_items})
                vacancies = vacancies_container.find_all('div', {'class': div_class_item})

                for vacancy in vacancies:

                    dict_vacancy = {}     # Словарь с информацией о вакансии
                    # Наименование вакансии и ссылка на вакансию
                    vacancy_name = vacancy.find('div', {'class': div_class_name})
                    name_info = vacancy_name.find('a', {'class': a_class_name})
                    dict_vacancy['Name'] = name_info.text
                    dict_vacancy['Link'] = self.__link_complete(name_info['href'])

                    # З/П
                    vacancy_salary = vacancy.find('div', {'class': div_class_salary})
                    salary = vacancy_salary.find('span', {'class': span_class_salary})
                    if salary is None:
                        dict_vacancy['Salary'] = 'by agreement'
                        # dict_vacancy['Salary']['Min'] = 'by agreement'
                        # dict_vacancy['Salary']['Max'] = 'by agreement'
                        # dict_vacancy['Salary']['Valuta'] = 'by agreement'
                    else:
                        dict_vacancy['Salary'] = self.__salary_parsing(salary.text)

                    # Информация о компании
                    vacancy_company = vacancy.find('div', {'class': div_class_company})
                    company_info = vacancy_company.find('a', {'class': a_class_company}) if vacancy_company is not None\
                        else None
                    if company_info is None:
                        dict_vacancy['Company'] = ''
                        dict_vacancy['Company Link'] = ''
                    else:
                        dict_vacancy['Company'] = company_info.text
                        dict_vacancy['Company Link'] = self.__link_complete(company_info['href'])

                    # Наименование сайта
                    dict_vacancy['Site'] = site_name

                    self.list_result.append(dict_vacancy)
                    # self.df_adding(i_vacancy_counter, dict_vacancy)

                    i_vacancy_counter = i_vacancy_counter + 1

                # Проверяем количество просмотренных страниц
                i_page_counter = i_page_counter + 1
                if self.__page_count != 'max':
                    if i_page_counter >= self.__page_count:
                        break

                # Проверяем наличие следующей страницы
                next_button = parsed_response.find('a', {'class': a_class_button_next})
                if next_button is None:
                    break
                parsed_response = self.http_request(next_button["href"])

        elif WorkSearching.__list_sites[self.__current_site_number][0] == 'Superjob':
            # Количество вакансий на Superjob
            numb = parsed_response.find('span', {'class': '_3mfro _1ZlLP _2JVkc _2VHxz'})
            print(f'Всего найдено вакансий  на {self.__list_sites[self.__current_site_number][0]}: {numb.text}')

            # Подготовка информации о классах, по которым будет осуществляться поиск.

            # класс тэга div, содержащего информацию о вакансии
            div_class_item = 'iJCa5 f-test-vacancy-item _1fma_ undefined _2nteL'

            # класс тэга div, содержащего информацию о названии вакансии
            # класс тэга a, содержащего ссылку и название вакансии, находится в тэге div (везде индивидуальный)
            div_class_name = '_3mfro PlM3e _2JVkc _3LJqf'

            span_class_salary = '_3mfro _2Wp8I PlM3e _2JVkc _2VHxz'  # класс тэга span с з/п
            # span_class_period = '_3mfro PlM3e _2JVkc _2VHxz' # класс тэга span о периоде з/п

            site_name = WorkSearching.__list_sites[self.__current_site_number][0]

            # класс тэга span, содержащего инф-ю о компании
            # тэг a, содержащего инф. о компании + ссылка содержатся в тэге span (везде индивидуальный)
            span_class_company = '_3mfro _3Fsn4 f-test-text-vacancy-item-company-name _9fXTd _2JVkc _2VHxz _15msI'

            # Информация по кнопке "дальше"
            a_class_button_next = 'icMQ_ bs_sM _3ze9n f-test-button-dalshe f-test-link-Dalshe'    # кнопка дальше

            # Перебор найденных вакансий
            i_page_counter = 0
            i_vacancy_counter = 0
            while True:
                print(f'Обрабатывается {i_page_counter + 1} страница из {self.__page_count}.')

                # Получение списка вакансий
                vacancies = parsed_response.find_all('div', {'class': div_class_item})

                for vacancy in vacancies:

                    dict_vacancy = {}   # Словарь с информацией о вакансии

                    # Наименование вакансии и ссылка на вакансию
                    vacancy_name = vacancy.find('div', {'class': div_class_name})
                    name_info = vacancy_name.find('a')
                    dict_vacancy['Name'] = name_info.text
                    dict_vacancy['Link'] = self.__link_complete(name_info['href'])

                    # З/П
                    salary = vacancy.find('span', {'class': span_class_salary})
                    if (salary is None) or ('По договор' in salary.text):
                        dict_vacancy['Salary'] = 'by agreement'
                        # dict_vacancy['Salary']['Min'] = 'by agreement'
                        # dict_vacancy['Salary']['Max'] = 'by agreement'
                        # dict_vacancy['Salary']['Valuta'] = 'by agreement'
                    else:
                        dict_vacancy['Salary'] = self.__salary_parsing(salary.text)

                    # Информация о компании
                    vacancy_company = vacancy.find('span', {'class': span_class_company})
                    company_info = vacancy_company.find('a') if vacancy_company is not None \
                        else None
                    if company_info is None:
                        dict_vacancy['Company'] = ''
                        dict_vacancy['Company Link'] = ''
                    else:

                        dict_vacancy['Company'] = company_info.text
                        dict_vacancy[
                            'Company Link'] = f"{WorkSearching.__list_sites[self.__current_site_number][1]['Url']}" \
                                              f"{company_info['href']}"

                    # Наименование сайта
                    dict_vacancy['Site'] = site_name

                    self.list_result.append(dict_vacancy)
                    # self.df_adding(i_vacancy_counter, dict_vacancy)

                    i_vacancy_counter = i_vacancy_counter + 1

                # Проверяем количество просмотренных страниц
                i_page_counter = i_page_counter + 1
                if self.__page_count != 'max':
                    if i_page_counter >= self.__page_count:
                        break

                    # Проверяем наличие следующей страницы
                next_button = parsed_response.find('a', {'class': a_class_button_next})
                if next_button is None:
                    break
                parsed_response = self.http_request(next_button["href"])
        return

    def df_adding(self, ind: int, dv: dict) -> None:
        """
        Метод, который добавляет информацию о вакансии в объект DataFrame
        :param ind: порядковый номер записи в DataFrame
        :param dv: словарь с информацией о вакансии
        :return: None
        """

        if isinstance(dv['Salary'], str):
            min_value = dv['Salary']
            max_value = dv['Salary']
            valuta_value = dv['Salary']
        elif len(dv['Salary']) == 2:
            min_value = dv['Salary']['Salary']
            max_value = dv['Salary']['Salary']
            valuta_value = dv['Salary']['Valuta']
        else:
            min_value = dv['Salary']['Min']
            max_value = dv['Salary']['Max']
            valuta_value = dv['Salary']['Valuta']

        self.df_result.loc[ind] = {'Name': dv['Name'], 'Link': dv['Link'], 'Min Salary': min_value,
                                   'Max Salary': max_value, 'Valuta': valuta_value, 'Site name': dv['Site'],
                                   'Company': dv['Company'], 'Company Link': dv['Company Link']}

    @staticmethod
    def save_file(work_path: str) -> str:
        """
        Метод производит запись информации в файл.
        :param work_path: директория, в которой будет сохранен файл
        :return: возвращает полное имя файла
        """
        file_name = f'{work_path}\\{searching_query.site_name}_{searching_query.query}_pages-{searching_query.pages}.json'
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(searching_query.list_result, f, ensure_ascii=False, indent=4)
        return file_name


if __name__ == "__main__":

    while True:
        # Объект класса для поиска списка вакансий
        searching_query = WorkSearching()

        # Выбор сайта для поиска вакансий.
        while True:
            try:
                searching_query.menu()
                var = input("Выберите сайт для поиска (введите номер меню) или 'q' для выхода: ")

                if var == 'q':
                    exit(0)

                searching_query.url = int(var)
                break

            except ValueError as ve:
                print("ERROR! Вы ввели не число!")

            except IncorrectAction as err:
                print(err)

        # Формирование поискового запроса.
        # Количество требуемых страниц.
        try:
            searching_query.query = input("Введите поисковый запрос: ")
            searching_query.pages = input("Введите количество страниц (пустой ввод для макс. кол-ва страниц): ")

        except ValueError as ve:
            print(ve)
            break

        except IncorrectAction as err:
            print(err)
            break

        # отправляем запрос на сервер
        try:
            parsed = searching_query.http_request()

            # вызываем метод для обработки результатов
            searching_query.result_processing(parsed)

        except RequestProblem as rp:
            print(rp)
            break

        except UnknownData as ud:
            print(ud)
            break

        # Обработка полученного результата
        print(f'\nОтобрано {len(searching_query.list_result)} вакансий.\n')
        while True:
            try:
                print("Какие действия произвести с полученным результатом:")
                print("1. Вывести на экран")
                print("2. Сохранить в файл формата 'json'")
                print("3. Сделать новый запрос")
                result_action = int(input("Выберите вариант действия: "))

                if result_action == 1:
                    for i, item in enumerate(searching_query.list_result):
                        searching_query.df_adding(i, item)
                    print()
                    print(tabulate(searching_query.df_result, headers='keys', tablefmt='psql'))
                    print()
                elif result_action == 2:
                    print(f'Информация была сохранена в файл: {WorkSearching.save_file(os.getcwd())}\n')
                elif result_action == 3:
                    print('*' * 20)
                    break
                else:
                    raise ValueError("ERROR! Выбрали несуществующий пункт меню!")
            except ValueError as ve:
                print(ve)
