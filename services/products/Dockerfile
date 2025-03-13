# Dockerfile para o Microserviço de Produtos
FROM python:3.10-slim

# Define o diretório de trabalho na imagem
WORKDIR /app

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código fonte para o diretório de trabalho
COPY . .

# Informa em qual porta o container estará escutando
EXPOSE 5000

# Comando para iniciar o aplicativo quando o container for executado
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]