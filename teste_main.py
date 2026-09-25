import sys
import warnings
from unittest.mock import MagicMock

# Silencia os avisos
warnings.filterwarnings("ignore")
sys.modules['pyaudio'] = MagicMock()

import cv2
import os
import time
from dotenv import load_dotenv
from gpiozero import Servo
from edge_impulse_linux.image import ImageImpulseRunner

# Carrega variáveis
load_dotenv()
MODEL_PATH = os.getenv("MODEL_PATH", "./epi-shield-v2.eim")
GPIO_PIN = int(os.getenv("GPIO_PIN", 18))
THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.85))
TARGET_LABEL = os.getenv("TARGET_LABEL", "vest") 
OPEN_TIME = float(os.getenv("OPEN_DURATION", 3.0))
CAMERA_ID = int(os.getenv("CAMERA_ID", 0))

SERVO_OPEN_VALUE = float(os.getenv("SERVO_OPEN_VALUE", 1.0))
SERVO_CLOSE_VALUE = float(os.getenv("SERVO_CLOSE_VALUE", -1.0))

# Configura o servo com largura de pulso estendida para garantir força no movimento
catraca_servo = Servo(GPIO_PIN, min_pulse_width=0.0005, max_pulse_width=0.0025)

def mover_servo(posicao):
    """
    Move o servo e depois desliga o sinal PWM para a IA não atrapalhar
    """
    catraca_servo.value = posicao
    time.sleep(0.6)         # Dá tempo para o bracinho mecânico terminar de girar
    catraca_servo.value = None # Desliga o sinal elétrico (evita tremores)

def main():
    if not os.path.exists(MODEL_PATH):
        print(f"Erro: Modelo não encontrado em {MODEL_PATH}")
        return

    runner = ImageImpulseRunner(MODEL_PATH)
    
    print("Travando a catraca inicialmente...")
    mover_servo(SERVO_CLOSE_VALUE)
    
    try:
        model_info = runner.init()
        print(f"Modelo carregado: {model_info['project']['owner']} / {model_info['project']['name']}")
        print("Iniciando câmera... Pressione a tecla 'q' na janela do vídeo para sair.")
        
        cap = cv2.VideoCapture(CAMERA_ID, cv2.CAP_V4L2)
        if not cap.isOpened():
            print("ERRO: Não foi possível abrir a câmera.")
            return

        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            vest_detectada = False
            
            # IA processando o frame
            features, img_processada = runner.get_features_from_image(frame)
            res = runner.classify(features)
            
            # Verifica detecção de objetos
            if "bounding_boxes" in res["result"]:
                for bb in res["result"]["bounding_boxes"]:
                    if bb["label"] == TARGET_LABEL and bb["value"] >= THRESHOLD:
                        vest_detectada = True 
                        x, y, w, h = bb["x"], bb["y"], bb["width"], bb["height"]
                        cor = (0, 255, 0)
                        cv2.rectangle(img_processada, (x, y), (x + w, y + h), cor, 2)
                        cv2.putText(img_processada, f"{bb['label']} {bb['value']:.2f}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2)

            # Mostra a imagem atualizada
            cv2.imshow("EPI-SHIELD", img_processada)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            # LÓGICA SEQUENCIAL (PAUSA A IA)
            if vest_detectada:
                print(f"\n[{TARGET_LABEL}] detectado! Pausando câmera e abrindo catraca...")
                
                # 1. Abre a catraca
                mover_servo(SERVO_OPEN_VALUE)
                
                # 2. Espera o tempo configurado (A IA fica travada aqui, CPU livre!)
                print(f"Aguardando passagem ({OPEN_TIME} segundos)...")
                time.sleep(OPEN_TIME)
                
                # 3. Fecha a catraca
                print("Fechando catraca e retomando câmera...")
                mover_servo(SERVO_CLOSE_VALUE)
                
                # 4. Limpeza de Buffer da Câmera
                # Como a câmera continuou filmando enquanto o programa dormia, 
                # jogamos fora os quadros velhos acumulados para o vídeo não ficar atrasado.
                for _ in range(10):
                    cap.read()
                    
                print("Sistema pronto para a próxima detecção.")

    finally:
        print("\nEncerrando sistema...")
        mover_servo(SERVO_CLOSE_VALUE) # Garante que feche ao sair
        
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        if runner:
            runner.stop()
        cv2.destroyAllWindows()
        print("Finalizado com sucesso.")

if __name__ == "__main__":
    main()