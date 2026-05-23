import cv2
import mediapipe as mp
import math
import pyautogui
import subprocess
import json
import os
import threading
import tkinter as tk
from tkinter import messagebox, Toplevel, Label, Button, Entry, Text, ttk, Radiobutton, StringVar
from PIL import Image, ImageTk
import time
pyautogui.FAILSAFE = False
# MediaPipe ayarları
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands

# JSON dosyası
COMMANDS_FILE = "commands.json"
BUFFER_SIZE = 3  # Fare yumuşatma için

# ------------------ Hareket-Resim Eşleştirme ------------------
GESTURE_IMAGES = {
    "left el 4": "4_finger_left.png",
    "right el 4": "4_finger_right.png",
    "left el 3": "3_finger_left.png",
    "right el 3": "3_finger_right.png",
    "left el 2": "2_finger_left.png",
    "right el 2": "2_finger_right.png",
    "left el 1": "1_finger_left.png",
    "right el 1": "1_finger_right.png",
    "left el olumlu": "olumlu_finger_left.png",
    "right el olumlu": "olumlu_finger_right.png",
    "left el 5": "5_finger_left.png",
    "right el 5": "5_finger_right.png",
    "left el kapalı": "kapalı_finger_left.png",
    "right el kapalı": "kapalı_finger_right.png"
}

DEFAULT_COMMANDS = {
    "right el 1": {"type": "mouse", "action": "left_click"},
    "right el 2": {"type": "mouse", "action": "right_click"},
    "right el 3": {"type": "mouse", "action": "scroll_up"},
    "right el 4": {"type": "mouse", "action": "scroll_down"},
    "right el 5": {"type": "mouse", "action": "move"},
    "right el kapalı": {"type": "keyboard", "keys": "ctrl+c"},
    "right el olumlu": {"type": "keyboard", "keys": "ctrl+v"},
    "left el 1": {"type": "keyboard", "keys": "alt+tab"},
    "left el 2": {"type": "keyboard", "keys": "win+d"},
    "left el 3": {"type": "keyboard", "keys": "ctrl+z"},
    "left el 4": {"type": "keyboard", "keys": "ctrl+y"},
    "left el 5": {"type": "app", "value": "notepad.exe"},
    "left el kapalı": {"type": "app", "value": "calc.exe"},
    "left el olumlu": {"type": "app", "value": "mspaint.exe"}
}

class GestureApp:
    def __init__(self, root):
        self.root = root
        self.root.title("El Hareketi Kontrol Uygulaması")
        self.root.geometry("480x320")
        self.root.resizable(False, False)

        # Komutları yükle
        self.commands = self.load_commands()
        self.camera_is_active = False
        self.last_executed = {}  # gesture -> son çalıştırma zamanı
        self.cooldown = 2.0      # saniye (örn: 2 saniye bekle)
        # El bazlı buffer ve koordinatlar
        self.buffers = {"right": [], "left": []}
        self.avg_coords = {"right": (0, 0), "left": (0, 0)}

        self.create_main_menu()

    # ------------------ JSON Yükleme / Kaydetme ------------------
    def load_commands(self):
        if os.path.exists(COMMANDS_FILE):
            try:
                with open(COMMANDS_FILE, "r") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and data:
                        return data
            except:
                messagebox.showerror("Hata", "Komut dosyası bozuk. Varsayılana dönülüyor.")
        # Dosya yoksa veya bozuksa varsayılanları yükle
        self.save_default_commands()
        return DEFAULT_COMMANDS
    def save_commands(self):
        """Geçerli komutları JSON dosyasına kaydet"""
        with open(COMMANDS_FILE, "w") as f:
            json.dump(self.commands, f, indent=4)
            
            
            
    def remove_command(self, gesture_name, parent_window):
        if gesture_name in self.commands:
            if messagebox.askyesno("Onay", f"'{gesture_name}' komutu kaldırılsın mı?"):
                del self.commands[gesture_name]
                self.save_commands()
                messagebox.showinfo("Başarılı", f"'{gesture_name}' komutu başarıyla kaldırıldı.")
                parent_window.destroy() # Pencereyi kapat
                self.show_saved_gestures() # Listeyi yeniden yükle

    # ------------------ Ana Menü ------------------
    def create_main_menu(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(expand=True)

        Label(main_frame, text="Ana Menü", font=("Helvetica", 16, "bold")).pack(pady=10)

        Button(main_frame, text="Kontrolü Başlat", command=self.start_camera_threaded, width=35).pack(pady=5)
        Button(main_frame, text="Hareket Ekle", command=self.show_add_gesture_menu, width=35).pack(pady=5)
        Button(main_frame, text="Kayıtlı Hareketleri Görüntüle", command=self.show_saved_gestures, width=35).pack(pady=5)
        Button(main_frame, text="Komutları Sıfırla", command=self.reset_commands, width=35).pack(pady=5)
        Button(main_frame, text="Çıkış", command=self.root.destroy, width=35).pack(pady=5)

    # ------------------ Kamera ------------------
    def reset_commands(self):
        if messagebox.askyesno("Onay", "Komutlar varsayılana sıfırlansın mı?"):
            self.save_default_commands()
            self.commands = DEFAULT_COMMANDS.copy()
            messagebox.showinfo("Bilgi", "Komutlar varsayılana sıfırlandı.")

    def save_default_commands(self):
        with open(COMMANDS_FILE, "w") as f:
            json.dump(DEFAULT_COMMANDS, f, indent=4)

    def start_camera_threaded(self):
        if not self.camera_is_active:
            self.camera_is_active = True
            threading.Thread(target=self.camera, daemon=True).start()
        else:
            messagebox.showinfo("Bilgi", "Kamera zaten açık!")

    def camera(self):
        cap = cv2.VideoCapture(0)
        with mp_hands.Hands(model_complexity=0, min_detection_confidence=0.5, min_tracking_confidence=0.5) as hands:
            while cap.isOpened() and self.camera_is_active:
                success, image = cap.read()
                if not success:
                    continue

                image = cv2.flip(image, 1)
                image.flags.writeable = False
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                results = hands.process(image)
                image.flags.writeable = True
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

                if results.multi_hand_landmarks:
                    for hand_landmarks, hand_handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                        mp_drawing.draw_landmarks(
                            image, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                            mp_drawing_styles.get_default_hand_landmarks_style(),
                            mp_drawing_styles.get_default_hand_connections_style()
                        )
                        label = hand_handedness.classification[0].label.lower()  # right / left

                        # Parmak durumları
                        index_open = self.is_finger_open(hand_landmarks, 'INDEX_FINGER')
                        middle_open = self.is_finger_open(hand_landmarks, 'MIDDLE_FINGER')
                        ring_open = self.is_finger_open(hand_landmarks, 'RING_FINGER')
                        pinky_open = self.is_finger_open(hand_landmarks, 'PINKY')
                        thumb_open = self.thumb_status(hand_landmarks)

                        # Fare koordinatları
                        index_x = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].x * pyautogui.size()[0]
                        index_y = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y * pyautogui.size()[1]

                        # Gesture algılama
                        gesture = self.detect_gesture(label, index_open, middle_open, ring_open, pinky_open, thumb_open)
                        if gesture:
                            buffer = self.buffers[label]
                            buffer.append((index_x, index_y))
                            if len(buffer) > BUFFER_SIZE:
                                buffer.pop(0)

                            if len(buffer) == BUFFER_SIZE:
                                avg_x = sum(p[0] for p in buffer) / BUFFER_SIZE
                                avg_y = sum(p[1] for p in buffer) / BUFFER_SIZE
                                self.avg_coords[label] = (avg_x, avg_y)

                            self.run_command(gesture, label)

                cv2.imshow('Kamera - Q tuşuna basarak kapat', image)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.camera_is_active = False
                    break

        cap.release()
        cv2.destroyAllWindows()
        messagebox.showinfo("Bilgi", "Kamera kapatıldı.")

    # ------------------ Hareket Algılama ------------------
    def detect_gesture(self, label, index_open, middle_open, ring_open, pinky_open, thumb_open):
        gesture = None
        if index_open and middle_open and ring_open and pinky_open and not thumb_open:
            gesture = f"{label} el 4"
        elif index_open and middle_open and ring_open and not pinky_open and not thumb_open:
            gesture = f"{label} el 3"
        elif index_open and middle_open and not ring_open and not pinky_open and not thumb_open:
            gesture = f"{label} el 2"
        elif index_open and not middle_open and not ring_open and not pinky_open and not thumb_open:
            gesture = f"{label} el 1"
        elif index_open and middle_open and ring_open and pinky_open and thumb_open:
            gesture = f"{label} el 5"
        elif not index_open and not middle_open and not ring_open and not pinky_open and not thumb_open:
            gesture = f"{label} el kapalı"
        elif not index_open and not middle_open and not ring_open and not pinky_open and thumb_open:
            gesture = f"{label} el olumlu"
        return gesture

    # ------------------ Komut Çalıştır ------------------
    # ------------------ Komut Çalıştır ------------------
    # ------------------ Komut Çalıştır (EMA ile pürüzsüz fare) ------------------
    def run_command(self, gesture_name, hand_label):
            now = time.time()
            
            # Fare hareketi (move) için cooldown uygulanmamalı
            if self.commands.get(gesture_name, {}).get("action") == "move":
                cmd = self.commands.get(gesture_name)
                avg_x, avg_y = self.avg_coords[hand_label]
                if not hasattr(self, "ema_pos"):
                    self.ema_pos = (avg_x, avg_y)
                alpha = 0.3
                ema_x = self.ema_pos[0] * (1 - alpha) + avg_x * alpha
                ema_y = self.ema_pos[1] * (1 - alpha) + avg_y * alpha
                self.ema_pos = (ema_x, ema_y)
                pyautogui.moveTo(ema_x, ema_y, duration=0)
                return
    
            # Diğer tüm komutlar için cooldown kontrolü
            last_time = self.last_executed.get(gesture_name, 0)
            if now - last_time < self.cooldown:
                return
    
            self.last_executed[gesture_name] = now
            cmd = self.commands.get(gesture_name)
            if not cmd:
                return
    
            try:
                if cmd["type"] == "app":
                    subprocess.Popen(cmd["value"], shell=True)
                elif cmd["type"] == "mouse":
                    action = cmd["action"]
                    # Fare hareket eylemlerini burada tutma
                    if action == "left_click":
                        pyautogui.leftClick()
                    elif action == "right_click":
                        pyautogui.rightClick()
                    elif action == "scroll_up":
                        pyautogui.scroll(50)
                    elif action == "scroll_down":
                        pyautogui.scroll(-50)
                elif cmd["type"] == "keyboard":
                    pyautogui.hotkey(*cmd["keys"].split("+"))
            except Exception as e:
                print(f"Hata: {e}")




    # ------------------ Parmak Durumları ------------------
    def is_finger_open(self, hand_landmarks, finger):
        tip = hand_landmarks.landmark[getattr(mp_hands.HandLandmark, f"{finger}_TIP")]
        dip = hand_landmarks.landmark[getattr(mp_hands.HandLandmark, f"{finger}_DIP")]
        return tip.y < dip.y

    def thumb_status(self, hand_landmarks):
        wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
        thumb_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_MCP]
        thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]

        v1 = [thumb_mcp.x - wrist.x, thumb_mcp.y - wrist.y]
        v2 = [thumb_tip.x - thumb_mcp.x, thumb_tip.y - thumb_mcp.y]
        dot = v1[0]*v2[0] + v1[1]*v2[1]
        mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
        mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
        if mag1 * mag2 == 0: return False
        angle = math.degrees(math.acos(dot / (mag1 * mag2)))
        return angle < 30

    # ------------------ Hareket Ekle ------------------
    def show_add_gesture_menu(self):
        add_window = Toplevel(self.root)
        add_window.title("Hareket Ekle")
        add_window.geometry("500x500")
    
        Label(add_window, text="Yeni Hareket Ekle", font=("Helvetica", 14, "bold")).pack(pady=10)
    
        # Hareket seçimi
        gestures = list(GESTURE_IMAGES.keys())
        gesture_combobox = ttk.Combobox(add_window, values=gestures, state="readonly", width=47)
        gesture_combobox.set("right el 5")
        gesture_combobox.pack()
    
        # Resim gösterimi
        img_label = Label(add_window)
        img_label.pack(pady=10)
        self.add_gesture_image = None  
    
        def update_image(event=None):
            gesture_name = gesture_combobox.get()
            img_path = GESTURE_IMAGES.get(gesture_name)
            if img_path and os.path.exists(f"handimages/{img_path}"):
                img = Image.open(f"handimages/{img_path}").resize((100, 100))
                photo = ImageTk.PhotoImage(img)
                self.add_gesture_image = photo
                img_label.config(image=photo, text="")
            else:
                img_label.config(image="", text="[Resim yok]")
    
        gesture_combobox.bind("<<ComboboxSelected>>", update_image)
        update_image()
    
        # Komut tipi seçimi
        Label(add_window, text="Komut Tipi Seçin:").pack(pady=5)
        command_type = StringVar(value="app")
        Radiobutton(add_window, text="Uygulama", variable=command_type, value="app").pack(anchor="w", padx=20)
        Radiobutton(add_window, text="Fare", variable=command_type, value="mouse").pack(anchor="w", padx=20)
        Radiobutton(add_window, text="Klavye", variable=command_type, value="keyboard").pack(anchor="w", padx=20)
    
        # Dinamik giriş alanı
        input_frame = tk.Frame(add_window)
        input_frame.pack(pady=10)
    
        def update_input_widgets():
            for widget in input_frame.winfo_children():
                widget.destroy()
            cmd_type = command_type.get()
            if cmd_type == "app":
                Label(input_frame, text="Uygulama Yolu (örn: notepad.exe):").pack()
                self.value_entry = Entry(input_frame, width=50)
                self.value_entry.pack()
            elif cmd_type == "mouse":
                Label(input_frame, text="Fare Hareketi Seçin:").pack()
                mouse_actions = ["move", "left_click", "right_click", "scroll_up", "scroll_down"]
                self.value_entry = ttk.Combobox(input_frame, values=mouse_actions, state="readonly", width=47)
                self.value_entry.set("move")
                self.value_entry.pack()
            elif cmd_type == "keyboard":
                Label(input_frame, text="Tuş Kombinasyonu (örn: ctrl+c):").pack()
                self.value_entry = Entry(input_frame, width=50)
                self.value_entry.pack()
    
        command_type.trace("w", lambda *args: update_input_widgets())
        update_input_widgets()
    
        # Kaydet butonu
        def add_and_close():
            gesture_name = gesture_combobox.get().strip()
            cmd_type = command_type.get()
            cmd_value = self.value_entry.get().strip()
        
            if not gesture_name or not cmd_value:
                messagebox.showerror("Hata", "Lütfen tüm alanları doldurun.")
                return
        
            if cmd_type == "app":
                command_dict = {"type": "app", "value": cmd_value}
            elif cmd_type == "mouse":
                command_dict = {"type": "mouse", "action": cmd_value}
            elif cmd_type == "keyboard":
                command_dict = {"type": "keyboard", "keys": cmd_value}
            else:
                messagebox.showerror("Hata", "Geçersiz komut tipi.")
                return
        
            if gesture_name in self.commands:
                if not messagebox.askyesno("Onay", f"'{gesture_name}' zaten kayıtlı. Üzerine yazılsın mı?"):
                    return
        
            self.commands[gesture_name] = command_dict
            self.save_commands()
            messagebox.showinfo("Başarılı", f"'{gesture_name}' hareketi kaydedildi!")
            add_window.destroy()
        
        Button(add_window, text="Kaydet", command=lambda: (add_and_close(), self.show_saved_gestures()), width=20).pack(pady=20)


    # ------------------ Kayıtlı Hareketler ------------------
    def show_saved_gestures(self):
        info_window = Toplevel(self.root)
        info_window.title("Kayıtlı Hareketler")
        info_window.geometry("600x400")
    
        self.commands = self.load_commands()
        Label(info_window, text="Kayıtlı El Hareketleri", font=("Helvetica", 14, "bold")).pack(pady=10)
    
        if not self.commands:
            Label(info_window, text="Henüz kayıtlı hareket yok!", font=("Helvetica", 12)).pack(pady=20)
            return
    
        canvas = tk.Canvas(info_window)
        scrollbar = ttk.Scrollbar(info_window, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas)
    
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
    
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
    
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
        self.saved_images = {}  # referansları sakla
        for gesture, command in self.commands.items():
            frame = tk.Frame(scroll_frame, pady=5)
            frame.pack(fill="x")
    
            img_path = GESTURE_IMAGES.get(gesture)
            if img_path and os.path.exists(f"handimages/{img_path}"):
                img = Image.open(f"handimages/{img_path}").resize((80, 80))
                photo = ImageTk.PhotoImage(img)
                self.saved_images[gesture] = photo  # referans kaydet
                img_label = Label(frame, image=photo)
                img_label.pack(side="left", padx=5)
            else:
                Label(frame, text="[Resim yok]", width=10, height=5).pack(side="left", padx=5)
    
            info_text = f"{gesture}\nTipi: {command['type']}"
            if 'value' in command: info_text += f"\nDeğer: {command['value']}"
            elif 'action' in command: info_text += f"\nEylem: {command['action']}"
            elif 'keys' in command: info_text += f"\nTuşlar: {command['keys']}"
    
            Label(frame, text=info_text, justify="left").pack(side="left", padx=10)
            # --- Bu bölümü ekle ---
            Button(frame, text="Kaldır", 
                   command=lambda g=gesture: self.remove_command(g, info_window), 
                   fg="red").pack(side="right", padx=5)
            # --------------------

# ------------------ PROGRAM BAŞLANGICI ------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = GestureApp(root)
    root.mainloop()