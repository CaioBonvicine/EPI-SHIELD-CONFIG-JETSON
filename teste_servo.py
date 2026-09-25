import time
import os
from gpiozero import OutputDevice

GPIO_PIN = 18
PULSO_FECHADO = 0.0005  
PULSO_ABERTO = 0.0025   
CATRACA_FILE = "estado_catraca.txt"

catraca_pino = OutputDevice(GPIO_PIN)

def mover_servo(tempo_pulso):
    for _ in range(50): 
        catraca_pino.on()
        time.sleep(tempo_pulso)
        catraca_pino.off()
        time.sleep(0.020 - tempo_pulso)

print("Serviço do Servo iniciado. Aguardando comandos...")
mover_servo(PULSO_FECHADO) # Inicia fechado

try:
    while True:
        if os.path.exists(CATRACA_FILE):
            with open(CATRACA_FILE, "r") as f:
                comando = f.read().strip()
            
            if comando == "ABRIR":
                print("Sinal recebido: ABRINDO CATRACA...")
                mover_servo(PULSO_ABERTO)
                # Apaga o comando para não repetir
                os.remove(CATRACA_FILE)
                
                # Mantém aberto pelo tempo necessário
                time.sleep(3.0)
                
                print("FECHANDO CATRACA...")
                mover_servo(PULSO_FECHADO)
        
        time.sleep(0.1)
except KeyboardInterrupt:
    catraca_pino.close()