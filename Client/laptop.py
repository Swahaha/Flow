import cv2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import requests
from inference import get_model
import math

# === Roboflow model ===
model = get_model("swa-flow/2", api_key="I am not putting my api key here :)")

PI_STREAM_URL = "http://172.28.120.230:5000/video_feed"
PI_SERVO_URL = "http://172.28.120.230:5000/run-servo"

class InferenceApp:
    def __init__(self, window):
        self.window = window
        self.window.title("Laptop View :)")
        self.window.configure(bg="#f0f0f0")

        self.cap = cv2.VideoCapture(PI_STREAM_URL)
        self.running = True

        # === Video Feed ===
        self.video_label = tk.Label(window, bd=2, relief="sunken")
        self.video_label.grid(row=0, column=0, columnspan=4, padx=10, pady=10)

        # === Controls Frame ===
        control_frame = tk.Frame(window, bg="#f0f0f0")
        control_frame.grid(row=1, column=0, columnspan=4, pady=(0, 10))

        tk.Label(control_frame, text="PW:", bg="#f0f0f0", font=("Segoe UI", 10)).grid(row=0, column=0, padx=5)
        self.pw_entry = tk.Entry(control_frame, width=6, font=("Segoe UI", 10))
        self.pw_entry.insert(0, "1.3")
        self.pw_entry.grid(row=0, column=1, padx=5)

        tk.Label(control_frame, text="Delay:", bg="#f0f0f0", font=("Segoe UI", 10)).grid(row=0, column=2, padx=5)
        self.delay_entry = tk.Entry(control_frame, width=6, font=("Segoe UI", 10))
        self.delay_entry.insert(0, "1")
        self.delay_entry.grid(row=0, column=3, padx=5)

        self.hit_button = tk.Button(control_frame, text="Hit", width=12, command=self.send_servo_command, font=("Segoe UI", 10, "bold"), bg="#4CAF50", fg="white")
        self.hit_button.grid(row=1, column=0, columnspan=2, pady=10, padx=5)

        self.snapshot_button = tk.Button(control_frame, text="Snapshot", width=12, command=self.take_snapshot, font=("Segoe UI", 10, "bold"), bg="#2196F3", fg="white")
        self.snapshot_button.grid(row=1, column=2, columnspan=2, pady=10, padx=5)

        self.message_label = tk.Label(window, text="", font=("Segoe UI", 11, "bold"), bg="#f0f0f0", fg="#333")
        self.message_label.grid(row=2, column=0, columnspan=4, pady=10)

        self.attempt = 1
        self.last_instruction = None
        self.update_frame()

    def update_frame(self):
        if not self.running:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.window.after(10, self.update_frame)
            return

        self.current_frame = frame.copy()

        result = model.infer(frame, confidence=0.5)

        for response in result:
            for det in response.predictions:
                x, y = int(det.x), int(det.y)
                w, h = int(det.width), int(det.height)
                label = det.class_name
                conf = det.confidence

                cv2.rectangle(frame, (x - w // 2, y - h // 2), (x + w // 2, y + h // 2), (0, 255, 0), 2)
                cv2.putText(frame, f"{label} {conf:.2f}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

        img = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)

        self.window.after(10, self.update_frame)

    def send_servo_command(self):
        try:
            pw = float(self.pw_entry.get())
            delay = float(self.delay_entry.get())
            res = requests.post(PI_SERVO_URL, json={"pw": pw, "delay": delay})
            print("Servo response:", res.json())
        except Exception as e:
            print("Failed to send command:", e)

    def take_snapshot(self):
        result = model.infer(self.current_frame, confidence=0.5)

        discs, targets = [], []

        for response in result:
            for det in response.predictions:
                x, y = int(det.x), int(det.y)
                label = det.class_name

                if label == "Disc":
                    discs.append((x, y))
                elif label == "Targets":
                    targets.append((x, y))

        instruction = ""
        score_text = ""
        if len(discs) == 1 and len(targets) == 1:
            x_d, y_d = discs[0]
            x_t, y_t = targets[0]

            distance = math.sqrt((x_d - x_t)**2 + (y_d - y_t)**2)
            score_text = f"Score: {distance:.2f}"

            current_pw = float(self.pw_entry.get())
            current_delay = float(self.delay_entry.get())

            if distance < 50:
                instruction = "Hit correctly"
            elif (x_d <= x_t) and (y_d < (y_t-50)):
                instruction = "Hit earlier"
                self.delay_entry.delete(0, tk.END)
                self.delay_entry.insert(0, f"{max(current_delay - 0.05, 0):.2f}")
            elif (x_d > (x_t+50)) and (y_d >= y_t):
                instruction = "Hit later"
                self.delay_entry.delete(0, tk.END)
                self.delay_entry.insert(0, f"{current_delay + 0.05:.2f}")
            elif (x_d > x_t) and (y_d < y_t):
                instruction = "Hit harder"
                self.pw_entry.delete(0, tk.END)
                self.pw_entry.insert(0, f"{current_pw - 0.2:.2f}")
            elif (x_d < x_t) and (y_d > y_t):
                instruction = "Hit softer"
                self.pw_entry.delete(0, tk.END)
                self.pw_entry.insert(0, f"{max(current_pw + 0.05, 0):.2f}")
            

        self.message_label.config(text=f"Attempt {self.attempt}: {instruction}    {score_text}")
        self.attempt += 1

    def close(self):
        self.running = False
        self.cap.release()
        self.window.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = InferenceApp(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()