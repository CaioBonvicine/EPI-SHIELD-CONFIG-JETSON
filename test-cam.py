import cv2

print("Testando a câmera na porta 0 com Video4Linux2...")

# cv2.CAP_V4L2 força o OpenCV a usar o controlador nativo do Linux
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

if not cap.isOpened():
    print("ERRO TIPO A: O sistema operacional bloqueou o acesso à câmera (falta de permissões ou câmera em uso).")
else:
    ret, frame = cap.read()
    if ret:
        print("SUCESSO: O OpenCV conseguiu ler a imagem fisicamente!")
    else:
        print("ERRO TIPO B: A câmera abriu, mas enviou uma imagem vazia ou corrompida.")

    cap.release()