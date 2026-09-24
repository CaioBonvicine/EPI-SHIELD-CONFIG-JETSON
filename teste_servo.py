from gpiozero import Servo
from time import sleep

# Configura o servo conectado ao GPIO 18 (Pino físico 12)
# Os parâmetros min_pulse_width e max_pulse_width ajustam o range para a maioria dos servos comuns (como o SG90)
servo = Servo(18, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000)

print("Iniciando teste do servo. Pressione Ctrl+C para parar.")

try:
    while True:
        print("Indo para a posição MÍNIMA (-1)")
        servo.min()
        sleep(1)
        
        print("Indo para a posição CENTRAL (0)")
        servo.mid()
        sleep(1)
        
        print("Indo para a posição MÁXIMA (1)")
        servo.max()
        sleep(1)

except KeyboardInterrupt:
    print("\nTeste encerrado pelo usuário.")