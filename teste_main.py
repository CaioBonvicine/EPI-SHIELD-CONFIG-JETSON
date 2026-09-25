import sys
import warnings
from unittest.mock import MagicMock

# Silencia os avisos
warnings.filterwarnings("ignore")
sys.modules['pyaudio'] = MagicMock()

import cv2
import os
import time
import multiprocessing # MUDANÇA: Usando multiprocessamento para fugir do gargalo da CPU
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

# ==========================================
# PROCESSO INDEPENDENTE DO SERVO MOTOR
# Roda em outro núcleo da CPU para não travar
# ==========================================
def controlador_servo(estado_catraca, pino, valor_aberto, valor_fechado):
    """
    Fica monitorando a variável 'estado_catraca'.
    Se mudar para 1, abre. Se mudar para 0, fecha.
    """
    # Ampliamos a faixa de pulso para o motor ter mais força/ângulo
    meu_servo = Servo(pino, min_pulse_width=0.0005, max_pulse_width=0.0025)
    
    ultimo_estado_aplicado = -1 
    
    while True:
        estado_atual = estado_catraca.value
        
        # Se houve mudança na ordem (abrir ou fechar)
        if estado_atual != ultimo_estado_aplicado:
            if estado_atual == 1:
                meu_servo.value = valor_aberto
            else:
                meu_servo.value = valor_fechado
            
            # Dá meio segundo para o braço mecânico se mover
            time.sleep(0.5)
            
            # Corta o sinal do motor (evita que ele fique tremendo/puxando energia à toa)
            meu_servo.value = None 
            
            ultimo_estado_aplicado = estado_atual
            
        time.sleep(0.1) # Pausa leve para não sobrecarregar o núcleo

# ==========================================
# PROCESSO PRINCIPAL (INTELIGÊNCIA ARTIFICIAL)
# ==========================================
def main():
    if not os.path.exists(MODEL_PATH):
        print(f"Erro: Modelo não encontrado em {MODEL_PATH}")
        return

    # Variável compartilhada entre os processos: 0 = Fechado, 1 = Aberto
    estado_catraca = multiprocessing.Value('i', 0)
    
    # Inicia o processo do servo no fundo
    processo_servo = multiprocessing.Process(
        target=controlador_servo, 
        args=(estado_catraca, GPIO_PIN, SERVO_OPEN_VALUE, SERVO_CLOSE_VALUE)
    )
    processo_servo.daemon = True
    processo_servo.start()

    runner = ImageImpulseRunner(MODEL_PATH)
    ultimo_momento_visto = 0.0
    
    try:
        model_info = runner.init()
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

            cv2.imshow("EPI-SHIELD", img_processada)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            tempo_atual = time.time()

            # Manda a ordem para o processo do servo!
            if vest_detectada:
                ultimo_momento_visto = tempo_atual 
                if estado_catraca.value == 0:
                    print(f"[{TARGET_LABEL}] detectado! Mandando sinal para abrir...")
                    estado_catraca.value = 1 # Muda para 1 (Abre)
            else:
                if estado_catraca.value == 1:
                    tempo_sem_ver = tempo_atual - ultimo_momento_visto
                    if tempo_sem_ver >= OPEN_TIME:
                        print(f"[{TARGET_LABEL}] ausente. Mandando sinal para fechar...")
                        estado_catraca.value = 0 # Muda para 0 (Fecha)

    finally:
        print("\nEncerrando sistema...")
        # Força fechamento antes de sair
        estado_catraca.value = 0
        time.sleep(1) # Dá tempo pro servo fechar
        
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        if runner:
            runner.stop()
        cv2.destroyAllWindows()
        processo_servo.terminate() # Mata o processo do servo
        print("Finalizado com sucesso.")

if __name__ == "__main__":
    main()