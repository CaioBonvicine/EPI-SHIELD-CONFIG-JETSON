# Usa a imagem base oficial da NVIDIA para Jetson Nano (JetPack 4.x / L4T r32.7)
FROM nvcr.io/nvidia/l4t-base:r32.7.1

ENV DEBIAN_FRONTEND=noninteractive

# Instala dependências de sistema, suporte a vídeo (GStreamer/V4L2) e Python
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    python3-opencv \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    v4l-utils \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Atualiza pip e instala as dependências Python essenciais
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

# Instala SDK do Edge Impulse, controle dos Pinos GPIO e clientes de API/MQTT
RUN pip3 install --no-cache-dir \
    edge_impulse_linux \
    Jetson.GPIO \
    requests \
    paho-mqtt

WORKDIR /app

# Copia todo o código do repositório para dentro do container
COPY . /app

# Garante permissão de execução para o arquivo binário do Edge Impulse (.eim)
RUN chmod +x /app/model/model.eim || true

# Comando padrão de execução do script de borda
CMD ["python3", "src/main.py"]