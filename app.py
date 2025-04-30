from flask import Flask, render_template, Response
import cv2
import mediapipe as mp
import numpy as np
import pickle
import time
import threading

# Variables globales con protección de hilos
latest_frame = None
frame_lock = threading.Lock()
shared_vars_lock = threading.Lock()
hold_start_time = None
current_letter = ""
confirmed_phrase = ""
hold_duration_required = 3

app = Flask(__name__)

model_dict = pickle.load(open('./model.p', 'rb'))
model = model_dict['model']

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
    max_num_hands=1
)
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

labels_dict = {i: chr(65 + i) for i in range(26)}
labels_dict[26] = " "

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)  # Buffer más pequeño para reducir latencia

def camera_processing_thread():
    global latest_frame, hold_start_time, current_letter, confirmed_phrase
    
    while True:
        # Captura de frame
        ret, frame = cap.read()
        if not ret:
            break

        H, W, _ = frame.shape
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)
        data_aux, x_, y_ = [], [], []

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Dibujo de landmarks (manteniendo tu estilo)
                mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style()
                )

                # Procesamiento de landmarks (igual que tu versión)
                for i in range(len(hand_landmarks.landmark)):
                    x = hand_landmarks.landmark[i].x
                    y = hand_landmarks.landmark[i].y
                    x_.append(x)
                    y_.append(y)
                    data_aux.append(x - min(x_))
                    data_aux.append(y - min(y_))

            # Predicción (igual que tu versión)
            prediction = model.predict([np.asarray(data_aux)])
            predicted_character = labels_dict[int(prediction[0])]

            with shared_vars_lock:  # Protección para variables compartidas
                # Lógica de hold (igual que tu versión pero protegida)
                if predicted_character == current_letter:
                    if hold_start_time is None:
                        hold_start_time = time.time()
                    elapsed = time.time() - hold_start_time

                    # Dibujar temporizador
                    remaining = max(0, hold_duration_required - elapsed)
                    cv2.putText(frame, f"Holding: {predicted_character} ({remaining:.1f}s)", 
                                (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (156, 156, 156), 2)

                    # Barra de progreso
                    bar_length = int((elapsed / hold_duration_required) * (W - 40))
                    bar_length = min(bar_length, W - 40)
                    cv2.rectangle(frame, (20, 70), (20 + bar_length, 100), (156, 156, 156), -1)

                    # Confirmar letra
                    if elapsed >= hold_duration_required:
                        confirmed_phrase += " " if predicted_character == " " else predicted_character
                        print("✅ Added:", predicted_character)
                        hold_start_time = None
                        current_letter = ""
                else:
                    current_letter = predicted_character
                    hold_start_time = time.time()

                # Dibujar rectángulo y texto
                x1 = int(min(x_) * W) - 10
                y1 = int(min(y_) * H) - 10
                x2 = int(max(x_) * W) + 10
                y2 = int(max(y_) * H) + 10
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), 2)
                cv2.putText(frame, predicted_character, (x1, y1 - 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 3, cv2.LINE_AA)

        # Dibujar frase confirmada (protegida con lock)
        with shared_vars_lock:
            current_confirmed = confirmed_phrase
        
        cv2.rectangle(frame, (10, H - 60), (W - 10, H - 20), (255, 255, 255), -1)
        cv2.putText(frame, current_confirmed, (20, H - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2, cv2.LINE_AA)

        # Compartir frame procesado
        with frame_lock:
            _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            latest_frame = buffer.tobytes()

        # Pequeña pausa para evitar sobrecarga
        time.sleep(0.01)

# Iniciar el hilo de procesamiento
processing_thread = threading.Thread(target=camera_processing_thread, daemon=True)
processing_thread.start()

def gen_frames():
    while True:
        with frame_lock:
            frame = latest_frame if latest_frame is not None else b''
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video')
def video():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=False, threaded=True)