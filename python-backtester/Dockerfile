# Dockerfile — Python Backtester (CPU; GPU richiede immagine CUDA + CuPy)
# Uso:
#   docker build -t backtester ./python-backtester
#   docker run --rm --env-file python-backtester/.env -v %cd%/data:/data -v %cd%/python-backtester/backtest-results:/app/backtest-results backtester
# Nota GPU: per CuPy/CUDA usare nvidia/cuda:12.x-runtime + pip install cupy-cuda12x
# e lanciare con --gpus all.

FROM python:3.10-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY main.py pytest.ini ./
# trade_profile.py / stoploss_analysis.py inclusi come tool diagnostici
COPY trade_profile.py stoploss_analysis.py ./

CMD ["python", "main.py"]
