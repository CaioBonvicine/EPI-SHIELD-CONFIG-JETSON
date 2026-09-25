import sys
import warnings
from unittest.mock import MagicMock

# Silencia os avisos
warnings.filterwarnings("ignore")

# MOCK DO PYAUDIO: Engana o edge_impulse_linux
sys.modules['pyaudio'] = MagicMock()

import cv2
import os
import time
import RPi.GPIO as GPIO  # MUDANÇA: Usando RPi.GPIO em vez de gpiozero
from dotenv import load_dotenv
from edge_impulse_linux.image import ImageImpulseRunner

# Carrega variáveis
load_dotenv()
MODEL_PATH = os.getenv("MODEL_PATH", "./epi-shield-v2.eim")
GPIO_PIN = int(os.getenv("GPIO_PIN", 18))
THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.85))
TARGET_LABEL = os.getenv("TARGET_LABEL", "vest") 
OPEN_TIME = float(os.getenv("OPEN_DURATION", 3.0))
CAMERA_ID = int(os.getenv("CAMERA_ID", 0))

# --- CONFIGURAÇÃO DO SERVO COM RPi.GPIO ---
# Transforma o tempo de pulso original em Duty Cycle (%)
# 0.0010s (1ms) em um ciclo de 20ms (50Hz) = 5%
# 0.0020s (2ms) em um ciclo de 20ms (50Hz) = 10%
DUTY_FECHADO = 5.0  
DUTY_ABERTO = 10.0  

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_PIN, GPIO.OUT)
servo_pwm = GPIO.PWM(GPIO_PIN, 50) # Frequência de 50Hz
servo_pwm.start(0)

def mover_servo(duty_cycle):
    """Move o servo usando hardware/C-level PWM que não trava com a IA"""
    servo_pwm.ChangeDutyCycle(duty_cycle)
    time.sleep(0.5) # Tempo para o braço físico terminar de girar
    servo_pwm.ChangeDutyCycle(0) # Corta o sinal para o servo não ficar "tremendo"

def main():
    if not os.path.exists(MODEL_PATH):
        print(f"Erro: Modelo não encontrado em {MODEL_PATH}")
        return

    runner = ImageImpulseRunner(MODEL_PATH)
    
    # Trava a catraca inicialmente
    print("Posicionando catraca no estado fechado...")
    mover_servo(DUTY_FECHADO)
    catraca_aberta = False
    ultimo_momento_visto = 0.0
    
    try:
        model_info = runner.init()
        print(f"Modelo carregado: {model_info['project']['owner']} / {model_info['project']['name']}")
        print("Iniciando câmera... Pressione a tecla 'q' na janela do vídeo para sair.")
        
        # INICIALIZAÇÃO MANUAL DA CÂMERA COM OPENCV
        cap = cv2.VideoCapture(CAMERA_ID, cv2.CAP_V4L2)
        if not cap.isOpened():
            print(f"ERRO: Não foi possível abrir a câmera {CAMERA_ID} com o OpenCV.")
            return

        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            vest_detectada = False
            
            # Prepara a imagem e faz a IA classificar o frame
            features, img_processada = runner.get_features_from_image(frame)
            res = runner.classify(features)
            
            # Verifica detecção de objetos
            if "bounding_boxes" in res["result"]:
                for bb in res["result"]["bounding_boxes"]:
                    label = bb["label"]
                    conf = bb["value"]
                    
                    if label == TARGET_LABEL and conf >= THRESHOLD:
                        vest_detectada = True 
                        x, y, w, h = bb["x"], bb["y"], bb["width"], bb["height"]
                        
                        cor = (0, 255, 0)
                        cv2.rectangle(img_processada, (x, y), (x + w, y + h), cor, 2)
                        cv2.putText(img_processada, f"{label} {conf:.2f}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2)

            cv2.imshow("EPI-SHIELD - Monitoramento", img_processada)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            tempo_atual = time.time()

            # LÓGICA DE ABERTURA E FECHAMENTO
            if vest_detectada:
                ultimo_momento_visto = tempo_atual 
                if not catraca_aberta:
                    print(f"[{TARGET_LABEL}] detectado na tela! Abrindo catraca (Servo)...")
                    mover_servo(DUTY_ABERTO)
                    catraca_aberta = True
            else:
                if catraca_aberta:
                    tempo_sem_ver = tempo_atual - ultimo_momento_visto
                    if tempo_sem_ver >= OPEN_TIME:
                        print(f"[{TARGET_LABEL}] ausente da tela. Fechando catraca (Servo)...")
                        mover_servo(DUTY_FECHADO)
                        catraca_aberta = False

    finally:
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        if runner:
            runner.stop()
        cv2.destroyAllWindows()
        
        # Trava o servo e limpa os pinos antes de fechar
        mover_servo(DUTY_FECHADO)
        servo_pwm.stop()
        GPIO.cleanup()
        print("\nSistema encerrado. Catraca travada e pinos liberados.")

if __name__ == "__main__":
    main()