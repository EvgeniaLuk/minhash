import string
import re
import pymorphy2 as pymorphy2
from elasticsearch import Elasticsearch
import json
import kshingle as ks
import datasketch

# Функция подключения к БД Elasticsearch
def connect_elasticsearch():
    _es = None
    _es = Elasticsearch('http://127.0.0.1:9200')
    if _es.ping():
        print('Connect')
    else:
        print('Not connect!')
    return _es


# Функция удаления пробелов
def remove_whitespace(text):
    return " ".join(text.split())


# Функция удаления знаков припинания
def remove_punctuation(text):
    translator = str.maketrans('', '', string.punctuation)
    return text.translate(translator)


# Функция предствления слова в нормальной форме. Например, думающему - думать
def normalization(text):
    pymorph = pymorphy2.MorphAnalyzer()
    text_norm = ""
    for word in text.split(' '):
        word = pymorph.parse(word)[0].normal_form
        text_norm += word
        text_norm += ' '
    return text_norm


# Функция удаления цифр
def remove_numbers(text):
    result = re.sub(r'\d+', '', text)
    return result


# Функция приведения входных данных к необходимому виду (удаление лишнего и приведения к нормальной форме)
def canonize(source):
    source = source.lower()
    source = remove_punctuation(source)
    source = remove_numbers(source)
    source = remove_whitespace(source)
    source = normalization(source)
    return source


#-----------------------------------Начало скрипта------------------------------------------
# Подключение к БД
es = connect_elasticsearch()
search_content = es.search(index="evgeny", body={"query":{"match_all":{}}}) # Выполняем запрос к БД
# print(search_content)

text_list = []

# Из ранее выполненного запроса к БД достаем текст каждой новости
for text in search_content['hits']['hits']:
    text_json = json.dumps(text, indent=3, ensure_ascii=False)
    text = json.loads(text_json)
    text = text['_source']['TEXT']
    text_str = str(text)
    text_list.append(canonize(text_str))  # добавляем нормализованный элемент в конец списка

# Создание списка с шинглами
# Шинглы - выделенные из статьи подпоследовательности слов
shingles_of_texts = []
for text in text_list:
    shingles_of_texts.append(ks.shingleset_k(text, k=3))

# Оцениваем подобие Жаккара (сходство) между наборами,
# используя маленький и фиксированный объем памяти - datasketch.MinHash
minhash = []
i = 0
for shingles in shingles_of_texts:
    minhash.append(datasketch.MinHash(num_perm=128))
    for shingle in shingles:
        minhash[i].update(shingle.encode('utf-8'))
    i += 1

# Печать коэффициента сходства
# i-столбец
# j-строка
# Перебор всех комбинаций
i = 0
j = 0
while(j <= len(minhash) - 1):
    print(i+1, "-", j+1, "\t\t", minhash[j].jaccard(minhash[i]))    # Берем коэффициент (Жаккара) сходства
    if i == len(minhash) - 1:
        i = 0
        j += 1
        print() # Переход на новую строку, чтобы было красиво
        continue
    i += 1