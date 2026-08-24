import cv2
import requests
import time
import os
import Jetson.GPIO as GPIO
from edgeimpulse_linux.image import ImageImpulseRunner

# 1. Configurações da API
# Pega o IP por variável de ambiente (facilita testar depois). Se não achar, usa localhost.
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8001/events")
AGENTE_ID = "jetson-catraca-01"
SETOR_ID = 1 # ID do setor que deve bater com o banco de dados do servidor

# 2. Configuração do Servo (PWM no pino 33)
SERVO_PIN = 33
GPIO.setmode(GPIO.BOARD)
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, 50) # 50Hz
pwm.start(0)

def abrir_catraca():
    print("Acesso Liberado! Abrindo catraca...")
    pwm.ChangeDutyCycle(7) # Ajuste este valor para o ângulo de abertura da sua catraca
    time.sleep(3)
    pwm.ChangeDutyCycle(2) # Ajuste este valor para a posição fechada
    print("Catraca fechada.")

def verificar_epis(bounding_boxes, threshold=0.60):
    """
    Checa se capacete, veste e luvas foram detectados com confiança >= threshold
    """
    epis_encontrados = set()
    for bbox in bounding_boxes:
        if bbox['value'] >= threshold:
            epis_encontrados.add(bbox['label'])
    
    # ATENÇÃO: As strings abaixo devem ser EXATAMENTE iguais às classes que você criou no Edge Impulse
    epis_obrigatorios = {"capacete", "veste", "luvas", "humanos"}
    
    faltantes = epis_obrigatorios - epis_encontrados
    
    return len(faltantes) == 0, list(faltantes)

def main():
    modelo_path = "modelo_epi.eim" # Nome padronizado
    runner = ImageImpulseRunner(modelo_path)
    
    try:
        model_info = runner.init()
        print(f"Modelo IA carregado: {model_info}")
        
        cap = cv2.VideoCapture(0) # 0 para USB. Se for câmera CSI, a string de inicialização do GStreamer vai aqui.
        
        # Controle de fluxo para não floodar a API
        ultimo_envio = 0
        intervalo_envio = 2.0 # Envia no máximo 1 relatório a cada 2 segundos
        
        while True:
            ret, frame = cap.read()
            if not ret: continue
            
            features, cropped = runner.get_custom_image_tensor(frame)
            res = runner.classify(features)
            
            if "bounding_boxes" in res["result"]:
                bboxes = res["result"]["bounding_boxes"]
                tudo_conforme, faltantes = verificar_epis(bboxes)
                
                if tudo_conforme:
                    abrir_catraca()
                    status = "allowed"
                else:
                    status = "blocked"
                    
                # 4. Envia o relatório via API apenas se passou o intervalo
                tempo_atual = time.time()
                if (tempo_atual - ultimo_envio) > intervalo_envio:
                    payload = {
                        "agente_id": AGENTE_ID,
                        "setor_id": SETOR_ID, 
                        "status": status,
                        "detections": bboxes,
                        "epis_faltantes": faltantes # O banco do seu amigo na migration 001 espera essa lista
                    }
                    
                    try:
                        requests.post(API_URL, json=payload, timeout=2)
                        ultimo_envio = tempo_atual
                    except requests.exceptions.RequestException as e:
                        print(f"Aviso - Falha ao conectar na API: {e}")
            
            # Pequeno delay para aliviar a CPU
            time.sleep(0.05)
            
    finally:
        # Bloco de segurança: independente de erro ou interrupção (Ctrl+C), limpa os pinos.
        print("Encerrando sistema e limpando GPIO...")
        runner.stop()
        pwm.stop()
        GPIO.cleanup()
        cap.release()

if __name__ == "__main__":
    main()