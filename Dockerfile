# Usa a imagem base do L4T (JetPack 4.6 / r32.7.1)
FROM nvcr.io/nvidia/l4t-base:r32.7.1

ENV DEBIAN_FRONTEND=noninteractive
# Impede que o Git trave esperando autenticação em ambiente não interativo
ENV GIT_TERMINAL_PROMPT=0

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

# Clona o SDK do Edge Impulse diretamente e faz a instalação local
RUN pip3 install edge_impulse_linux

# Instala requisições HTTP e controle de GPIO da Jetson
RUN pip3 install requests Jetson.GPIO

# Copia os arquivos da aplicação
COPY modelo_epi.eim /app/
COPY catraca.py /app/

# Garante permissão de execução no binário da IA
RUN chmod +x /app/modelo_epi.eim

CMD ["python3", "-u", "catraca.py"]