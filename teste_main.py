import sys
import warnings
from unittest.mock import MagicMock

warnings.filterwarnings("ignore")
sys.modules['pyaudio'] = MagicMock()

import cv2
import os
import time
from dotenv import load_dotenv
from edge_impulse_linux.image import ImageImpulseRunner

load_dotenv()
MODEL_PATH = os.getenv("MODEL_PATH", "./epi-shield-v2.eim")
THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.85))
TARGET_LABEL = os.getenv("TARGET_LABEL", "vest") 
OPEN_TIME = float(os.getenv("OPEN_DURATION", 3.0))
CAMERA_ID = int(os.getenv("CAMERA_ID", 0))
CATRACA_FILE = "estado_catraca.txt"

def main():
    if not os.path.exists(MODEL_PATH):
        print(f"Erro: Modelo não encontrado em {MODEL_PATH}")
        return

    runner = ImageImpulseRunner(MODEL_PATH)
    
    if os.path.exists(CATRACA_FILE):
        os.remove(CATRACA_FILE)

    try:
        model_info = runner.init()
        print(f"Modelo carregado: {model_info['project']['owner']} / {model_info['project']['name']}")
        print("Iniciando câmera... Pressione a tecla 'q' para sair.")
        
        # Reduz o tamanho do buffer da câmera para evitar delay (lag) na imagem
        cap = cv2.VideoCapture(CAMERA_ID, cv2.CAP_V4L2)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if not cap.isOpened():
            print("ERRO: Não foi possível abrir a câmera.")
            return

        ultima_abertura = 0

        while True:
            # Pula alguns frames para garantir que a IA está analisando o "agora" e não o passado
            for _ in range(3):
                cap.grab()
                
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            vest_detectada = False
            
            features, img_processada = runner.get_features_from_image(frame)
            res = runner.classify(features)
            
            # --- RESTAURADO: Lógica completa de detecção do seu código original ---
            
            # 1. Verifica Detecção de Objetos (Quadrados)
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

            # 2. Verifica Classificação de Imagem Inteira (Fallback)
            elif "classification" in res["result"]:
                predictions = res["result"]["classification"]
                if TARGET_LABEL in predictions and predictions[TARGET_LABEL] >= THRESHOLD:
                    vest_detectada = True
                    conf = predictions[TARGET_LABEL]
                    cv2.putText(img_processada, f"{TARGET_LABEL} {conf:.2f} DETECTADO", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # -----------------------------------------------------------------------

            cv2.imshow("EPI-SHIELD", img_processada)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            tempo_atual = time.time()
            if vest_detectada and (tempo_atual - ultima_abertura > (OPEN_TIME + 2.0)):
                print(f"\n[{TARGET_LABEL}] DETECTADO! Solicitando abertura ao servo...")
                with open(CATRACA_FILE, "w") as f:
                    f.write("ABRIR")
                ultima_abertura = tempo_atual

    finally:
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        if runner:
            runner.stop()
        cv2.destroyAllWindows()
        print("Sistema encerrado.")

if __name__ == "__main__":
    main()