"""Инструменты для поискового агента МАИ

Этот модуль предоставляет инструменты для поиска информации, связанной с поступлением в МАИ (Московский авиационный институт).

Инструменты включают:
- Поиск по векторной базе знаний
- Получение и подсчёт баллов за индивидуальные достижения
- Доступ к информации о стипендиях, стоимости обучения и адресах филиалов
- Вспомогательный генеративный поиск через YandexGPT

Предназначен для использования в агентной среде, поддерживающей LangChain и LangGraph.
"""

MAX_TOKENS = 2048 * 1
from functools import lru_cache
from typing import Any, Callable, List
import json
import os
import requests

import pandas as pd
from datasets import Dataset
import tqdm

from langchain_core.tools import tool
from react_agent.configuration import Configuration

from qdrant_client import QdrantClient, models
from fastembed import SparseTextEmbedding
from yandex_cloud_ml_sdk import YCloudML

# Qdrant + Embedding SDK
client = QdrantClient(os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])
sdk = YCloudML(folder_id=os.environ["FOLDER_ID"], auth=os.environ["API_KEY"])

dense_query_embedding_model = sdk.models.text_embeddings("query")
dense_doc_embedding_model = sdk.models.text_embeddings("doc")
bm25_embedding_model = SparseTextEmbedding("Qdrant/bm25")

model = sdk.models.completions("yandexgpt", model_version="rc")
# Загрузка данных
with open(os.path.dirname(__file__) + '/data/tuition_fees.json', 'r') as file:
    TUITION = json.load(file)

with open(os.path.dirname(__file__) + '/data/scholarships_info.json', 'r') as file:
    SCHOLARSHIP = json.load(file)

with open(os.path.dirname(__file__) + '/data/passing_scores.json', 'r') as file:
    PASSING_SCORES = json.load(file)

with open(os.path.dirname(__file__) + '/data/filials_info.json', 'r') as file:
    BRANCH = json.load(file)

with open(os.path.dirname(__file__) + '/data/individual_achivements_mapping.json', 'r') as file:
    I_ACHIVEMENTS = json.load(file)

with open(os.path.dirname(__file__) + '/data/tagging_prompt.md', 'r', encoding='utf-8') as f:
    TAGGING_PROMPT = f.read()

# Индексация (если не существует)
if not client.collection_exists("Collection_BVI"):
    df = Dataset.from_pandas(pd.read_csv(os.path.dirname(__file__) + "/data/bvi.csv", header=1, names=["_id","название_олимпиады","профиль_олимпиады","предмет","уровень_олимпиады","направления_подготовки"]))
    
    client.create_collection(
        "Collection_BVI",
        vectors_config={
            "dense": models.VectorParams(
                size=len(dense_doc_embedding_model.run("0").embedding),
                distance=models.Distance.COSINE,
            )
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(
                modifier=models.Modifier.IDF,
            )
        }
    )

    batch_size = 4
    for batch in tqdm.tqdm(df.iter(batch_size=batch_size), 
                        total=len(df) // batch_size):
        dense_embeddings =  [dense_doc_embedding_model.run(doc[:MAX_TOKENS*2]).embedding for doc in batch["chunk_text"]]
        bm25_embeddings = list(bm25_embedding_model.embed(batch["chunk_text"]))

        client.upload_points(
            "Collection_BVI",
            points=[
                models.PointStruct(
                    id=int(batch["_id"][i]),
                    vector={
                        "dense": dense_embeddings[i],
                        "sparse": bm25_embeddings[i].as_object(),
                    },
                    payload={
                        "_id": batch["_id"][i],
                        "название_олимпиады": batch["название_олимпиады"][i],
                        "профиль_олимпиады": batch["профиль_олимпиады"][i],
                        "предмет": batch["предмет"][i],
                        "уровень_олимпиады": batch["уровень_олимпиады"][i],
                        "направления_подготовки": batch["направления_подготовки"][i],
                        "chunk_text": batch["chunk_text"][i],
                    }
                ) for i, _ in enumerate(batch["_id"])
            ],
            batch_size=batch_size,
        )



# Индексация (если не существует)
if not client.collection_exists("Collection_pdf"):
    df = Dataset.from_pandas(pd.read_csv(os.path.dirname(__file__) + "/data/knowledge_data.csv", header=1, names=["_id", "source", "chunk_text", "topics"]))
    client.create_collection(
        "Collection_pdf",
        vectors_config={
            "dense": models.VectorParams(
                size=len(dense_doc_embedding_model.run("0").embedding),
                distance=models.Distance.COSINE,
            )
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(
                modifier=models.Modifier.IDF,
            )
        }
    )

    batch_size = 4
    for batch in tqdm.tqdm(df.iter(batch_size=batch_size), 
                        total=len(df) // batch_size):
        dense_embeddings =  [dense_doc_embedding_model.run(doc[:MAX_TOKENS*2]).embedding for doc in batch["chunk_text"]]
        bm25_embeddings = list(bm25_embedding_model.embed(batch["chunk_text"]))

        client.upload_points(
            "Collection_pdf",
            points=[
                models.PointStruct(
                    id=int(batch["_id"][i]),
                    vector={
                        "dense": dense_embeddings[i],
                        "sparse": bm25_embeddings[i].as_object(),
                    },
                    payload={
                        "_id": batch["_id"][i],
                        "source": batch["source"][i],
                        "topics": batch["topics"][i],
                        "chunk_text": batch["chunk_text"][i],
                    }
                ) for i, _ in enumerate(batch["_id"])
            ],
            batch_size=batch_size,
        )

@lru_cache(maxsize=30)
def tag_query(query):
    return model.run(TAGGING_PROMPT + "\n\n Входной запрос:\n" + query).text

@lru_cache(maxsize=30)
def query_from_collection_with_topics(query: str, collection_name:str, top_k: int = 5) -> str:
    dense_query_vector = dense_query_embedding_model.run(query[:MAX_TOKENS*2]).embedding
    sparse_query_vector = list(bm25_embedding_model.embed([query]))[0]
    query_topics = tag_query(query).split(', ')
    if 'мусор' in query_topics:
        query_topics.remove("мусор")
    query_topics = set(query_topics)

    prefetch = [
        models.Prefetch(query=dense_query_vector, using="dense", limit=6*top_k,),
        models.Prefetch(query=models.SparseVector(**sparse_query_vector.as_object()), using="sparse", limit=6*top_k,),
    ]
    results = []
    resp = client.query_points(
        collection_name,
        prefetch=prefetch,
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        with_payload=True,
        limit=7*top_k,
    )
    treshold = sum([p.score for p in resp.points]) / len(resp.points)
    for point in resp.points:
        if 'chat' in point.payload['source']:
            date = point.payload['source'].split('_')[0].replace('chat', '')
        else:
            date = {
                'Онлайн_магистратура_«Машинное_обучение_и_анализ_данных»': 2024,
                'Особые_условия_для_поступления_в_Институт_№8_МАИ': '2024-2026',
                'Постановление Правительства РФ от 27.04.2024 N 555 — Редакция от 07.04.2025 — Контур.Норматив': '2025-2026',
                'Правила приема МАИ': '2025-2026',
                'Правила Приема(Министерские)': '2024 - 2026',
                'Федеральный закон от 29 декабря 2012 г. N 273-ФЗ _Об образовании в Российской Фе ... _ Система ГАРАНТ': '2012 - 2025'
            }.get(point.payload['source'], '2025-2026')
        if set(point.payload['topics']).intersection(query_topics) or point.score > treshold:
            results.append(f"Актуально в период: {date}\n\n{point.payload['chunk_text']}")
    results = results[:top_k]
    return "\n".join([("=" * 20) + f"\n# Источник номер {i + 1}\n" + r for i, r in enumerate(results)])

@lru_cache(maxsize=30)
def query_from_collection(query: str, collection_name:str, top_k: int = 3) -> str:
    dense_query_vector = dense_query_embedding_model.run(query[:MAX_TOKENS*2]).embedding
    sparse_query_vector = list(bm25_embedding_model.embed([query]))[0]
    prefetch = [
        models.Prefetch(query=dense_query_vector, using="dense", limit=3*top_k,),
        models.Prefetch(query=models.SparseVector(**sparse_query_vector.as_object()), using="sparse", limit=3*top_k,),
    ]
    results = []
    resp = client.query_points(
        collection_name,
        prefetch=prefetch,
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        with_payload=True,
        limit=top_k,
    )
    for point in resp.points:
            results.append(f"{point.payload['chunk_text']}")
    return "\n".join([("=" * 20) + f"\n# Источник номер {i + 1}\n" + r for i, r in enumerate(results)])



@tool
def search_on_mai_knowledge_base(query: str) -> str:
    """
    Поиск по базе знаний МАИ. Содержит много полезного материала для студентов и преподавателей.
    Стоит упоминать в query тематические темы, которые вас интересуют, а также подробный запрос

    Аргументы:
        query (str): Пользовательский запрос на русском языке.

    Возвращает:
        str: До 10 релевантных фрагментов текста из базы знаний с указанием периода актуальности.
    """
    return query_from_collection_with_topics(query, "Collection_pdf")

@tool
def search_on_bvi_table(query: str) -> str:
    """
    Поиск по таблице БВИ для поступления без вступительных испытаний в МАИ. Содержит много полезного материала об олимпиадах, по которым можно поступить без ЕГЭ.
    Стоит упоминать 

    Аргументы:
        query (str): Пользовательский запрос на русском языке.

    Возвращает:
        str: До 10 релевантных фрагментов текста из базы знаний с указанием периода актуальности.
    """
    return query_from_collection(query, "Collection_BVI")
    
    
@tool
@lru_cache(maxsize=30)
def get_individual_achivements() -> str:
    """
    Получить список всех индивидуальных достижений и их баллов.

    Возвращает:
        str: JSON с полным перечнем достижений и количеством баллов за каждое.
    """
    return f"JSON с информацией об индивидуальных достижениях \n {I_ACHIVEMENTS}"
@tool
@lru_cache(maxsize=30)
def count_individual_achivements(achivements_list: list) -> str:
    """
    Подсчёт суммы баллов за указанные индивидуальные достижения.

    Аргументы:
        achivements_list (list[str]): Список названий достижений (ключей из JSON).

    Возвращает:
        str: Сумма баллов за достижения.
    """
    total = 0
    for achievement in achivements_list:
        total += I_ACHIVEMENTS.get(achievement, 0)
    return f"Сумма индивидуальных достижений пользователя: \n {total % 10}"
@tool
@lru_cache(maxsize=30)
def get_branch_addresses() -> str:
    """
    Получить список филиалов МАИ и адресов общежитий.

    Возвращает:
        str: JSON с информацией о размещении.
    """
    return f"JSON с информацией об адресах филлиалов \n {BRANCH}"
@tool
@lru_cache(maxsize=30)
def get_passing_scores() -> str:
    """
    Получить проходные баллы по направлениям подготовки в 2024 году.

    Возвращает:
        str: JSON с проходными баллами.
    """
    return f"JSON с информацией о проходных баллах \n {PASSING_SCORES}"

@tool
def calculate_total_scholarship(scholarship_names: list[str]) -> str:
    """
    Подсчитать общую сумму стипендий по их названиям.

    Аргументы:
        scholarship_names (list[str]): Названия стипендий.

    Возвращает:
        str: Общая сумма стипендий или список ненайденных.
    """
    total = 0
    missing = []
    for name in scholarship_names:
        if name in SCHOLARSHIP:
            total += SCHOLARSHIP[name]
        else:
            missing.append(name)
    if missing:
        return f"Ошибка: следующие стипендии не найдены - {', '.join(missing)}"
    return f"Общая сумма стипендий: {total} руб."
@tool
@lru_cache(maxsize=30)
def get_scholarship_amounts() -> str:
    """
    Получить перечень стипендий и их размеры.

    Возвращает:
        str: JSON с информацией о стипендиях.
    """
    return f"JSON с размерами стипендий: \n {SCHOLARSHIP}"
@tool
@lru_cache(maxsize=30)
def calculate_tuition_by_program(program_code: str, duration: int = 1) -> str:
    """
    Рассчитать стоимость обучения по коду направления за выбранное количество лет.

    Аргументы:
        program_code (str): Код программы (например, "09.03.01").
        duration (int): Количество лет обучения.

    Возвращает:
        str: Текст с расчётом стоимости или ошибкой.
    """
    for campus_name, campus_data in TUITION.items():
        for level_name, level_data in campus_data.items():
            if program_code in level_data:
                program_info = level_data[program_code]
                if isinstance(program_info["Очная"], int):
                    if level_name in ["Базовое высшее (4 года)", "Бакалавриат"]:
                        yearly_cost = program_info["Очная"] / 4
                    else:
                        yearly_cost = program_info["Очная"] / 5.5
                    total_cost = yearly_cost * duration
                    return (
                        f"Стоимость обучения по программе '{program_info['Наименование']}' ({program_code}):\n"
                        f"• За 1 год: {yearly_cost} руб.\n"
                        f"• За {duration} года(лет): {total_cost} руб.\n"
                        f"Филиал: {campus_name.split('(')[0].strip()}\n"
                        f"Уровень образования: {level_name}"
                    )
                else:
                    return f"Ошибка: стоимость обучения для программы {program_code} не указана (уточняется)"
    return f"Ошибка: программа с кодом {program_code} не найдена"
@tool
@lru_cache(maxsize=30)
def get_tuition_info() -> str:
    """
    Получить полную информацию о стоимости обучения по институтам.

    Возвращает:
        str: JSON с ценами на обучение.
    """
    return f"JSON с данными о стоимости обучения: \n {TUITION}"

@tool
@lru_cache(maxsize=30)
def yandex_generative_search(question: str) -> str:
    """
    Выполнить генеративный поиск ответа на вопрос через YandexGPT (по сайтам МАИ).

    Аргументы:
        question (str): Вопрос на русском языке.

    Возвращает:
        str: Сгенерированный ответ или сообщение об ошибке.
    """
    api_key = os.environ["API_KEY"]
    folder_id = os.environ["FOLDER_ID"]
    IAM_TOKEN = os.environ["IAM_TOKEN"]

    url = "https://searchapi.api.cloud.yandex.net/v2/gen/search"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {IAM_TOKEN}" if IAM_TOKEN else f"Api-Key {api_key}"
    }
    payload = {
        "site": {"site": ["https://mai.ru", "https://priem.mai.ru", 'https://tabiturient.ru/vuzu/mai/proxodnoi/', 'https://www.ucheba.ru/']},
        "messages": [{"role": "ROLE_USER", "content": question}],
        "folder_id": folder_id
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = ''
        for ind, record in enumerate(response.json()):
            result += f'Результат поиска номер {ind + 1}' + record['message']['content'] + '\n\n'
        return result
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return "Ошибка запроса к YandexGPT"
    except KeyError:
        print("Error parsing response")
        return "Ошибка обработки ответа от YandexGPT"

# Список всех инструментов
TOOLS: List[Callable[..., Any]] = [
    get_individual_achivements, count_individual_achivements, get_branch_addresses,
    get_scholarship_amounts, calculate_total_scholarship,
    get_tuition_info, calculate_tuition_by_program,
    search_on_mai_knowledge_base,
    search_on_bvi_table,
    yandex_generative_search
]
