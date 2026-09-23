import sys
from unittest.mock import MagicMock

# MOCK DO PYAUDIO: Engana o edge_impulse_linux para que ele não quebre 
# ao tentar carregar dependências de áudio, já que não temos root para instalá-las.
sys.modules['pyaudio'] = MagicMock()

import cv2
import os
import time
from dotenv import load_dotenv
from gpiozero import Servo
from edge_impulse_linux.image import ImageImpulseRunner

# Carrega variáveis
load_dotenv()
MODEL_PATH = os.getenv("MODEL_PATH", "./modelo.eim")
GPIO_PIN = int(os.getenv("GPIO_PIN", 18))
THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.8))
TARGET_LABEL = os.getenv("TARGET_LABEL", "vest") 
OPEN_TIME = float(os.getenv("OPEN_DURATION", 3.0))
CAMERA_ID = int(os.getenv("CAMERA_ID", 0))

# Configuração dos limites do Servo Motor (valores de -1.0 a 1.0)
SERVO_OPEN = float(os.getenv("SERVO_OPEN_VALUE", 1.0))
SERVO_CLOSE = float(os.getenv("SERVO_CLOSE_VALUE", -1.0))

# Inicializa o pino do servo
catraca_servo = Servo(GPIO_PIN)

def mover_servo(valor_posicao):
    catraca_servo.value = valor_posicao
    time.sleep(0.5) # Dá meio segundo para a mecânica do motor girar fisicamente
    catraca_servo.value = None # Desliga o sinal PWM para o motor não ficar "tremendo"

def main():
    if not os.path.exists(MODEL_PATH):
        print(f"Erro: Modelo não encontrado em {MODEL_PATH}")
        return

    runner = ImageImpulseRunner(MODEL_PATH)
    
    # Garante que a catraca comece fisicamente travada ao rodar o script
    mover_servo(SERVO_CLOSE)
    catraca_aberta = False
    ultimo_momento_visto = 0.0
    
    try:
        model_info = runner.init()
        print(f"Modelo carregado: {model_info['project']['owner']} / {model_info['project']['name']}")
        print("Iniciando monitoramento da câmera. Pressione Ctrl+C para encerrar.")
        
        # O loop roda infinitamente
        for res, img in runner.classifier(CAMERA_ID):
            vest_detectada = False
            
            # Verifica detecção de objetos (Bounding Boxes)
            if "bounding_boxes" in res["result"]:
                for bb in res["result"]["bounding_boxes"]:
                    if bb["label"] == TARGET_LABEL and bb["value"] >= THRESHOLD:
                        vest_detectada = True
                        break 
                        
            # Verifica classificação de imagem completa
            elif "classification" in res["result"]:
                predictions = res["result"]["classification"]
                if TARGET_LABEL in predictions and predictions[TARGET_LABEL] >= THRESHOLD:
                    vest_detectada = True

            tempo_atual = time.time()

            # LÓGICA DE ABERTURA E FECHAMENTO
            if vest_detectada:
                ultimo_momento_visto = tempo_atual 
                
                if not catraca_aberta:
                    print(f"[{TARGET_LABEL}] detectado! Abrindo catraca (Servo)...")
                    mover_servo(SERVO_OPEN)
                    catraca_aberta = True
                    
            else:
                if catraca_aberta:
                    tempo_sem_ver = tempo_atual - ultimo_momento_visto
                    
                    if tempo_sem_ver >= OPEN_TIME:
                        print(f"[{TARGET_LABEL}] ausente por {OPEN_TIME}s. Fechando catraca (Servo)...")
                        mover_servo(SERVO_CLOSE)
                        catraca_aberta = False

    finally:
        if runner:
            runner.stop()
        
        # Garante a segurança: trava a catraca antes do script fechar
        mover_servo(SERVO_CLOSE)
        print("\nSistema encerrado. Catraca travada.")

if __name__ == "__main__":
    main()