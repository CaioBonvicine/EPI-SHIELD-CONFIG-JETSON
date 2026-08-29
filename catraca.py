import cv2
import requests
import time
import os
import Jetson.GPIO as GPIO
from edgeimpulse_linux.image import ImageImpulseRunner

# 1. Configurações da API
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8001/events")
AGENTE_ID = "jetson-catraca-01"
SETOR_ID = 1 # ID do setor no dashboard

# 2. Configuração do Servo (PWM no pino 33)
SERVO_PIN = 33
GPIO.setmode(GPIO.BOARD)
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, 50) # 50Hz
pwm.start(0)

# Controle de estado do servo (evita reenviar sinal sem necessidade)
catraca_esta_aberta = False

def posicionar_catraca(abrir: bool):
    """
    Muda a posição do servo apenas se houver alteração de estado.
    """
    global catraca_esta_aberta
    
    if abrir and not catraca_esta_aberta:
        print("[SERVO] Veste detectada! Abrindo catraca...")
        pwm.ChangeDutyCycle(7) # Ajuste este valor para o ângulo de abertura
        catraca_esta_aberta = True
        
    elif not abrir and catraca_esta_aberta:
        print("[SERVO] Veste ausente! Fechando catraca...")
        pwm.ChangeDutyCycle(2) # Ajuste este valor para o ângulo de fechamento
        catraca_esta_aberta = False

def verificar_veste(bounding_boxes, threshold=0.60):
    """
    Checa especificamente se 'vest' foi detectada acima do threshold.
    """
    for bbox in bounding_boxes:
        # Ajustado para bater exatamente com a classe do Edge Impulse: 'vest'
        if bbox['label'] == 'vest' and bbox['value'] >= threshold:
            return True
    return False
def main():
    modelo_path = "modelo_epi.eim"
    runner = ImageImpulseRunner(modelo_path)
    
    try:
        model_info = runner.init()
        print(f"Modelo IA carregado: {model_info}")
        
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        ultimo_envio = 0
        intervalo_envio = 2.0
        
        # Garante que a catraca inicie fechada
        posicionar_catraca(abrir=False)
        
        while True:
            ret, frame = cap.read()
            if not ret: continue
            
            features, cropped = runner.get_custom_image_tensor(frame)
            res = runner.classify(features)
            
            bboxes = res["result"].get("bounding_boxes", [])
            tem_veste = verificar_veste(bboxes)
            
            # Atualiza a posição do servo em tempo real conforme a detecção
            posicionar_catraca(abrir=tem_veste)
            
            status = "allowed" if tem_veste else "blocked"
            faltantes = [] if tem_veste else ["vest"]
            
            # Envia relatório periódico para a API do dashboard
            tempo_atual = time.time()
            if (tempo_atual - ultimo_envio) > intervalo_envio:
                payload = {
                    "agente_id": AGENTE_ID,
                    "setor_id": SETOR_ID, 
                    "status": status,
                    "detections": bboxes,
                    "epis_faltantes": faltantes
                }
                
                try:
                    requests.post(API_URL, json=payload, timeout=2)
                    ultimo_envio = tempo_atual
                except requests.exceptions.RequestException as e:
                    print(f"Aviso - Falha ao conectar na API: {e}")
            
            time.sleep(0.05)
            
    finally:
        print("Encerrando sistema, fechando catraca e limpando GPIO...")
        posicionar_catraca(abrir=False)
        time.sleep(0.5)
        runner.stop()
        pwm.stop()
        GPIO.cleanup()
        cap.release()

if __name__ == "__main__":
    main()