import collections, multiprocessing

def calc(name, item):
    result = 0
    if name in item["name"]:
        result += 1
    return result

def process_item(args):
    return calc (*args)

class Ada(object):
    def __init__(self, scientists, name):
        self.scientists = scientists
        self.name = name

    def begin(self):
        pool = multiprocessing.Pool()
        TASKS = [("Ada", el) for el in self.scientists]
        result = pool.map(process_item, TASKS)
        return result
        


if __name__ == "__main__":
    multiprocessing.freeze_support()
    scientists = [{'name': 'Ada Lovelace', 'born': 1815},
                    {'name': 'Emmy Noether', 'born': 1882},
                    {'name': 'Marie Curie', 'born': 1867},
                    {'name': 'Tu Youyou', 'born': 1930},
                    {'name': 'Ada Yonath', 'born': 1939},
                    {'name': 'Vera Rubin', 'born': 1928},
                    {'name': 'Sally Ride', 'born': 1951}]
    ada = Ada(scientists, "Ada")
    result = ada.begin()
    print (range(1, 11))
    print(sum(result))