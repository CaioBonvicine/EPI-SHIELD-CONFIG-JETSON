#!/bin/bash

# Interrompe o script caso ocorra algum erro
set -e

echo "=================================================="
echo "   Iniciando Setup do EPI Shield na Jetson Nano   "
echo "=================================================="

# 1. Garante que o usuário atual tenha permissão para usar câmera e pinos GPIO
echo "[1/4] Ajustando permissões de usuário (video/gpio)..."
sudo usermod -aG video,gpio $USER

# 2. Torna o executável do modelo .eim rodável no Linux
if [ -f "model/model.eim" ]; then
    echo "[2/4] Ajustando permissões do modelo .eim..."
    chmod +x model/model.eim
else
    echo "[AVISO] Arquivo model/model.eim não encontrado. Certifique-se de colocá-lo na pasta /model!"
fi

# 3. Constrói a imagem Docker
echo "[3/4] Construindo a imagem Docker (isso pode levar alguns minutos na primeira vez)..."
docker build -t epi-shield-edge:latest .

# 4. Roda o container com acesso total à GPU, Câmera e GPIO
echo "[4/4] Iniciando o container na Jetson Nano..."
docker run -it --rm \
    --runtime nvidia \
    --privileged \
    --network host \
    --device /dev/video0:/dev/video0 \
    -v /dev/bus/usb:/dev/bus/usb \
    -v /sys:/sys \
    epi-shield-edge:latest