FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
# Instala as dependências e o Gunicorn
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

EXPOSE 8000

# Aqui você troca o "backend.wsgi" pelo nome real da pasta principal do seu Django
CMD ["gunicorn", "lashapp.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]