import sys
import warnings
from unittest.mock import MagicMock

# Silencia os avisos da biblioteca gpiozero
warnings.filterwarnings("ignore", module="gpiozero")

# MOCK DO PYAUDIO: Engana o edge_impulse_linux
sys.modules['pyaudio'] = MagicMock()

import cv2
import os
import time
from dotenv import load_dotenv
from gpiozero import Servo # Mudança aqui: Importando a classe Servo
from edge_impulse_linux.image import ImageImpulseRunner

# Carrega variáveis
load_dotenv()
MODEL_PATH = os.getenv("MODEL_PATH", "./epi-shield-v2.eim")
GPIO_PIN = int(os.getenv("GPIO_PIN", 18))
THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.85))
TARGET_LABEL = os.getenv("TARGET_LABEL", "vest") 
OPEN_TIME = float(os.getenv("OPEN_DURATION", 3.0))
CAMERA_ID = int(os.getenv("CAMERA_ID", 0))

# Configuração do Servo Motor baseada no .env
SERVO_OPEN_VALUE = float(os.getenv("SERVO_OPEN_VALUE", 1.0))
SERVO_CLOSE_VALUE = float(os.getenv("SERVO_CLOSE_VALUE", -1.0))

# Inicializa o servo no pino correto
catraca_servo = Servo(GPIO_PIN)

def mover_servo(posicao):
    """
    Move o servo para a posição informada (-1.0 a 1.0)
    """
    catraca_servo.value = posicao
    # Pausa rápida para dar tempo físico do motor girar antes do código continuar
    time.sleep(0.5) 

def main():
    if not os.path.exists(MODEL_PATH):
        print(f"Erro: Modelo não encontrado em {MODEL_PATH}")
        return

    runner = ImageImpulseRunner(MODEL_PATH)
    
    # Trava a catraca inicialmente
    mover_servo(SERVO_CLOSE_VALUE)
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
                print("Falha ao ler frame. Tentando novamente...")
                time.sleep(0.1)
                continue
            
            vest_detectada = False
            
            # Prepara a imagem e faz a IA classificar o frame
            features, img_processada = runner.get_features_from_image(frame)
            res = runner.classify(features)
            
            # Verifica detecção de objetos e DESENHA NA TELA
            if "bounding_boxes" in res["result"]:
                for bb in res["result"]["bounding_boxes"]:
                    label = bb["label"]
                    conf = bb["value"]
                    
                    if label == TARGET_LABEL and conf >= THRESHOLD:
                        vest_detectada = True 
                        x, y, w, h = bb["x"], bb["y"], bb["width"], bb["height"]
                        
                        # Desenha o quadrado
                        cor = (0, 255, 0) # Verde se for o EPI
                        cv2.rectangle(img_processada, (x, y), (x + w, y + h), cor, 2)
                        cv2.putText(img_processada, f"{label} {conf:.2f}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2)

            # Verifica classificação de imagem inteira (fallback)
            elif "classification" in res["result"]:
                predictions = res["result"]["classification"]
                if TARGET_LABEL in predictions and predictions[TARGET_LABEL] >= THRESHOLD:
                    vest_detectada = True
                    cv2.putText(img_processada, f"{TARGET_LABEL} DETECTADA", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # --- EXIBE A JANELA DE VÍDEO ---
            cv2.imshow("EPI-SHIELD - Monitoramento", img_processada)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            tempo_atual = time.time()

            # LÓGICA DE ABERTURA E FECHAMENTO
            if vest_detectada:
                ultimo_momento_visto = tempo_atual 
                if not catraca_aberta:
                    print(f"[{TARGET_LABEL}] detectado na tela! Abrindo catraca (Servo)...")
                    mover_servo(SERVO_OPEN_VALUE)
                    catraca_aberta = True
            else:
                if catraca_aberta:
                    tempo_sem_ver = tempo_atual - ultimo_momento_visto
                    if tempo_sem_ver >= OPEN_TIME:
                        print(f"[{TARGET_LABEL}] ausente da tela. Fechando catraca (Servo)...")
                        mover_servo(SERVO_CLOSE_VALUE)
                        catraca_aberta = False

    finally:
        # Fecha os processos de vídeo de forma segura
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        if runner:
            runner.stop()
        
        cv2.destroyAllWindows()
        # Trava o servo antes de fechar
        mover_servo(SERVO_CLOSE_VALUE)
        print("\nSistema encerrado. Catraca travada.")

if __name__ == "__main__":
    main()