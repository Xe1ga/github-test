
# -*- coding: utf8 -*-
import os
import sys
import configparser 
import json
import urllib.parse
import re
import multiprocessing
import socket
from urllib.request import Request, urlopen
from urllib.error import URLError
from datetime import datetime, date
from collections import namedtuple

# API_KEY = os.environ.get('API_KEY')
ACCEPT = "application/vnd.github.v3+json"
TIMEOUT = 15
PER_PAGE = 30

def get_params ():
    
     # Ввод url
    flag = True
    while flag:
        sys.stdout.write("Enter url in format 'https://github.com/:owner/:repo': \n")
        url = sys.stdin.readline().strip("\n")
        if re.fullmatch(r'https://github\.com/(\w*)/(\w*)', url):
            flag = False
        else:
            sys.stdout.write("URL is incorrect.\n")

    # Ввод даты начала отчетного периода
    flag = True
    while flag:
        sys.stdout.write("Enter the start date of the reporting period in format 'dd.mm.yyyy': \n")
        begin_date = sys.stdin.readline().strip("\n")
        if begin_date == "":
            flag = False
        elif re.fullmatch(r'\d{2}\.\d{2}\.\d{4}', begin_date):
            flag = False
            begin_date = datetime.strptime(begin_date, "%d.%m.%Y")
            begin_date = begin_date.combine(begin_date.date(), begin_date.min.time()).isoformat()
        else:
            sys.stdout.write("Date is incorrect.\n")
    
    # Ввод даты окончания отчетного периода
    flag = True
    while flag:
        sys.stdout.write("Enter the end date of the reporting period in format 'dd.mm.yyyy': \n")
        end_date = sys.stdin.readline().strip("\n")
        if end_date == "":
            flag = False
        elif re.fullmatch(r'\d{2}\.\d{2}\.\d{4}', end_date):
            end_date = datetime.strptime(end_date, "%d.%m.%Y")
            end_date = end_date.combine(end_date.date(), end_date.max.time()).isoformat()
            if begin_date <= end_date:
                flag = False
            else:
                sys.stdout.write("End date is less than start date.\n")
        else:
            sys.stdout.write("Date is incorrect.\n")

    # Ввод branch
    sys.stdout.write("Enter the name of the branch: \n")
    branch = sys.stdin.readline().strip("\n")
    if branch == '':
        branch = 'master'

    result = {"url": url,
             "begin_date": begin_date,
             "end_date": end_date,
             "branch": branch}
    
    return result

def get_pages_list(since_date, until_date, headers, key_search, url_pull_requests, url_issues, url_commits, state, branch, num_of_pages):
    the_page = []   
    if key_search == 'pulls':
        values = {'state': state, 'base': branch, 'page': str(num_of_pages), 'per_page': str(PER_PAGE)}
        full_url = url_pull_requests + "?" + urllib.parse.urlencode(values)
    elif key_search == 'issues':
        values = {'state': state, 'page': str(num_of_pages), 'per_page': str(PER_PAGE)}
        full_url = url_issues + "?" + urllib.parse.urlencode(values)
    else:
        if since_date and until_date:
            values = {'sha': branch, 'since': since_date, 'until': until_date, 'page': str(num_of_pages), 'per_page': str(PER_PAGE)}
        elif since_date and until_date == None:
            values = {'sha': branch, 'since': since_date, 'page': str(num_of_pages), 'per_page': str(PER_PAGE)}
        elif since_date == None and until_date:
            values = {'sha': branch, 'until': until_date, 'page': str(num_of_pages), 'per_page': str(PER_PAGE)}
        else:
            values = {'sha': branch, 'page': str(num_of_pages), 'per_page': str(PER_PAGE)}

        full_url = url_commits + "?" + urllib.parse.urlencode(values)
    
    # создание объекта-запроса
    req = Request(full_url, None, headers)
    try:
        response = urlopen(req)
    except URLError as e:
        if hasattr(e, 'reason'):
            print('We failed to reach a server.')
            print('Reason: ', e.reason)
        elif hasattr(e, 'code'):
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', e.code)
    else:   
        the_page = response.readline().decode('utf-8')
    if the_page:   
        # Десериализовать экземпляр bytes, содержащий документ JSON, в объект Python
        result_page = json.loads(the_page)
    else:
        result_page = []
    return result_page

def get_pages(args):
    return get_pages_list(*args)

def get_one_page(full_url, headers):
    the_page = []   
    # создание объекта-запроса
    req = Request(full_url, None, headers)
    try:
        response = urlopen(req)
    except URLError as e:
        if hasattr(e, 'reason'):
            print('We failed to reach a server.')
            print('Reason: ', e.reason)
        elif hasattr(e, 'code'):
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', e.code)
    else:   
        the_page = response.readline().decode('utf-8')
    if the_page:   
        # Десериализовать экземпляр bytes, содержащий документ JSON, в объект Python
        result_page = json.loads(the_page)
    else:
        result_page = []
    return result_page

class GitHubStatistics(object):
    def __init__(self, url_repository, since_date, until_date, branch):
        self._URL_BASE = "https://api.github.com"
        self._url_repository = url_repository
        self._part_url = self._get_part_url()
        self._url_commits = self._get_url_commits()
        self._url_pull_requests = self._get_url_pull_requests()
        self._url_issues = self._get_url_issues()
        self._API_KEY = self._get_api_key()
        self._since_date = since_date
        self._until_date = until_date
        self._branch = branch
        self._limit_data = self._get_limit_data()
        self._table_of_active_participants = self._get_table_of_active_participants()
        self._pull_requeststs_open = self._get_pull_requeststs_or_issues("open", False, "pulls")
        self._pull_requeststs_closed = self._get_pull_requeststs_or_issues("closed", False, "pulls")
        self._pull_requeststs_old = self._get_pull_requeststs_or_issues("open", True, "pulls")
        self._issues_open = self._get_pull_requeststs_or_issues("open", False, "issues")
        self._issues_closed = self._get_pull_requeststs_or_issues("closed", False, "issues")
        self._issues_old = self._get_pull_requeststs_or_issues("open", True, "issues")

    def _get_part_url(self):
        u"""
        :type: string
        Возвращает строку :owner/:repo
        """
        return "/".join(self._url_repository.split("/")[-2:])

    def _get_url_commits(self):
        return self._URL_BASE + "/repos/" + self._part_url + "/commits"

    def _get_url_pull_requests(self):
        return self._URL_BASE + "/repos/" + self._part_url + "/pulls"
    
    def _get_url_issues(self):
        return self._URL_BASE + "/repos/" + self._part_url + "/issues"
    
    def _get_api_key(self):
        u"""
        Возвращает API_KEY
        rtype: str
        """

        try:
            config = configparser.RawConfigParser()
            config.read("authentication.ini")
            return  config.get("Parameters", "API_KEY")
            
        except Exception:
            print("Missing file containing API_KEY or problem loading data from authentication.ini file.")
            return ""

    
    def _get_date_from_str(self, date_to_convert):
        u"""
        Возвращает дату в формате "%Y-%m-%d"
        :param date_to_convert: str
        rtype: datetime.datetime
        """
        if date_to_convert:
            return datetime.strptime(date_to_convert[:10], "%Y-%m-%d").date()
        else: 
            return None

    def _get_limit_data(self):

        limit_data = namedtuple("limit_data", "limit remaining reset")
        full_url = self._URL_BASE + "/rate_limit"
        headers = {'Accept': ACCEPT, 'Authorization': "Token {}".format(self._API_KEY)}
        # получаем количество страниц ответа
        speed_limit_data = get_one_page(full_url, headers)
        print("Core limit = " + str(speed_limit_data["resources"]["core"]["limit"]) + "(remaining = " + str(speed_limit_data["resources"]["core"]["remaining"]) + ").")
        print ("Reset: " + str(datetime.fromtimestamp(speed_limit_data["resources"]["core"]["reset"])))
        if speed_limit_data:
            result = limit_data(speed_limit_data["resources"]["core"]["limit"], speed_limit_data["resources"]["core"]["remaining"], speed_limit_data["resources"]["core"]["reset"])
        else:
            result = None
        
        return result
      
    
    def _get_table_of_active_participants(self):
        
        result = []
        commit_list = []
        commit_dict = {}
        if self._since_date and self._until_date:
            values = {'sha': self._branch, 'since': self._since_date, 'until': self._until_date, 'per_page': str(PER_PAGE)}
        elif self._since_date and self._until_date == None:
            values = {'sha': self._branch, 'since': self._since_date, 'per_page': str(PER_PAGE)}
        elif self._since_date == None and self._until_date:
            values = {'sha': self._branch, 'until': self._until_date, 'per_page': str(PER_PAGE)}
        else:
            values = {'sha': self._branch, 'per_page': str(PER_PAGE)}
        full_url = self._url_commits + "?" + urllib.parse.urlencode(values)
        headers = {'Accept': ACCEPT, 'Authorization': "Token {}".format(self._API_KEY)}
        
        # получаем количество страниц ответа
        num_of_pages = self._get_num_of_pages(full_url, headers)
        print(full_url)
        print(num_of_pages)
        if num_of_pages > 0:
            t1 = datetime.now()
            TASKS = [(self._since_date, self._until_date, headers, "", self._url_pull_requests, self._url_issues, self._url_commits, "", self._branch, i) for i in range(1, num_of_pages + 1)]
            pool = multiprocessing.Pool(4)
            # получаем список списков постранично, отдельный элемент - словарь, например [[{issue1},{issue2},...],[{issue31},{issue32},...],...]
            commit_list = pool.map(get_pages, TASKS)
            for page_list in commit_list:
                for commit in page_list:
                    if commit.get("author"):
                        login = commit["author"]["login"]
                        if commit_dict.get(login):
                            commit_dict[login] += 1
                        else: 
                            commit_dict[login] = 1
            for login, commits in commit_dict.items():
                result.append ((login, commits))
            t2 = datetime.now()
            print("Enumeration of pages: " + str(t2 - t1))
            return sorted(result, key=lambda participant: participant[1], reverse = True)   # сортировка
        else:
            return result
        
    def _get_pull_requeststs_or_issues(self, state, old, key_search):
        u"""
        Возвращает количество pull_requests или issues
        :param state: string
        :param old: boolean
        :param key_search: string
        rtype: integer
        """
        result = 0
        result_list = []
        if key_search == 'pulls':
            values = {'state': state, 'base': self._branch, 'per_page': str(PER_PAGE)}
            num_days = 30
            full_url = self._url_pull_requests + "?" + urllib.parse.urlencode(values)
        else:
            values = {'state': state, 'per_page': str(PER_PAGE)}
            num_days = 14
            full_url = self._url_issues + "?" + urllib.parse.urlencode(values)
        
        headers = {'Accept': ACCEPT, 'Authorization': "Token {}".format(self._API_KEY)}
        
        # получаем количество страниц ответа
        num_of_pages = self._get_num_of_pages(full_url, headers)
        print(full_url)
        print(num_of_pages)
        if num_of_pages > 0:
            t1 = datetime.now()
            TASKS = [(self._since_date, self._until_date, headers, key_search, self._url_pull_requests, self._url_issues, self._url_commits, state, self._branch, i) for i in range(1, num_of_pages + 1)]
            pool = multiprocessing.Pool(4)
            # получаем список списков постранично, отдельный элемент - словарь [[{issue1},{issue2},...],[{issue31},{issue32},...],...]
            result_list = pool.map(get_pages, TASKS)
            if old:
                for page_list in result_list:
                    for item_data in page_list:
                        if item_data.get("created_at") and (key_search == 'pulls' or (key_search == 'issues' and not(item_data.get("pull_request")))):
                            if self._since_date and self._until_date:
                                if (self._get_date_from_str(item_data["created_at"]) >= self._get_date_from_str(self._since_date) and self._get_date_from_str(item_data["created_at"]) <= self._get_date_from_str(self._until_date)
                                    and item_data["state"] == "open" and (item_data["closed_at"] == None) and abs(datetime.now().date() - self._get_date_from_str(item_data["created_at"])).days > num_days):
                                    result += 1
                            elif self._since_date and self._until_date == None:
                                if (self._get_date_from_str(item_data["created_at"]) >= self._get_date_from_str(self._since_date)
                                    and item_data["state"] == "open" and (item_data["closed_at"] == None) and abs(datetime.now().date() - self._get_date_from_str(item_data["created_at"])).days > num_days):
                                    result += 1
                            elif self._since_date == None and self._until_date:
                                if (self._get_date_from_str(item_data["created_at"]) <= self._get_date_from_str(self._until_date)
                                    and item_data["state"] == "open" and (item_data["closed_at"] == None) and abs(datetime.now().date() - self._get_date_from_str(item_data["created_at"])).days > num_days):
                                    result += 1
                            else:
                                if (item_data["state"] == "open" and (item_data["closed_at"] == None) and abs(datetime.now().date() - self._get_date_from_str(item_data["created_at"])).days > num_days):
                                    result += 1
            else:
                for page_list in result_list:
                    for item_data in page_list:
                        if item_data.get("created_at") and (key_search == 'pulls' or (key_search == 'issues' and not(item_data.get("pull_request")))):
                            if self._since_date and self._until_date:
                                if self._get_date_from_str(item_data["created_at"]) >= self._get_date_from_str(self._since_date) and self._get_date_from_str(item_data["created_at"]) <= self._get_date_from_str(self._until_date):
                                    result += 1
                            elif self._since_date and self._until_date == None:
                                if self._get_date_from_str(item_data["created_at"]) >= self._get_date_from_str(self._since_date):
                                    result += 1
                            elif self._since_date == None and self._until_date:
                                if self._get_date_from_str(item_data["created_at"]) <= self._get_date_from_str(self._until_date):
                                    result += 1
                            else:
                                result += 1
            t2 = datetime.now()
            print("Enumeration of pages: " + str(t2 - t1))
            return result
        else:
            return result

    def _get_response_data(self, req):
        u"""
        Возвращает содержимое объекта Response
        :param req: :class: Request
        rtype: bytes
        rtype: string
        rtype: integer
        """
        try:
            response = urlopen(req)
        except URLError as e:
            if hasattr(e, 'reason'):
                print('We failed to reach a server.')
                print('Reason: ', e.reason)
            elif hasattr(e, 'code'):
                print('The server couldn\'t fulfill the request.')
                print('Error code: ', e.code)
        else:   
            the_page = response.readline().decode('utf-8')
            header_link = response.headers['Link']
            header_content_length = int(response.headers['Content-Length'])
            # header = response.getheaders()
            return the_page, header_link, header_content_length
    
    def _get_num_of_pages(self, full_url, headers):
        """
        Возвращает количество страниц ответа
        :param full_url: string
        :param headers: dictionary
        :rtype: integer
        """
        #создаем объект запроса
        req = Request(full_url, None, headers)
        #получаем результат - ответ с заголовками
        the_page, header_link, header_content_length = self._get_response_data(req)
        # если поиск с параметрами дал результат
        if header_content_length > 2:
            # если страница одна, то заголовка Link не будет
            if header_link == None:
                return 1
            else:
                links_dict = {}
                links_list = header_link.split(", ")
                for link in links_list:
                    (url, rel) = link.split("; ")
                    url = url[1:-1]
                    rel = rel[5:-1]
                    links_dict[rel] = url
                # пример links_dict = {'next': 'https://api.github.com/repositories/27442967/commits?sha=master&per_page=100&page=2', 'last': 'https://api.github.com/repositories/27442967/commits?sha=master&per_page=100&page=154'}
                last_page = links_dict.get("last").split("page=")[2]
                return int(last_page)
        else:
            return 0
        
    def get_statistics(self):
        u'''
        Печать данных в stdout
        '''
        sys.stdout.write("1. COMMIT STATISTICS\n")
        if self._table_of_active_participants:
            sys.stdout.write('{0:25} | {1:10}'.format("login", "number of commits") + "\n")
            sys.stdout.write("-" * 46 + "\n")
            for participant in self._table_of_active_participants[0:30]:
                sys.stdout.write('{0:25} | {1:10d}'.format(participant[0], participant[1]) + "\n")
                
        else:
            sys.stdout.write("There are no commits in the reporting period.\n")

        sys.stdout.write("2. Number of open pull requests = " + str(self._pull_requeststs_open) + ". Number of closed pull requests = " + str(self._pull_requeststs_closed) + ".\n")
        sys.stdout.write("3. Number of old pull requests = " + str(self._pull_requeststs_old) + ".\n")

        sys.stdout.write("4. Number of open issues = " + str(self._issues_open) + ". Number of closed issues = " + str(self._issues_closed) + ".\n")
        sys.stdout.write("5. Number of old issues = " + str(self._issues_old) + ".\n")

if __name__ == "__main__":

    multiprocessing.freeze_support()
    socket.setdefaulttimeout(TIMEOUT)
    
    time_begin = datetime.now()
    # Ввод параметров stdin
    params = get_params()
    # try:
    # Создание объекта статистики
    # pool = multiprocessing.Pool()
    # result = pool.map(process_item, scientists)
    statistics_obj = GitHubStatistics(params["url"], params["begin_date"] if params["begin_date"] else None, params["end_date"] if params["end_date"] else None, params["branch"] if params["branch"] else "master")
    # Получение статистических данных и их вывод stdout
    statistics_obj.get_statistics()
    # except Exception:
    #     print("No statistics were received. Verify that the parameters and API_KEY are entered correctly.")
    print("Script run time: " + str(datetime.now() - time_begin))

    