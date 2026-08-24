# Usa a imagem base do L4T (verifique a versão exata do JetPack da sua Nano, a r32.7.1 é comum para a Jetson Nano padrão)
FROM nvcr.io/nvidia/l4t-base:r32.7.1

# Evita prompts interativos durante a instalação
ENV DEBIAN_FRONTEND=noninteractive

# Instala dependências do sistema e do Edge Impulse
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    libopencv-dev \
    python3-opencv \
    gcc \
    make \
    git \
    && rm -rf /var/lib/apt/lists/*

# Instala bibliotecas Python necessárias (Edge Impulse, Requests para a API, Jetson.GPIO para o servo)
RUN pip3 install --upgrade pip
RUN pip3 install edgeimpulse-linux requests Jetson.GPIO

# Cria o diretório de trabalho
WORKDIR /app

# Copia o modelo da IA, seu script principal e dependências para dentro do container
COPY modelo_epi.eim /app/
COPY catraca.py /app/

# Garante que o modelo do Edge Impulse tenha permissão de execução
RUN chmod +x /app/modelo_epi.eim

# Comando de execução
CMD ["python3", "catraca.py"]