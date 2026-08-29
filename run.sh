#!/bin/bash
set -e

echo "Construindo a imagem Docker..."
sudo docker build -t agente-epi .

echo "Iniciando o container..."

# Desligamos o 'set -e' temporariamente para o script não abortar imediatamente se o Docker falhar
set +e

sudo docker run -it --rm \
    --runtime nvidia \
    --privileged \
    --network host \
    --ipc=host \
    -v /dev/video0:/dev/video0 \
    -v /sys:/sys \
    -v /dev:/dev \
    agente-epi

# Captura o código de erro do comando anterior (o docker run)
EXIT_CODE=$?

# Ligamos de volta a proteção do bash
set -e

# Verifica se o código de saída é diferente de zero (zero significa sucesso no Linux)
if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "======================================================================"
    echo "❌ ERRO DETECTADO: O container falhou e retornou o código: $EXIT_CODE"
    echo "======================================================================"
    echo "Dicas para investigar:"
    echo " 1. Role o terminal para cima e leia a mensagem de erro do Python (Traceback)."
    echo " 2. Verifique se a câmera está conectada executando: ls -l /dev/video0"
    echo " 3. A API no endereço $API_URL está rodando e acessível?"
    echo "======================================================================"
    
    # Sai do script retornando o mesmo erro do Docker, útil se você for rodar isso via sistema (systemd/cron)
    exit $EXIT_CODE
else
    echo ""
    echo "✅ Container executado e finalizado normalmente!"
fi