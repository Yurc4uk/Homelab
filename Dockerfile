# Використовуємо офіційний легкий образ Python
FROM python:3.12-slim

# Встановлюємо робочу директорію всередині контейнера
WORKDIR /app

# Копіюємо файл із залежностями та встановлюємо їх
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь наш код у контейнер
COPY src/ ./src/

# За замовчуванням запускаємо дашборд
CMD ["streamlit", "run", "src/dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
