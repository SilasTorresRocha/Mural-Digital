FROM python:3.12-slim

WORKDIR /aplicacao

ENV USUARIO_ADMIN=admin
ENV SENHA_ADMIN=ascom123

ENV VERSAO=1.4.3
ENV TESTER=true

ENV LATITUDE=-23.55
ENV LONGITUDE=-51.46

COPY requisitos.txt .

RUN pip install --no-cache-dir -r requisitos.txt

ENV TZ="America/Sao_Paulo"

# Instala o ffmpeg  para tentar dar suporte a videos
RUN apt-get update && apt-get install -y ffmpeg


COPY ./app /aplicacao/app

EXPOSE 8000

CMD ["uvicorn", "app.principal:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
