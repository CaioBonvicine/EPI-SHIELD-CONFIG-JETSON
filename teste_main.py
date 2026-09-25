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
import pigpio  # MUDANÇA: Usando pigpio
from dotenv import load_dotenv
from edge_impulse_linux.image import ImageImpulseRunner

# Carrega variáveis do .env
load_dotenv()
MODEL_PATH = os.getenv("MODEL_PATH", "./epi-shield-v2.eim")
GPIO_PIN = int(os.getenv("GPIO_PIN", 18)) # BCM 18 é Pino Físico 12, ok para PWM0
THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.85))
TARGET_LABEL = os.getenv("TARGET_LABEL", "vest") 
OPEN_TIME = float(os.getenv("OPEN_DURATION", 3.0))
CAMERA_ID = int(os.getenv("CAMERA_ID", 0))

# --- CONFIGURAÇÃO DO SERVO COM pigpio ---
# pigpio usa largura de pulso em microssegundos (µs)
# Faixa clássica estendida: 500µs (0°) a 2500µs (180°)
# Se notar que o motor força demais nas pontas, mude para 1000/2000.
# O .env original não é mais usado diretamente porque pigpio não usa -1.0 a 1.0.
PULSO_FECHADO_US = 1000 # Neutro baixo
PULSO_ABERTO_US = 2000   # Neutro alto

# Inicializa o pigpio
pi = pigpio.pi()
if not pi.connected:
    print("ERRO: Não foi possível conectar ao daemon 'pigpiod'.")
    print("Execute: sudo systemctl start pigpiod")
    sys.exit(1)

# pigpio configura o pino automaticamente como saída para o servo

def mover_servo_preciso(pulsewidth_us):
    """
    Move o servo usando DMA/Hardware PWM (não trava com a IA).
    Atribui 0 para cortar o sinal após o movimento.
    """
    pi.set_servo_pulsewidth(GPIO_PIN, pulsewidth_us)
    time.sleep(0.5) # Tempo para o braço físico terminar de girar
    pi.set_servo_pulsewidth(GPIO_PIN, 0) # Corta o sinal (evita tremor)

def main():
    if not os.path.exists(MODEL_PATH):
        print(f"Erro: Modelo não encontrado em {MODEL_PATH}")
        pi.stop()
        return

    runner = ImageImpulseRunner(MODEL_PATH)
    
    # Trava a catraca inicialmente
    print("Posicionando catraca no estado fechado...")
    mover_servo_preciso(PULSO_FECHADO_US)
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
            
            # Verifica detecção de objetos e desenha
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
                    print(f"[{TARGET_LABEL}] detectado na tela! Abrindo catraca...")
                    mover_servo_preciso(PULSO_ABERTO_US)
                    catraca_aberta = True
            else:
                if catraca_aberta:
                    tempo_sem_ver = tempo_atual - ultimo_momento_visto
                    if tempo_sem_ver >= OPEN_TIME:
                        print(f"[{TARGET_LABEL}] ausente da tela. Fechando catraca...")
                        mover_servo_preciso(PULSO_FECHADO_US)
                        catraca_aberta = False

    finally:
        # Encerramento seguro
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        if runner:
            runner.stop()
        cv2.destroyAllWindows()
        
        # Trava o servo e libera pigpio antes de fechar
        mover_servo_preciso(PULSO_FECHADO_US)
        pi.stop()
        print("\nSistema encerrado. Catraca travada e daemon pigpio liberado.")

if __name__ == "__main__":
    main()