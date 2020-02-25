
# -*- coding: utf8 -*-

import ConfigParser
from datetime import datetime

def input_contributors_statistic(table):
    for name, num_commits in table.items():
        print('{0:10} ==> {1:10d}'.format(name, num_commits))

def main():
    u"""
    Главная функция скрипта.
    """
    contributors_statistic = {'Sjoerd': 4127, 'Jack': 4098, 'Dcab': 7678}
    config = ConfigParser.RawConfigParser()
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
        
    
    branch = config.get("Parameters", "branch")
    input_contributors_statistic(contributors_statistic)

    print [url, begin_date, end_date, branch]

if __name__ == "__main__":
    main()