import time
from gpiozero import OutputDevice

# Configurações idênticas às da main.py
GPIO_PIN = 18
PULSO_FECHADO = 0.0005  # Pulso para um lado
PULSO_ABERTO = 0.0025   # Pulso para o outro lado

print(f"Iniciando configuração do pino {GPIO_PIN}...")
catraca_pino = OutputDevice(GPIO_PIN)

def mover_servo(tempo_pulso):
    """
    Exatamente a mesma função de bit-banging (pulso manual) da main.py
    Gera 50 ciclos (1 segundo de sinal)
    """
    for _ in range(50): 
        catraca_pino.on()
        time.sleep(tempo_pulso)
        catraca_pino.off()
        time.sleep(0.020 - tempo_pulso)

try:
    print("Testando: Posição FECHADA...")
    mover_servo(PULSO_FECHADO)
    time.sleep(2)  # Pausa 2 segundos
    
    print("Testando: Posição ABERTA...")
    mover_servo(PULSO_ABERTO)
    time.sleep(2)  # Pausa 2 segundos
    
    print("Testando: Voltando para FECHADA...")
    mover_servo(PULSO_FECHADO)
    
    print("Teste concluído com sucesso!")

except KeyboardInterrupt:
    print("\nTeste interrompido pelo usuário.")
finally:
    catraca_pino.close()
    print("Pino liberado.")