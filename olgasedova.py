
# -*- coding: utf8 -*-
import os
import sys
import configparser 
import json
import urllib.parse
from urllib.request import Request, urlopen
from urllib.error import URLError
from datetime import datetime
from pprint import pprint

# API_KEY = os.environ.get('API_KEY')
ACCEPT = "application/vnd.github.v3+json"

def get_params ():
    
    # data = sys.stdin.read()
    # print('Content-type: text/plain\n\nGot Data: "%s"' % data)

    result = {}
    config = configparser.RawConfigParser()
    config.read("config.ini")
    url = config.get("Parameters", "url")

    if config.get("Parameters", "begin_date"):
        begin_date = datetime.strptime(config.get("Parameters", "begin_date"), "%d.%m.%Y")
        begin_date = begin_date.combine(begin_date.date(), begin_date.min.time())
    else: 
        begin_date = None
    
    if config.get("Parameters", "end_date"):
        end_date = datetime.strptime(config.get("Parameters", "end_date"), "%d.%m.%Y")
        end_date = end_date.combine(end_date.date(), end_date.max.time())
    else: 
        end_date = None
        
    if config.get("Parameters", "branch"):
        branch = config.get("Parameters", "branch")
    else:
        branch = "master"
    result = {"url": url,
             "begin_date": begin_date,
             "end_date": end_date,
             "branch": branch}
    
    return result

class GitHubStatistics(object):
    def __init__(self, url_repository, since_date, until_date, branch):
        self._URL_BASE = "https://api.github.com"
        self._url_repository = url_repository
        self._part_url = self._get_part_url()
        self._url_commits = self._get_url_commits()
        self._url_pull_requests = self._get_url_pull_requests()
        self._API_KEY = self._get_api_key()
        self._since_date = since_date
        self._until_date = until_date
        self._since_date_isoformat = self._get_date_to_isoformat(since_date)
        self._until_date_isoformat = self._get_date_to_isoformat(until_date)
        self._branch = branch
        self._table_of_active_participants = self._get_table_of_active_participants()
        self._pull_requeststs_open = self._get_pull_requeststs("open")
        self._pull_requeststs_closed = self._get_pull_requeststs("closed")
        self._pull_requeststs_old = self._get_pull_requeststs("open", True)

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
            print ("Missing file containing API_KEY or problem loading data from authentication.ini file.")
            return ""

    def _get_date_to_isoformat(self, date_to_convert):
        u"""
        Возвращает дату в формате iso
        :param date_to_convert: datetime.datetime
        rtype: str
        """
        if date_to_convert:
            return date_to_convert.isoformat()
        else: 
            return ""
    def _get_date_from_isoformat(self, date_to_convert):
        u"""
        Возвращает дату в формате "%Y-%m-%d"
        :param date_to_convert: str
        rtype: datetime.datetime
        """
        if date_to_convert:
            return datetime.fromisoformat(date_to_convert).date()
        else: 
            return None

    def _get_table_of_active_participants(self):
        
        result = []
        commit_list = []
        commit_dict = {}
        if self._since_date and self._until_date:
            values = {'sha': self._branch, 'since': self._since_date_isoformat, 'until': self._until_date_isoformat}
        elif self._since_date and self._until_date == None:
            values = {'sha': self._branch, 'since': self._since_date_isoformat}
        elif self._since_date == None and self._until_date:
            values = {'sha': self._branch, 'until': self._until_date_isoformat}
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
                    values = {'sha': self._branch, 'since': self._since_date_isoformat, 'until': self._until_date_isoformat, 'page': str(page)}
                elif self._since_date and self._until_date == None:
                    values = {'sha': self._branch, 'since': self._since_date_isoformat, 'page': str(page)}
                elif self._since_date == None and self._until_date:
                    values = {'sha': self._branch, 'until': self._until_date_isoformat, 'page': str(page)}
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
        
    def _get_pull_requeststs(self, state="open", old=False):
        
        result = 0
        pull_request_list = []
        pull_request_dict = {}
        
        values = {'state': state, 'base': self._branch, 'since': self._since_date_isoformat, 'until': self._until_date_isoformat}
        full_url = self._url_pull_requests + "?" + urllib.parse.urlencode(values)
        headers = {'Accept': ACCEPT, 'Authorization': "Token {}".format(self._API_KEY)}
        print (full_url)
        # получаем количество страниц ответа
        num_of_pages = self._get_num_of_pages(full_url, headers)
        print (num_of_pages)
        if num_of_pages > 0:
            for page in range(1, num_of_pages + 1):
                values = {'state': state, 'base': self._branch, 'page': str(page)}
                full_url = self._url_pull_requests + "?" + urllib.parse.urlencode(values)
                # создание объекта-запроса
                req = Request(full_url, None, headers)
                the_page, header_link, header_content_length = self._get_response_data(req)
                # Десериализовать экземпляр bytes, содержащий документ JSON, в объект Python
                pull_request_page = json.loads(the_page)
                pull_request_list.extend(pull_request_page)
            
            if old:
                for pull_request in pull_request_list:
                    if pull_request.get("created_at"):
                        if (self._get_date_from_isoformat(pull_request["created_at"]) >= self._since_date.date() and self._get_date_from_isoformat(pull_request["created_at"]) <= self._until_date.date()
                            and pull_request["state"] == "open" and (pull_request["closed_at"] == None) and abs(datetime.now().date() - datetime.strptime(pull_request["created_at"][:10], "%Y-%m-%d")).days > 30):
                            result += 1
                            print (pull_request['id'])
                            print (abs(datetime.now().date() - datetime.strptime(pull_request["created_at"][:10], "%Y-%m-%d")).days)
            else:
                for pull_request in pull_request_list:
                    if pull_request.get("created_at"):
                        if self._get_date_from_isoformat(pull_request["created_at"]) >= self._since_date.date() and self._get_date_from_isoformat(pull_request["created_at"]) <= self._until_date.date():
                            result += 1
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
            the_page = response.read()
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
        
    def get_statistics(self):
        u'''
        Печать данных в stdout
        '''
        print ("1. COMMIT STATISTICS")
        if self._table_of_active_participants:
            print('{0:25} | {1:10}'.format("login", "number of commits"))
            print("-" * 46)
            for participant in self._table_of_active_participants:
                print('{0:25} | {1:10d}'.format(participant[0], participant[1]))
        else:
            print ("There are no commits in the reporting period.")

        print ("2. Number of open pull requests = " + str(self._pull_requeststs_open) + ". Number of closed pull requests = " + str(self._pull_requeststs_closed) + ".")
        print ("3. Number of old pull requests = " + str(self._pull_requeststs_old) + ".")

def main():
    u"""
    Главная функция скрипта.
    """
    print(datetime.now())
    
    params = get_params()
    # try:
    statistics_obj = GitHubStatistics(params["url"], params["begin_date"] if params["begin_date"] else None, params["end_date"] if params["end_date"] else None, params["branch"] if params["branch"] else "master")
    statistics_obj.get_statistics()
    # except Exception:
    #     print ("No statistics were received. Verify that the parameters and API_KEY are entered correctly.")
    
    print(datetime.now())
  
if __name__ == "__main__":
    main()