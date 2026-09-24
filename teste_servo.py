import RPi.GPIO as GPIO
from time import sleep

# Configuração dos pinos
servo_pin = 18

GPIO.setmode(GPIO.BCM)
GPIO.setup(servo_pin, GPIO.OUT)

# Configura o PWM com 50Hz (frequência padrão para servomotores)
pwm = GPIO.PWM(servo_pin, 50)
pwm.start(0)  # Inicia com duty cycle 0 (sem enviar pulso forçado)

try:
    print("Movendo o servo para 90 graus...")
    
    # Para a maioria dos servos, 90 graus fica em torno de 7.5% de duty cycle
    # (pode variar levemente entre 7.0 e 8.0 dependendo do modelo)
    pwm.ChangeDutyCycle(7.5)
    sleep(1)  # Tempo para o servo alcançar a posição

finally:
    # Para o sinal PWM para evitar que o servo fique "forçando" ou tremendo
    pwm.ChangeDutyCycle(0)
    pwm.stop()
    GPIO.cleanup()
    print("Posição atingida e conexões limpas.")