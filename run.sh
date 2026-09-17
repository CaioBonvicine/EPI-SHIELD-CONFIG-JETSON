#!/bin/bash
set -e

IMAGE="agente-epi"

echo "=========================================="
echo " Verificando imagem Docker..."
echo "=========================================="

if sudo docker image inspect "$IMAGE" > /dev/null 2>&1; then
    echo "✅ Imagem '$IMAGE' já existe localmente."
    echo "✅ Não será necessário reconstruí-la."
else
    echo "⚠️ Imagem '$IMAGE' não encontrada."
    echo "Construindo a imagem Docker..."
    
    sudo docker build -t "$IMAGE" .
    
    echo "✅ Imagem construída com sucesso."
fi

echo ""
echo "=========================================="
echo " Iniciando container..."
echo "=========================================="

set +e

sudo docker run -it --rm \
    --runtime nvidia \
    --privileged \
    --network host \
    --ipc=host \
    -v /dev/video0:/dev/video0 \
    -v /sys:/sys \
    -v /dev:/dev \
    "$IMAGE"

EXIT_CODE=$?

set -e

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "======================================================================"
    echo "❌ ERRO DETECTADO: O container falhou e retornou o código: $EXIT_CODE"
    echo "======================================================================"
    echo "Dicas para investigar:"
    echo " 1. Role o terminal para cima e leia a mensagem de erro do Python."
    echo " 2. Verifique se a câmera está conectada:"
    echo "       ls -l /dev/video0"
    echo " 3. Verifique se a imagem Docker existe:"
    echo "       sudo docker images"
    echo "======================================================================"
    exit $EXIT_CODE
else
    echo ""
    echo "✅ Container executado e finalizado normalmente!"
fi