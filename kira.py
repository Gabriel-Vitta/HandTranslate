import cv2
import mediapipe as mp
import serial
import time

# Configuração do MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2)
mp_draw = mp.solutions.drawing_utils

# Inicializa câmera
video = cv2.VideoCapture(0)

# Inicializa Arduino
arduino = serial.Serial('COM3', 9600, timeout=1)  
time.sleep(2)

# Último gesto enviado para o Arduino
ultimo_gesto = None

# Função auxiliar para verificar se dedo está levantado
def dedo_levantado(ponto_topo, ponto_base):
    return ponto_topo[1] < ponto_base[1]  # Y menor = mais acima

# Loop principal
while True:
    check, img = video.read()
    if not check:
        print("Falha na captura da imagem")
        break

    img = cv2.flip(img, 1)  # Espelha imagem
    h, w, _ = img.shape
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)

    gesto_atual = None  # Reset para cada frame

    if results.multi_hand_landmarks:
        for points, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            mp_draw.draw_landmarks(img, points, mp_hands.HAND_CONNECTIONS)

            # Identifica se é mão direita ou esquerda
            label = handedness.classification[0].label
            score = handedness.classification[0].score

            # Pega pontos da mão
            pontos = [(int(lm.x * w), int(lm.y * h)) for lm in points.landmark]

            # Verificações dos dedos
            polegar_cima = pontos[4][1] < pontos[2][1]
            polegar_baixo = pontos[4][1] > pontos[2][1]

            # Detecta se os outros dedos estão abaixados
            outros_abaixados = all(pontos[i][1] > pontos[i - 2][1] for i in [8, 12, 16, 20])

            # Detecta se todos os dedos estão levantados (exceto polegar)
            todos_dedos_levantados = all(pontos[i][1] < pontos[i - 2][1] for i in [8, 12, 16, 20])

            # Detecta dedo aberto ou fechado
            polegar_aberto = pontos[4][0] > pontos[3][0] if label == "Right" else pontos[4][0] < pontos[3][0]
            indicador_aberto = dedo_levantado(pontos[8], pontos[6])
            medio_aberto = dedo_levantado(pontos[12], pontos[10])
            anelar_aberto = dedo_levantado(pontos[16], pontos[14])
            minimo_aberto = dedo_levantado(pontos[20], pontos[18])

            medio_fechado = not medio_aberto
            anelar_fechado = not anelar_aberto
            minimo_fechado = not minimo_aberto

            # GESTOS -------------------------------------

            # JOINHA 👍
            if polegar_cima and outros_abaixados:
                gesto_atual = "J"
                cv2.putText(img, "JOINHA!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 3)

            # DESGOSTEI 👎
            elif polegar_baixo and outros_abaixados:
                gesto_atual = "D"
                cv2.putText(img, "DESGOSTEI!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)

            # ESPERE (mão aberta) ✋
            elif todos_dedos_levantados:
                gesto_atual = "E"
                cv2.putText(img, "ESPERE!", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 0), 3)

            # Letra "L" (polegar e indicador abertos, resto fechados) 🤟
            elif polegar_aberto and indicador_aberto and medio_fechado and anelar_fechado and minimo_fechado:
                gesto_atual = "L"
                cv2.putText(img, "L!", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 255), 3)

            # Exibe info da mão
            cv2.putText(img, f"{label} ({score:.2f})", 
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                        1, (0,255,0), 2, cv2.LINE_AA)

            # Envia gesto para Arduino, se mudou
            if gesto_atual and gesto_atual != ultimo_gesto:
                arduino.write(gesto_atual.encode())  # Envia caractere como byte
                print(f"Gesto enviado: {gesto_atual}")
                ultimo_gesto = gesto_atual

    # Mostra imagem
    cv2.imshow("Imagem", img)

    # Sai ao apertar ESC
    if cv2.waitKey(1) & 0xFF == 27:
        break

# Finaliza
video.release()
cv2.destroyAllWindows()
