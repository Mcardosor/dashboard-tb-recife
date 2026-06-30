FROM python:3.11-slim

WORKDIR /app

# Instala dependências de sistema necessárias para folium/branca
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python primeiro (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código-fonte
COPY app.py .
COPY src/ src/
COPY .streamlit/ .streamlit/

# Os parquets são montados via volume em produção
# (não copiados na imagem para manter a imagem leve)

EXPOSE 8501

CMD ["python", "-m", "streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]

# ── Comando de deploy na VM ────────────────────────────────────────────────────
# docker run -d --name dashboard-tb-recife -p 8503:8501 #   -v /home/matheusrodrigues/dashboard-tb-recife/dados_dashboard:/app/dados_dashboard #   dashboard-tb-recife #   python -m streamlit run app.py #   --server.port=8501 --server.address=0.0.0.0 #   --server.baseUrlPath=cenarios/tbrecife --server.headless=true
