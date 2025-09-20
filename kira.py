import cv2
import mediapipe as mp
import serial
import time
import math
from collections import deque

# Inicialização do MediaPipe Hands com parâmetros ajustados
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.6
)
mp_draw = mp.solutions.drawing_utils

# Inicia câmera
video = cv2.VideoCapture(0)

# Conecta com o Arduino (ajuste a porta se necessário)
arduino = serial.Serial('COM3', 9600, timeout=1)
time.sleep(2)

# Último gesto enviado e histórico de gestos para filtro
ultimo_gesto = None
historico_gestos = deque(maxlen=3)  # Requer 3 repetições para confirmar gesto

# Função auxiliar: verifica se dedo está levantado (exceto polegar)
def dedo_levantado(ponto_topo, ponto_base):
    return ponto_topo[1] < ponto_base[1]

# Função auxiliar: calcula distância euclidiana entre dois pontos
def distancia(p1, p2):
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

# Loop principal
while True:
    check, img = video.read()
    if not check:
        print("Falha na captura da imagem")
        break

    img = cv2.flip(img, 1)
    img = cv2.GaussianBlur(img, (3, 3), 0)  # Aplica blur
    h, w, _ = img.shape
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)

    gesto_atual = None

    if results.multi_hand_landmarks:
        for points, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            mp_draw.draw_landmarks(img, points, mp_hands.HAND_CONNECTIONS)

            label = handedness.classification[0].label
            score = handedness.classification[0].score

            pontos = [(int(lm.x * w), int(lm.y * h)) for lm in points.landmark]

            # Polegar → corrigido para 1 = aberto, 0 = fechado
            if label == "Right":
                polegar_aberto = pontos[4][0] < pontos[3][0]
            else:  # Left
                polegar_aberto = pontos[4][0] > pontos[3][0]

            indicador_aberto = dedo_levantado(pontos[8], pontos[6])
            medio_aberto = dedo_levantado(pontos[12], pontos[10])
            anelar_aberto = dedo_levantado(pontos[16], pontos[14])
            minimo_aberto = dedo_levantado(pontos[20], pontos[18])

            polegar_cima = pontos[4][1] < pontos[2][1]
            polegar_baixo = pontos[4][1] > pontos[2][1]

            outros_abaixados = all(pontos[i][1] > pontos[i - 2][1] for i in [8, 12, 16, 20])
            todos_dedos_levantados = all(pontos[i][1] < pontos[i - 2][1] for i in [8, 12, 16, 20])

            medio_fechado = not medio_aberto
            anelar_fechado = not anelar_aberto
            minimo_fechado = not minimo_aberto

            # ---------------- Reconhecimento de gestos ----------------
            if polegar_cima and outros_abaixados:
                gesto_atual = "J"
                cv2.putText(img, "JOINHA!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 3)

            elif polegar_baixo and outros_abaixados:
                gesto_atual = "D"
                cv2.putText(img, "DESGOSTEI!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)

            elif todos_dedos_levantados:
                gesto_atual = "E"
                cv2.putText(img, "ESPERE!", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 0), 3)

            # L → polegar aberto + indicador aberto
            elif polegar_aberto and indicador_aberto:
                gesto_atual = "L"
                cv2.putText(img, "L!", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 255), 3)

            # Apenas dedo do meio levantado
            elif medio_aberto and not indicador_aberto and not anelar_aberto and not minimo_aberto and not polegar_aberto:
                gesto_atual = "M"
                cv2.putText(img, "Pode não", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 255), 3)

            # OK → polegar e indicador juntos + outros levantados
            elif distancia(pontos[4], pontos[8]) < 40 and medio_aberto and anelar_aberto and minimo_aberto:
                gesto_atual = "O"
                cv2.putText(img, "OK!", (50, 400), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 165, 255), 3)

            # Mostra se é mão direita ou esquerda
            cv2.putText(img, f"{label} ({score:.2f})",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 255, 0), 2, cv2.LINE_AA)

            # Debug: mostra quais dedos estão abertos (1) ou fechados (0)
            debug_text = f"T:{int(polegar_aberto)} I:{int(indicador_aberto)} " \
                         f"M:{int(medio_aberto)} A:{int(anelar_aberto)} m:{int(minimo_aberto)}"
            cv2.putText(img, debug_text, (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (255, 255, 255), 2)

    # ------------------ Filtro de estabilidade ------------------
    if gesto_atual:
        historico_gestos.append(gesto_atual)
        if historico_gestos.count(gesto_atual) == historico_gestos.maxlen:
            if gesto_atual != ultimo_gesto:
                arduino.write(gesto_atual.encode())
                print(f"Gesto estável enviado: {gesto_atual}")
                ultimo_gesto = gesto_atual
    else:
        historico_gestos.clear()

    # Mostra a imagem
    cv2.imshow("Imagem", img)

    # Sai com ESC
    if cv2.waitKey(1) & 0xFF == 27:
        break

# Finaliza
video.release()
cv2.destroyAllWindows()
