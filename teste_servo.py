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
    print("Indo para a posição inicial de 0 graus...")
    pwm.ChangeDutyCycle(0)  # 2.5% = 0 graus
    sleep(1)
    
    print("Abrindo até 90 graus...")
    pwm.ChangeDutyCycle(7.5)  # 7.5% = 90 graus
    sleep(1.5)
    
    print("Voltando para a posição de 90 graus (ou mantendo)...")
    pwm.ChangeDutyCycle(7.5)  # Mantém ou ajusta se quiser voltar para 0
    sleep(1)

except KeyboardInterrupt:
    print("\nInterrompido pelo usuário.")

finally:
    print("Encerrando e limpando pinos...")
    # Para o sinal PWM e limpa os pinos de forma segura
    pwm.ChangeDutyCycle(0)
    pwm.stop()
    GPIO.cleanup()
    print("Finalizado com segurança.")