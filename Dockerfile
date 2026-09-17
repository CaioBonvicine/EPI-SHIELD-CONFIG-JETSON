# Usa a imagem base do L4T compatível com JetPack 4.6.x / r32.7.1
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
    libatlas-base-dev \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    gcc \
    g++ \
    make \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala o SDK do Edge Impulse e o controle de GPIO da Jetson
RUN pip3 install --no-cache-dir edge_impulse_linux Jetson.GPIO

# Copia os arquivos da aplicação
COPY modelo_epiV2.eim /app/
COPY catraca.py /app/

# Concede permissão de execução ao modelo
RUN chmod +x /app/modelo_epiV2.eim

# Executa a aplicação
CMD ["python3", "-u", "catraca.py"]