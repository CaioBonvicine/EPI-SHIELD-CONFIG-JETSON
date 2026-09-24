import RPi.GPIO as GPIO
from time import sleep

# Configuração dos pinos (Modo BCM)
servo_pin = 18

GPIO.setmode(GPIO.BCM)
GPIO.setup(servo_pin, GPIO.OUT)

# Configura o PWM com 50Hz (frequência padrão para servomotores)
pwm = GPIO.PWM(servo_pin, 50)
pwm.start(0)  # Inicia desativado

try:
    print("Movendo o servo para 90 graus...")
    # 7.5% de duty cycle = 90 graus
    pwm.ChangeDutyCycle(7.5)
    sleep(1.5)  # Aguarda o motor chegar à posição

except KeyboardInterrupt:
    print("\nInterrompido pelo usuário.")

finally:
    print("Retornando para a posição de 0 graus...")
    # 2.5% de duty cycle = 0 graus (posição inicial)
    pwm.ChangeDutyCycle(2.5)
    sleep(1)  # Aguarda o motor voltar
    
    # Para o sinal PWM e limpa os pinos
    pwm.ChangeDutyCycle(0)
    pwm.stop()
    GPIO.cleanup()
    print("Servo na posição inicial e conexões limpas.")