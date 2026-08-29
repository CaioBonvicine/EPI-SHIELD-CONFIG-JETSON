# Usa a imagem base do L4T (JetPack 4.6 / r32.7.1)
FROM nvcr.io/nvidia/l4t-base:r32.7.1

ENV DEBIAN_FRONTEND=noninteractive
ENV GIT_TERMINAL_PROMPT=0
ENV OPENBLAS_CORETYPE=ARMV8

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    libopencv-dev \
    python3-opencv \
    gcc \
    g++ \
    make \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Atualiza ferramentas base do Python
RUN pip3 install --upgrade pip setuptools wheel

# Instala o SDK do Edge Impulse e bibliotecas do projeto
RUN pip3 install edge_impulse_linux requests Jetson.GPIO

# CORRIGIDO: Copia o modelo novo para o container
COPY modelo_epiV2.eim /app/
COPY catraca.py /app/

# CORRIGIDO: Concede permissão de execução no novo modelo
RUN chmod +x /app/modelo_epiV2.eim

CMD ["python3", "-u", "catraca.py"]