import cv2
import requests
import time
import os
import Jetson.GPIO as GPIO
from edge_impulse_linux.image import ImageImpulseRunner

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8001/events")
AGENTE_ID = "jetson-catraca-01"
SETOR_ID = 1

SERVO_PIN = 33
pwm = None
catraca_esta_aberta = False


def posicionar_catraca(abrir: bool):
    global catraca_esta_aberta
    if abrir and not catraca_esta_aberta:
        print("[SERVO] Veste detectada! Abrindo catraca...")
        pwm.ChangeDutyCycle(7)
        catraca_esta_aberta = True
    elif not abrir and catraca_esta_aberta:
        print("[SERVO] Veste ausente! Fechando catraca...")
        pwm.ChangeDutyCycle(2)
        catraca_esta_aberta = False


def verificar_veste(bounding_boxes, threshold=0.60):
    for bbox in bounding_boxes:
        if bbox['label'] == 'vest' and bbox['value'] >= threshold:
            return True
    return False


def main():
    global pwm
    runner = None
    cap = None

    try:
        print("[1] Configurando GPIO...")
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(SERVO_PIN, GPIO.OUT)
        pwm = GPIO.PWM(SERVO_PIN, 50)
        pwm.start(0)
        print("[1] GPIO OK")

        print("[2] Carregando modelo...")
        # CORRIGIDO: Nome atualizado para modelo_epiV2.eim
        runner = ImageImpulseRunner("modelo_epiV2.eim")
        model_info = runner.init()
        print(f"[2] Modelo OK: {model_info['project']}")

        print("[3] Abrindo camera...")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise RuntimeError("Camera /dev/video0 nao abriu")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        print("[3] Camera OK - iniciando loop")

        ultimo_envio = 0
        intervalo_envio = 2.0
        posicionar_catraca(abrir=False)

        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            features, cropped = runner.get_features_from_image(frame)
            res = runner.classify(features)

            bboxes = res["result"].get("bounding_boxes", [])
            tem_veste = verificar_veste(bboxes)
            posicionar_catraca(abrir=tem_veste)

            status = "allowed" if tem_veste else "blocked"
            faltantes = [] if tem_veste else ["vest"]

            tempo_atual = time.time()
            if (tempo_atual - ultimo_envio) > intervalo_envio:
                payload = {
                    "agente_id": AGENTE_ID,
                    "setor_id": SETOR_ID,
                    "status": status,
                    "detections": bboxes,
                    "epis_faltantes": faltantes,
                }
                try:
                    requests.post(API_URL, json=payload, timeout=2)
                    ultimo_envio = tempo_atual
                except requests.exceptions.RequestException as e:
                    print(f"Aviso - Falha ao conectar na API: {e}")

            time.sleep(0.05)

    except Exception as e:
        import traceback
        print(f"ERRO: {type(e).__name__}: {e}")
        traceback.print_exc()

    finally:
        print("Encerrando...")
        try:
            if pwm:
                posicionar_catraca(abrir=False)
                time.sleep(0.5)
                pwm.stop()
        except Exception:
            pass
        if runner:
            runner.stop()
        if cap:
            cap.release()
        GPIO.cleanup()


if __name__ == "__main__":
    main()