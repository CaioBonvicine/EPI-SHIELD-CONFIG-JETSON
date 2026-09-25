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
from gpiozero import OutputDevice
from edge_impulse_linux.image import ImageImpulseRunner

# Carrega variáveis
load_dotenv()
MODEL_PATH = os.getenv("MODEL_PATH", "./epi-shield-v2.eim")
GPIO_PIN = int(os.getenv("GPIO_PIN", 18))
THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.85))
TARGET_LABEL = os.getenv("TARGET_LABEL", "vest") 
OPEN_TIME = float(os.getenv("OPEN_DURATION", 3.0))
CAMERA_ID = int(os.getenv("CAMERA_ID", 0))

# ==========================================
# PULSOS EXTREMOS QUE FUNCIONARAM NO TESTE
# ==========================================
PULSO_FECHADO = 0.0005  
PULSO_ABERTO = 0.0025   

# Configuração do pino do servo
catraca_pino = OutputDevice(GPIO_PIN)

def mover_servo(tempo_pulso):
    """
    EXATAMENTE A MESMA FUNÇÃO DO TESTE ISOLADO QUE FUNCIONOU!
    Gera 50 ciclos (1 segundo) de sinal perfeito.
    """
    for _ in range(50): 
        catraca_pino.on()
        time.sleep(tempo_pulso)
        catraca_pino.off()
        time.sleep(0.020 - tempo_pulso)

def main():
    if not os.path.exists(MODEL_PATH):
        print(f"Erro: Modelo não encontrado em {MODEL_PATH}")
        return

    runner = ImageImpulseRunner(MODEL_PATH)
    
    print("Posicionando catraca no estado FECHADO...")
    mover_servo(PULSO_FECHADO)
    
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

            # Mostra o vídeo
            cv2.imshow("EPI-SHIELD", img_processada)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            # LÓGICA DE ACIONAMENTO QUANDO DETECTAR O EPI
            if vest_detectada:
                print(f"\n[{TARGET_LABEL}] DETECTADO! Abrindo catraca...")
                
                # 1. Gira para abrir
                mover_servo(PULSO_ABERTO)
                
                # 2. Mantém aberto pelo tempo configurado (ex: 3 segundos)
                print(f"Catraca aberta. Aguardando passagem ({OPEN_TIME}s)...")
                time.sleep(OPEN_TIME)
                
                # 3. Gira para fechar
                print("Fechando catraca...")
                mover_servo(PULSO_FECHADO)
                
                # 4. Limpa o buffer da câmera para descartar frames antigos
                for _ in range(15):
                    cap.read()
                    
                print("Sistema pronto para a próxima detecção.")

    finally:
        print("\nEncerrando sistema...")
        # Garante que a catraca fecha ao sair
        mover_servo(PULSO_FECHADO)
        
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        if runner:
            runner.stop()
        cv2.destroyAllWindows()
        catraca_pino.close()
        print("Finalizado com sucesso.")

if __name__ == "__main__":
    main()