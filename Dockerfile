FROM python:3.10-slim

# Instala o FFmpeg (Obrigatório para o pydub funcionar)
RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app

# Copia as dependências e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Baixa o pacote do NLTK para dividir frases
RUN python -m nltk.downloader punkt
RUN python -m nltk.downloader punkt_tab

# Copia o resto do código
COPY . .

# Expõe a porta e liga a API
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
