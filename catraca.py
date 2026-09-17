import cv2
import time
import sys
import Jetson.GPIO as GPIO
from edge_impulse_linux.image import ImageImpulseRunner


# ============================================================
# CONFIGURAÇÕES
# ============================================================

SERVO_PIN = 33

# Valores atuais já utilizados no projeto.
# Devem ser calibrados fisicamente de acordo com a catraca.
DUTY_CATRACA_ABERTA = 7
DUTY_CATRACA_FECHADA = 2

# Confiança mínima para considerar que a vestimenta foi detectada.
THRESHOLD_VESTE = 0.60

# Tempo durante o qual a nova condição precisa permanecer
# estável antes de alterar o estado da catraca.
TEMPO_ATRASO_SEGUNDOS = 5.0


# ============================================================
# ESTADO GLOBAL
# ============================================================

pwm = None
catraca_esta_aberta = False


# ============================================================
# CONTROLE DA CATrACA
# ============================================================

def posicionar_catraca(abrir: bool):
    global catraca_esta_aberta

    if pwm is None:
        return

    # Abrir
    if abrir and not catraca_esta_aberta:
        print("[SERVO] Veste confirmada! Abrindo catraca...")

        pwm.ChangeDutyCycle(DUTY_CATRACA_ABERTA)

        catraca_esta_aberta = True

    # Fechar
    elif not abrir and catraca_esta_aberta:
        print("[SERVO] Veste ausente! Fechando catraca...")

        pwm.ChangeDutyCycle(DUTY_CATRACA_FECHADA)

        catraca_esta_aberta = False


# ============================================================
# VERIFICAÇÃO DA VESTIMENTA
# ============================================================

def verificar_veste(bounding_boxes, threshold=THRESHOLD_VESTE):
    """
    Retorna True caso exista pelo menos uma detecção
    da classe 'vest' com confiança igual ou superior
    ao threshold definido.
    """

    for bbox in bounding_boxes:
        label = bbox.get("label", "")
        confianca = bbox.get("value", 0.0)

        if label == "vest" and confianca >= threshold:
            return True

    return False


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():
    global pwm
    global catraca_esta_aberta

    runner = None
    cap = None

    try:
        # ========================================================
        # 1. CONFIGURAÇÃO DO GPIO
        # ========================================================

        print("[1] Configurando GPIO...")

        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(SERVO_PIN, GPIO.OUT)

        pwm = GPIO.PWM(SERVO_PIN, 50)
        pwm.start(0)

        print("[1] GPIO OK")
        print(f"[1] Servo configurado no pino físico {SERVO_PIN}")

        # ========================================================
        # 2. CARREGAMENTO DO MODELO
        # ========================================================

        print("[2] Carregando modelo...")

        runner = ImageImpulseRunner("modelo_epiV2.eim")
        model_info = runner.init()

        print(f"[2] Modelo OK: {model_info['project']}")

        # Verificação opcional dos labels disponíveis no modelo.
        # Usa .get() para evitar que a aplicação pare caso essa
        # informação não esteja presente no retorno do SDK.
        parametros_modelo = model_info.get("model_parameters", {})
        labels_modelo = parametros_modelo.get("labels", [])

        if labels_modelo:
            print(f"[2] Labels identificadas: {labels_modelo}")

            if "vest" not in labels_modelo:
                print(
                    "[2] AVISO: o label 'vest' não foi encontrado "
                    "na lista de labels do modelo."
                )
        else:
            print("[2] Labels do modelo nao foram informadas pelo SDK.")

        # ========================================================
        # 3. ABERTURA DA CÂMERA
        # ========================================================

        print("[3] Abrindo camera...")

        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            raise RuntimeError("Camera /dev/video0 nao abriu")

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        largura = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        altura = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(
            f"[3] Camera OK - resolucao configurada: "
            f"{largura}x{altura}"
        )

        print("[3] Iniciando loop offline...")

        # ========================================================
        # GARANTE QUE A CATrACA COMECE FECHADA
        # ========================================================

        pwm.ChangeDutyCycle(DUTY_CATRACA_FECHADA)
        catraca_esta_aberta = False

        # ========================================================
        # CONTROLE DO ATRASO
        # ========================================================

        tempo_inicio_transicao = None
        proximo_estado = None

        # ========================================================
        # LOOP PRINCIPAL
        # ========================================================

        while True:

            ret, frame = cap.read()

            if not ret:
                print("[CAMERA] Falha ao capturar frame.")
                time.sleep(0.1)
                continue

            # ----------------------------------------------------
            # OpenCV captura em BGR.
            # O fluxo de visão do Edge Impulse utiliza RGB.
            # ----------------------------------------------------

            frame_rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            # ----------------------------------------------------
            # Executa a inferência
            # ----------------------------------------------------

            features, cropped = runner.get_features_from_image(
                frame_rgb
            )

            res = runner.classify(features)

            # ----------------------------------------------------
            # Obtém bounding boxes
            # ----------------------------------------------------

            bboxes = res.get(
                "result",
                {}
            ).get(
                "bounding_boxes",
                []
            )

            # ----------------------------------------------------
            # Verifica se a vestimenta foi detectada
            # ----------------------------------------------------

            tem_veste = verificar_veste(bboxes)

            tempo_atual = time.time()

            # ----------------------------------------------------
            # Exibe as detecções encontradas
            # ----------------------------------------------------

            for bbox in bboxes:
                label = bbox.get("label", "desconhecido")
                confianca = bbox.get("value", 0.0)

                print(
                    f"[IA] Detectado: {label} "
                    f"| Confianca: {confianca:.2f}"
                )

            # ----------------------------------------------------
            # LÓGICA DE TRANSIÇÃO
            #
            # A nova condição precisa permanecer durante
            # TEMPO_ATRASO_SEGUNDOS antes de alterar a catraca.
            # ----------------------------------------------------

            if tem_veste != catraca_esta_aberta:

                # Uma nova mudança foi detectada.
                if proximo_estado != tem_veste:

                    proximo_estado = tem_veste
                    tempo_inicio_transicao = tempo_atual

                    acao = "abrir" if tem_veste else "fechar"

                    print(
                        f"[IA] Mudanca detectada "
                        f"({'Veste' if tem_veste else 'Sem veste'}). "
                        f"Aguardando "
                        f"{TEMPO_ATRASO_SEGUNDOS:.1f}s "
                        f"para {acao}..."
                    )

                # A mudança permaneceu durante os 5 segundos.
                elif (
                    tempo_inicio_transicao is not None
                    and (
                        tempo_atual - tempo_inicio_transicao
                        >= TEMPO_ATRASO_SEGUNDOS
                    )
                ):
                    posicionar_catraca(tem_veste)

                    tempo_inicio_transicao = None
                    proximo_estado = None

            else:
                # O estado detectado é igual ao estado atual
                # da catraca. Não existe mudança pendente.
                tempo_inicio_transicao = None
                proximo_estado = None

            # Pequena pausa para não ocupar desnecessariamente
            # 100% da CPU.
            time.sleep(0.05)

    # ============================================================
    # CTRL+C
    # ============================================================

    except KeyboardInterrupt:
        print("\n[CTRL+C] Programa interrompido pelo usuario.")

    # ============================================================
    # ERRO
    # ============================================================

    except Exception as e:
        import traceback

        print(
            f"ERRO CRITICO: "
            f"{type(e).__name__}: {e}"
        )

        traceback.print_exc()

        sys.exit(1)

    # ============================================================
    # FINALIZAÇÃO
    # ============================================================

    finally:
        print("Encerrando recursos...")

        # --------------------------------------------------------
        # Garante que a catraca seja fechada
        # --------------------------------------------------------

        try:
            if pwm is not None:
                posicionar_catraca(abrir=False)

                time.sleep(0.5)

                pwm.stop()

        except Exception:
            pass

        # --------------------------------------------------------
        # Libera o modelo
        # --------------------------------------------------------

        try:
            if runner is not None:
                runner.stop()

        except Exception:
            pass

        # --------------------------------------------------------
        # Libera a câmera
        # --------------------------------------------------------

        try:
            if cap is not None:
                cap.release()

        except Exception:
            pass

        # --------------------------------------------------------
        # Limpa GPIO
        # --------------------------------------------------------

        try:
            GPIO.cleanup()

        except Exception:
            pass

        print("Recursos liberados.")


# ============================================================
# PONTO DE ENTRADA
# ============================================================

if __name__ == "__main__":
    main()