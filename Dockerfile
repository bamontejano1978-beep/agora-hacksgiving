FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY agora ./agora
COPY jefe.py trabajador.py testigo.py ./

# APP=jefe | trabajador | testigo
ARG APP=testigo
ENV APP=${APP}

EXPOSE 8080

# 0.0.0.0 dentro del contenedor: Fly enruta desde fuera de la máquina.
CMD ["sh", "-c", "uvicorn ${APP}:app --host 0.0.0.0 --port ${PORT:-8080}"]
