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


import requests
from functools import lru_cache
from typing import Any, Dict, List
from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv(override=True)

# Decorator @tool assumed to be provided by the agent framework
from langchain.tools import tool

from dotenv import load_dotenv



load_dotenv(override=True)

@tool
@lru_cache(maxsize=30)
def code_rag(question: str) -> str:
    """
    Запрашивает у RAG-базы кодовые фрагменты, связанные с вопросом.

    Args:
        question (str): Текстовый запрос , описывающий, какой код и описание нужны.

    Returns:
        str: описание и код из репозиториия, который соответствует запросу

    Raises:
        requests.HTTPError: В случае неуспешного HTTP-статуса.
    """
    url = "https://example.com/api/code_rag"
    payload = {"question": question}
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    return response.text

from functools import lru_cache
import requests

@lru_cache(maxsize=30)
def graph_rag(question: str, repo: str = "default-repo") -> str:
    """
    Запрашивает у графовой RAG-системы информацию о структурах и связях, 
    упомянутых в пользовательском запросе. Вопрос должен содержать указания
    на названия **файлов, функций, классов, переменных или связей между ними** 
    в рамках указанного репозитория кода.

    Args:
        question (str): Естественно-языковой запрос, описывающий интересующие сущности или связи в коде. Пример: "Какие функции вызывают foo() в file.cpp?"
        repo (str): Название репозитория, по которому нужно сделать поиск. Должно быть валидным.

    Returns:
        str: Ответ от backend-сервиса, содержащий описание структуры, связей или элементов кода.

    Raises:
        requests.HTTPError: Если сервер вернул ошибку HTTP при выполнении запроса.
        ValueError: Если входные параметры отсутствуют или некорректны.
    """
    if not question:
        raise ValueError("Параметр 'question' не должен быть пустым.")
    if not repo:
        raise ValueError("Параметр 'repo' обязателен.")

    url = f"http://localhost:5000/chat"  # Используем переменную BACKEND_URL из .env
    headers = {
        "Authorization": f"{os.getenv('SECRET_TOKEN')}",  # SECRET_TOKEN
        "Content-Type": "application/json"
    }
    payload = {
        "repo": repo,
        "msg": question
    }

    response = requests.post(url, json=payload, headers=headers, timeout=1000)
    response.raise_for_status()

    data = response.json()
    if "response" not in data:
        raise ValueError(f"Некорректный ответ от сервиса: {data}")

    return data["response"]





# Список всех инструментов
TOOLS: List[Callable[..., Any]] = [
graph_rag
]
