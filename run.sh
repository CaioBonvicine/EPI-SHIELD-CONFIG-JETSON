#!/bin/bash
echo "Construindo a imagem Docker..."
sudo docker build -t agente-epi .

echo "Iniciando o container..."
# --privileged: necessário para acessar o /sys/class/gpio do servo motor
# -v /dev/video0:/dev/video0: passa a câmera USB para dentro do container
sudo docker run \
    --runtime nvidia \
    --privileged \
    -v /dev/video0:/dev/video0 \
    --network host \
    agente-epi
echo "Exit code: $?"