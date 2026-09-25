import sys
import warnings
from unittest.mock import MagicMock

warnings.filterwarnings("ignore")
sys.modules['pyaudio'] = MagicMock()

import cv2
import os
import time
from dotenv import load_dotenv
from gpiozero import OutputDevice
from edge_impulse_linux.image import ImageImpulseRunner

# Carrega variáveis básicas
load_dotenv()
MODEL_PATH = os.getenv("MODEL_PATH", "./epi-shield-v2.eim")
GPIO_PIN = int(os.getenv("GPIO_PIN", 18))
THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.85))
TARGET_LABEL = os.getenv("TARGET_LABEL", "vest") 
OPEN_TIME = float(os.getenv("OPEN_DURATION", 3.0))
CAMERA_ID = int(os.getenv("CAMERA_ID", 0))

# ==========================================
# VALORES EXTREMOS (0.5ms e 2.5ms)
# ==========================================
PULSO_EXTREMO_FECHADO = 0.0005  # Força máxima para um lado (~0 graus)
PULSO_EXTREMO_ABERTO = 0.0025   # Força máxima para o outro lado (~180 graus)

# Voltamos a usar o OutputDevice do seu código original
catraca_pino = OutputDevice(GPIO_PIN)

def mover_servo_extremo(tempo_pulso):
    """
    Usa o pulso manual (que agora funciona porque a IA está pausada).
    Roda por 50 ciclos (1 segundo) para forçar o motor a ir até o final.
    """
    for _ in range(50): 
        catraca_pino.on()
        time.sleep(tempo_pulso)
        catraca_pino.off()
        time.sleep(0.020 - tempo_pulso)
    
    # Após 1 segundo, ele sai do loop e o pino fica desligado automaticamente,
    # impedindo que o motor fique tremendo.

def main():
    if not os.path.exists(MODEL_PATH):
        print(f"Erro: Modelo não encontrado em {MODEL_PATH}")
        return

    runner = ImageImpulseRunner(MODEL_PATH)
    
    print("Testando giro extremo inicial (FECHANDO)...")
    mover_servo_extremo(PULSO_EXTREMO_FECHADO)
    
    try:
        model_info = runner.init()
        print(f"Modelo carregado: {model_info['project']['owner']} / {model_info['project']['name']}")
        print("Iniciando câmera... Pressione a tecla 'q' para sair.")
        
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
            
            features, img_processada = runner.get_features_from_image(frame)
            res = runner.classify(features)
            
            if "bounding_boxes" in res["result"]:
                for bb in res["result"]["bounding_boxes"]:
                    if bb["label"] == TARGET_LABEL and bb["value"] >= THRESHOLD:
                        vest_detectada = True 
                        x, y, w, h = bb["x"], bb["y"], bb["width"], bb["height"]
                        cv2.rectangle(img_processada, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.putText(img_processada, f"{bb['label']} {bb['value']:.2f}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            cv2.imshow("EPI-SHIELD", img_processada)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            if vest_detectada:
                print(f"\n[{TARGET_LABEL}] detectado! Pausando IA e testando GIRO EXTREMO DE ABERTURA...")
                
                # Vai virar tudo para um lado
                mover_servo_extremo(PULSO_EXTREMO_ABERTO)
                
                print(f"Aguardando passagem ({OPEN_TIME} segundos)...")
                time.sleep(OPEN_TIME)
                
                print("Fechando catraca com GIRO EXTREMO...")
                # Vai virar tudo para o outro lado
                mover_servo_extremo(PULSO_EXTREMO_FECHADO)
                
                # Limpa o buffer da câmera
                for _ in range(10):
                    cap.read()
                    
                print("Sistema pronto para a próxima detecção.")

    finally:
        print("\nEncerrando sistema...")
        # Força a posição fechada ao desligar
        mover_servo_extremo(PULSO_EXTREMO_FECHADO)
        
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        if runner:
            runner.stop()
        cv2.destroyAllWindows()
        print("Finalizado com sucesso.")

if __name__ == "__main__":
    main()