# Usa a imagem base do L4T (JetPack 4.6 / r32.7.1)
FROM nvcr.io/nvidia/l4t-base:r32.7.1

ENV DEBIAN_FRONTEND=noninteractive

# Instala dependências do sistema e ferramentas de compilação
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    libopencv-dev \
    python3-opencv \
    gcc \
    g++ \
    make \
    git \
    libatlas-base-dev \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Atualiza ferramentas base do Python
RUN pip3 install --upgrade pip setuptools wheel

# Instala o SDK do Edge Impulse direto do repositório Git e demais dependências
RUN pip3 install git+https://github.com/edgeimpulse/edge-impulse-linux-python.git
RUN pip3 install requests Jetson.GPIO

# Copia os arquivos do projeto
COPY modelo_epi.eim /app/
COPY catraca.py /app/

# Garante permissão de execução no binário da IA
RUN chmod +x /app/modelo_epi.eim

CMD ["python3", "catraca.py"]