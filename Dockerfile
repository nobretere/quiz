# Use uma imagem base do Python
FROM python:3.11

# Define o diretório de trabalho no contêiner
WORKDIR /app

# Copia os arquivos do projeto para o contêiner
COPY . /app

# Instala as dependências do projeto
RUN pip install --no-cache-dir -r requirements.txt

# Define a variável de ambiente necessária para o streamlit
ENV STREAMLIT_SERVER_PORT=8501

# Expõe a porta do streamlit
EXPOSE 8501

# Comando para iniciar o aplicativo
CMD ["streamlit", "run", "app.py"]