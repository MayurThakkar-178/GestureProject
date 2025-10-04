import cv2
import mediapipe as mp
import pyautogui
import math
import time

# -------------------- Tunables --------------------
CAM_W, CAM_H = 640, 480

PINCH_START_THR = 0.03   # start drag/scroll if thumb–index distance < this
PINCH_END_THR   = 0.05   # stop drag/scroll if thumb–index distance > this
SCROLL_DELTA_THR = 0.04  # how far (normalized) hand must move to trigger a scroll step
SCROLL_STEP = 60         # pixels per scroll tick
SMOOTHING = 5            # lower = snappier, higher = smoother

# -------------------- Setup ----------------------
pyautogui.FAILSAFE = False  # so you don't accidentally lock at screen corners

screen_w, screen_h = pyautogui.size()

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.6
)
mp_draw = mp.solutions.drawing_utils

# States
dragging = False
scrolling = False
initial_scroll_y = None

# For smoothing cursor movement
prev_x, prev_y = 0, 0

# FPS
prev_time = 0

def dist(p1, p2):
    return math.hypot(p1.x - p2.x, p1.y - p2.y)

try:
    print("✅ Gesture controller started. Press 'q' or Ctrl+C to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        if results.multi_hand_landmarks:
            hand = results.multi_hand_landmarks[0]
            lm = hand.landmark

            index_tip = lm[8]
            thumb_tip = lm[4]
            index_base = lm[5]
            pinky_base = lm[17]

            # Cursor position (screen coords)
            sx = int(index_tip.x * screen_w)
            sy = int(index_tip.y * screen_h)

            # Smooth movement
            cur_x = prev_x + (sx - prev_x) // SMOOTHING
            cur_y = prev_y + (sy - prev_y) // SMOOTHING
            pyautogui.moveTo(cur_x, cur_y)
            prev_x, prev_y = cur_x, cur_y

            # Draw hand & pointer on the camera frame
            mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)
            cx, cy = int(index_tip.x * CAM_W), int(index_tip.y * CAM_H)
            cv2.circle(frame, (cx, cy), 10, (255, 0, 255), cv2.FILLED)

            # Pinch distance
            pinch_d = dist(index_tip, thumb_tip)

            # ---------------- Drag & Drop ----------------
            if pinch_d < PINCH_START_THR and not dragging and not scrolling:
                pyautogui.mouseDown()
                dragging = True
                print("🟡 Dragging started")
            elif pinch_d > PINCH_END_THR and dragging:
                pyautogui.mouseUp()
                dragging = False
                print("🟢 Dropped")

            # ---------------- Scroll (pinch + vertical hand movement) -------------
            # Scroll using pinch + hand up/down movement
            hand_center_y = lm[9].y  # more stable scroll anchor (middle finger MCP)
            if pinch_d < PINCH_START_THR and not dragging:
                if not scrolling:
                    scrolling = True
                    initial_scroll_y = hand_center_y
                    print("🔵 Scroll mode ON")
                else:
                    delta_y = hand_center_y - initial_scroll_y
                    if delta_y > SCROLL_DELTA_THR:
                        pyautogui.scroll(-SCROLL_STEP)
                        initial_scroll_y = hand_center_y
                    elif delta_y < -SCROLL_DELTA_THR:
                        pyautogui.scroll(SCROLL_STEP)
                        initial_scroll_y = hand_center_y
            elif pinch_d > PINCH_END_THR and scrolling:
                scrolling = Fals
                initial_scroll_y = None
                print("🔵 Scroll mode OFF")


        # ---------------- FPS ----------------
        cur_time = time.time()
        fps = int(1 / (cur_time - prev_time)) if prev_time else 0
        prev_time = cur_time
        cv2.putText(frame, f'FPS: {fps}', (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

        # ---------------- Show frame ----------------
        cv2.imshow("Gesture Control", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("🛑 'q' pressed — exiting...")
            break

except KeyboardInterrupt:
    print("\n🛑 Ctrl+C detected — exiting...")

finally:
    print("📸 Releasing camera & cleaning up...")
    cap.release()
    cv2.destroyAllWindows()
    print("✅ Done.")
