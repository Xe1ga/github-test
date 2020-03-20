
# -*- coding: utf8 -*-
import os
import sys
import configparser 
import json
import urllib.parse
import re
import multiprocessing
from urllib.request import Request, urlopen
from urllib.error import URLError
from datetime import datetime, date
from pprint import pprint

# API_KEY = os.environ.get('API_KEY')
ACCEPT = "application/vnd.github.v3+json"
URL_BASE = "https://api.github.com"

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
        
def get_part_url(url_repository):
    u"""
    :type: string
    Возвращает строку :owner/:repo
    """
    return "/".join(url_repository.split("/")[-2:])

def get_url_commits(part_url):
    return URL_BASE + "/repos/" + part_url + "/commits"

def get_url_pull_requests(part_url):
    return URL_BASE + "/repos/" + part_url + "/pulls"

def get_url_issues(self):
    return URL_BASE + "/repos/" + part_url + "/issues"

def get_api_key():
    u"""
    Возвращает API_KEY
    rtype: str
    """
    try:
        config = configparser.RawConfigParser()
        config.read("authentication.ini")
        return  config.get("Parameters", "API_KEY")
        
    except Exception:
        print ("Missing file containing API_KEY or problem loading data from authentication.ini file.")
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


def _get_table_of_active_participants(self):
    
    result = []
    commit_list = []
    commit_dict = {}
    if self._since_date and self._until_date:
        values = {'sha': self._branch, 'since': self._since_date, 'until': self._until_date}
    elif self._since_date and self._until_date == None:
        values = {'sha': self._branch, 'since': self._since_date}
    elif self._since_date == None and self._until_date:
        values = {'sha': self._branch, 'until': self._until_date}
    else:
        values = {'sha': self._branch}
    full_url = self._url_commits + "?" + urllib.parse.urlencode(values)
    headers = {'Accept': ACCEPT, 'Authorization': "Token {}".format(self._API_KEY)}
    print (full_url)
    # получаем количество страниц ответа
    num_of_pages = self._get_num_of_pages(full_url, headers)
    print (num_of_pages)
    if num_of_pages > 0:
        for page in range(1, num_of_pages + 1):
            
            if self._since_date and self._until_date:
                values = {'sha': self._branch, 'since': self._since_date, 'until': self._until_date, 'page': str(page)}
            elif self._since_date and self._until_date == None:
                values = {'sha': self._branch, 'since': self._since_date, 'page': str(page)}
            elif self._since_date == None and self._until_date:
                values = {'sha': self._branch, 'until': self._until_date, 'page': str(page)}
            else:
                values = {'sha': self._branch, 'page': str(page)}

            full_url = self._url_commits + "?" + urllib.parse.urlencode(values)
            # создание объекта-запроса
            req = Request(full_url, None, headers)
            the_page, header_link, header_content_length = self._get_response_data(req)
            # Десериализовать экземпляр bytes, содержащий документ JSON, в объект Python
            commit_page = json.loads(the_page)
            commit_list.extend(commit_page)
        for commit in commit_list:
            if commit.get("author"):
                login = commit["author"]["login"]
                if commit_dict.get(login):
                    commit_dict[login] += 1
                else: 
                    commit_dict[login] = 1
        for login, commits in commit_dict.items():
            result.append ((login, commits))
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
        values = {'state': state, 'base': self._branch}
        num_days = 30
        full_url = self._url_pull_requests + "?" + urllib.parse.urlencode(values)
    else:
        values = {'state': state}
        num_days = 14
        full_url = self._url_issues + "?" + urllib.parse.urlencode(values)
    
    headers = {'Accept': ACCEPT, 'Authorization': "Token {}".format(self._API_KEY)}
    print (full_url)
    # получаем количество страниц ответа
    num_of_pages = self._get_num_of_pages(full_url, headers)
    print (num_of_pages)
    
    if num_of_pages > 0:
        t1 = datetime.now()
        for page in range(1, num_of_pages + 1):
            if key_search == 'pulls':
                values = {'state': state, 'base': self._branch, 'page': str(page)}
                full_url = self._url_pull_requests + "?" + urllib.parse.urlencode(values)
            else:
                values = {'state': state, 'page': str(page)}
                full_url = self._url_issues + "?" + urllib.parse.urlencode(values)
            
            # создание объекта-запроса
            req = Request(full_url, None, headers)
            the_page, header_link, header_content_length = self._get_response_data(req)
            # Десериализовать экземпляр bytes, содержащий документ JSON, в объект Python
            result_page = json.loads(the_page)
            result_list.extend(result_page)
        t2 = datetime.now()
        print("Enumeration of pages: " + str(t2 - t1))
        
        if old:
            for item_data in result_list:
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
            for item_data in result_list:
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
        t3 = datetime.now()
        print("Enumeration of pages: " + str(t3 - t2))
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
        the_page = response.readline()
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
            last_page = links_dict.get("last").split("page=")[1]
            return int(last_page)
    else:
        return 0

def print_statistics(table_of_active_participants, pull_requeststs_open, pull_requeststs_closed, pull_requeststs_old, issues_open, issues_closed, issues_old):
    u'''
    Печать данных в stdout
    '''
    sys.stdout.write("1. COMMIT STATISTICS\n")
    if table_of_active_participants:
        sys.stdout.write('{0:25} | {1:10}'.format("login", "number of commits") + "\n")
        sys.stdout.write("-" * 46 + "\n")
        for participant in table_of_active_participants:
            sys.stdout.write('{0:25} | {1:10d}'.format(participant[0], participant[1]) + "\n")
    else:
        sys.stdout.write("There are no commits in the reporting period.\n")

    sys.stdout.write("2. Number of open pull requests = " + str(pull_requeststs_open) + ". Number of closed pull requests = " + str(pull_requeststs_closed) + ".\n")
    sys.stdout.write("3. Number of old pull requests = " + str(pull_requeststs_old) + ".\n")

    sys.stdout.write("4. Number of open issues = " + str(issues_open) + ". Number of closed issues = " + str(issues_closed) + ".\n")
    sys.stdout.write("5. Number of old issues = " + str(issues_old) + ".\n")
  
  
if __name__ == "__main__":
    
    multiprocessing.freeze_support()
    time_begin = datetime.now()
    # Ввод параметров stdin
    params = get_params()
    # try:
    # Создание объекта статистики
    # pool = multiprocessing.Pool()
    # result = pool.map(process_item, scientists)
    url_repository = params["url"]
    part_url = get_part_url(url_repository)
    url_commits = get_url_commits(part_url)
    url_pull_requests = get_url_pull_requests(part_url)
    url_issues = get_url_issues(part_url)
    API_KEY = get_api_key()
    since_date = params["begin_date"] if params["begin_date"] else None
    until_date = params["end_date"] if params["end_date"] else None
    branch = params["branch"] if params["branch"] else "master"
    table_of_active_participants = self._get_table_of_active_participants()
    self._pull_requeststs_open = self._get_pull_requeststs_or_issues("open", False, "pulls")
    self._pull_requeststs_closed = self._get_pull_requeststs_or_issues("closed", False, "pulls")
    self._pull_requeststs_old = self._get_pull_requeststs_or_issues("open", True, "pulls")
    self._issues_open = self._get_pull_requeststs_or_issues("open", False, "issues")
    self._issues_closed = self._get_pull_requeststs_or_issues("closed", False, "issues")
    self._issues_old = self._get_pull_requeststs_or_issues("open", True, "issues")

    # Вывод статистических данных в stdout
    print_statistics(table_of_active_participants, pull_requeststs_open, pull_requeststs_closed, pull_requeststs_old, issues_open, issues_closed, issues_old)
    # except Exception:
    #     print ("No statistics were received. Verify that the parameters and API_KEY are entered correctly.")
    print("Script run time: " + str(datetime.now() - time_begin))