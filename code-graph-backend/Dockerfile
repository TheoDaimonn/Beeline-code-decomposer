# Этап 1: Базовый образ с Python
FROM python:3.12 as base

# Установка системных переменных
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Указываем Flask приложение (предполагается, что экземпляр Flask app создан в /api/api/index.py)
# Если путь другой, исправьте здесь. Используется формат модуля Python.
ENV FLASK_APP=api.index
# Включаем режим отладки Flask (для разработки)
ENV FLASK_DEBUG=1

# Устанавливаем рабочую директорию
WORKDIR /api

# Устанавливаем системные зависимости, необходимые для сборки некоторых пакетов Python
# build-essential содержит gcc, make и т.д.
# git может потребоваться для tree-sitter-languages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git && \
    # Очищаем кэш apt для уменьшения размера образа
    rm -rf /var/lib/apt/lists/*

# Обновляем pip до последней версии
RUN pip install --no-cache-dir --upgrade pip

# Копируем только файл зависимостей для использования кэша Docker
COPY requirements.txt ./

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код приложения
COPY . .

# Указываем порт, на котором будет работать приложение
EXPOSE 5000

# Команда для запуска Flask приложения
# --host=0.0.0.0 делает приложение доступным снаружи контейнера
# --port=5000 явно указывает порт (хотя Flask по умолчанию использует 5000)
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
