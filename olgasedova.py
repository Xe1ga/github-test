
# -*- coding: utf8 -*-

import configparser 
from urllib.request import Request, urlopen
from urllib.error import URLError
from datetime import datetime

def get_params ():

    config = configparser.RawConfigParser()
    config.read("config.ini")
    url = config.get("Parameters", "url")

    try:
        if config.get("Parameters", "begin_date"):
            begin_date = datetime.strptime(config.get("Parameters", "begin_date"), "%d.%m.%Y").isoformat()
        else:
            begin_date = "01.01.2019"
    except Exception:
        begin_date = "01.01.2019"

    try:
        if config.get("Parameters", "end_date"):
            end_date = datetime.strptime(config.get("Parameters", "end_date"), "%d.%m.%Y").isoformat()
        else:
            end_date = datetime.now().isoformat()
    except Exception:
        end_date = datetime.now().isoformat()
        
    if config.get("Parameters", "branch"):
        branch = config.get("Parameters", "branch")
    else:
        branch = "master"
    
    return [url, begin_date, end_date, branch]

def input_contributors_statistic(table):
    for name, num_commits in table.items():
        print('{0:10} ==> {1:10d}'.format(name, num_commits))

def main():
    u"""
    Главная функция скрипта.
    """
    contributors_statistic = {'Sjoerd': 4127, 'Jack': 4098, 'Dcab': 7678}
    
    input_contributors_statistic(contributors_statistic)

    params = get_params()
    print (params)

    accept = 'application/vnd.github.v3+json'
    # alues = {'name': 'Michael Foord',
    #       'location': 'Northampton',
    #       'language': 'Python' }
    headers = {'Accept': accept}
    req = Request("https://github.com/fastlane/fastlane/graphs/contributors", None, headers)
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
        # everything is fine    
        the_page = response.read()
        print (the_page)
if __name__ == "__main__":
    main()