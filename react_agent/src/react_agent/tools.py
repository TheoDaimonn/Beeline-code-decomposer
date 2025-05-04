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

@tool
@lru_cache(maxsize=30)
def graph_rag(question: str) -> str:
    """
    Запрашивает у графовой RAG-базы структуру и связи для заданного запроса.

    Args:
        question (str): Запрос пользователя, описывающий, какую структуру или связи он ищет.

    Returns:
        str: Структурированные данные, возвращённые сервисом.

    Raises:
        requests.HTTPError: В случае неуспешного HTTP-статуса.
    """
    url = "https://example.com/api/graph_rag"
    payload = {"question": question}
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    return response.text




# Список всех инструментов
TOOLS: List[Callable[..., Any]] = [

]
