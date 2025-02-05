import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import pydirectinput
import pyautogui
import time
import random
import pygetwindow as gw
import cv2
import numpy as np
from PIL import Image, ImageTk
import threading
from pynput import mouse, keyboard as pynput_keyboard
from pynput.keyboard import Key, Controller as KeyboardController
import os
import re
from datetime import datetime

try:
    import pytesseract
except ImportError:
    pytesseract = None

# --- Helper for key conversion during playback ---
def convert_key_str(key_str):
    """
    Converts a stored key string back to a key value.
    For special keys, returns the appropriate pynput Key value.
    For normal keys, returns the character.
    """
    if key_str.startswith("Key."):
        key_name = key_str.split(".")[1]
        try:
            return getattr(Key, key_name)
        except AttributeError:
            return key_str
    else:
        return key_str.strip("'")

# --- Macro System (for automation) ---
class ImageMacroSystem:
    def __init__(self, templates, log_message):
        self.templates = templates
        self.attempts = 0
        self.log_message = log_message

    def execute(self, game_window):
      return None

    def detect_text(self, image, pattern):
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if pytesseract is None:
            self.log_message("Tesseract OCR is not available.", "ERROR")
            return None
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            text = pytesseract.image_to_string(gray)
            if not text.strip():  # Check if the extracted text is empty
                self.log_message("No text detected in the image.", "INFO")
                return None
            match = re.search(pattern, text)
            if match:
                self.log_message(f"Detected text matching pattern '{pattern}': {match.group()}")
                return match.groups()
            self.log_message(f"No text matching pattern '{pattern}' found.")
            return None
        except Exception as e:
            self.log_message(f"Error during text detection: {str(e)}", "ERROR")
            return None

    def get_screenshot(self, game_window):
        try:
            self.log_message("Capturing screenshot...")
            screenshot = pyautogui.screenshot(region=(game_window.left, game_window.top, game_window.width, game_window.height))
            screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            self.log_message("Screenshot captured successfully.")
            return screenshot
        except Exception as e:
            self.log_message(f"Error capturing screenshot: {str(e)}", "ERROR")
            return None

# --- Main Application ---
class AutoBotApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("480x700")  # Adjusted for vertical layout
        self.running = threading.Event()  # Use threading.Event for thread safety
        self.recording = False
        self.preview_running = False
        self.game_window = None
        self.templates = {}
        self.macro_system = None
        self.k_listener = None
        self.m_listener = None
        self.recorded_macro = []
        self.loaded_macros = {}
        self.record_start_time = None
        self.playback_speed = 1.0
        self.roi_start = None
        self.roi_end = None
        self.roi_rect = None
        self.setup_ui()
        self.load_config()
        self.update_window_list()
        # self.root.after(1000, self.check_game_status)

    def setup_ui(self):
        self.root.title("DLS macros")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        # Main Frame
        main_frame = ttk.Frame(self.root, padding=5)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=0)  # Logs section
        main_frame.columnconfigure(0, weight=1)

        # Notebook for Tabs (Automation, Configuration, About)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        # Automation Tab
        self.automation_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.automation_tab, text="Automation")

        # Configuration Tab
        self.config_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.config_tab, text="Configuration")

        # About Tab
        self.about_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.about_tab, text="About")

        # Logs Frame (Below the Notebook)
        logs_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding=5)
        logs_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        logs_frame.rowconfigure(0, weight=1)
        logs_frame.columnconfigure(0, weight=1)

        # Scrollable Log Text Area
        log_container = ttk.Frame(logs_frame)
        log_container.grid(row=0, column=0, sticky="nsew")
        log_container.rowconfigure(0, weight=1)
        log_container.columnconfigure(0, weight=1)

        self.log_text = tk.Text(log_container, wrap=tk.WORD, state=tk.DISABLED, height=10)  # Limit height
        self.log_text.grid(row=0, column=0, sticky="nsew")

        # Vertical Scrollbar
        log_scrollbar = ttk.Scrollbar(log_container, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=log_scrollbar.set)

        # Log Controls
        log_controls = ttk.Frame(logs_frame)
        log_controls.grid(row=1, column=0, pady=5)
        ttk.Button(log_controls, text="Clear Log", command=self.clear_log).grid(row=0, column=0, padx=5)
        ttk.Button(log_controls, text="Save Log", command=self.save_log).grid(row=0, column=1, padx=5)

        # --- Automation Tab Layout ---
        top_frame = ttk.Frame(self.automation_tab, padding=5)
        top_frame.grid(row=0, column=0, sticky="ew")
        top_frame.columnconfigure(1, weight=1)
        ttk.Label(top_frame, text="Select Game Window:").grid(row=0, column=0, sticky="w")
        self.window_list = ttk.Combobox(top_frame)
        self.window_list.grid(row=0, column=1, sticky="ew", padx=5)
        self.window_list.bind("<<ComboboxSelected>>", self.on_window_select)
        ttk.Button(top_frame, text="Refresh", command=self.update_window_list).grid(row=0, column=2, padx=5)

        preview_frame = ttk.LabelFrame(self.automation_tab, text="Game Preview", padding=5)
        preview_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)
        self.preview_label = ttk.Label(preview_frame)
        self.preview_label.grid(row=0, column=0, sticky="nsew")
        preview_controls = ttk.Frame(preview_frame)
        preview_controls.grid(row=1, column=0, pady=5)
        self.preview_btn = ttk.Button(preview_controls, text="Start Preview", command=self.toggle_preview)
        self.preview_btn.grid(row=0, column=0, padx=5)
        ttk.Button(preview_controls, text="Load Templates", command=self.load_templates).grid(row=0, column=1, padx=5)

        # automation_ctrl_frame = ttk.LabelFrame(self.automation_tab, text="Automation Controls", padding=5)
        # automation_ctrl_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        # automation_ctrl_frame.columnconfigure(0, weight=1)
        # self.start_btn = ttk.Button(automation_ctrl_frame, text="Start Automation", command=None)
        # self.start_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        macro_frame = ttk.LabelFrame(self.automation_tab, text="Macro Controls", padding=5)
        macro_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        self.record_btn = ttk.Button(macro_frame, text="Record Macro", command=self.toggle_recording)
        self.record_btn.grid(row=0, column=0, padx=5, pady=5)
        self.play_btn = ttk.Button(macro_frame, text="Play Macro", command=self.play_macro)
        self.play_btn.grid(row=0, column=1, padx=5, pady=5)
        self.save_macro_btn = ttk.Button(macro_frame, text="Save Macro", command=self.save_macro_to_file)
        self.save_macro_btn.grid(row=0, column=2, padx=5, pady=5)
        self.load_macro_btn = ttk.Button(macro_frame, text="Load Macro", command=self.load_macro_from_file)
        self.load_macro_btn.grid(row=0, column=3, padx=5, pady=5)

        speed_frame = ttk.Frame(macro_frame)
        speed_frame.grid(row=1, column=0, columnspan=4, sticky="ew", pady=5)
        ttk.Label(speed_frame, text="Playback Speed:").grid(row=0, column=0, sticky="w")
        self.speed_slider = ttk.Scale(speed_frame, from_=0.5, to=3.0, orient=tk.HORIZONTAL, command=self.update_playback_speed)
        self.speed_slider.set(1.0)
        self.speed_slider.grid(row=0, column=1, sticky="ew", padx=5)
        speed_frame.columnconfigure(1, weight=1)

        lib_frame = ttk.Frame(macro_frame)
        lib_frame.grid(row=2, column=0, columnspan=4, sticky="ew", pady=5)
        ttk.Label(lib_frame, text="Macro Library:").grid(row=0, column=0, sticky="w")
        self.macro_listbox = tk.Listbox(lib_frame, height=4)
        self.macro_listbox.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5)
        lib_frame.columnconfigure(1, weight=1)
        ttk.Label(macro_frame, text="(Select a macro from the list to play it.)").grid(
            row=3, column=0, columnspan=4, sticky="w", padx=5
        )

        # --- Configuration Tab Layout ---
        config_frame = ttk.LabelFrame(self.config_tab, text="Image Templates", padding=5)
        config_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.template_list = tk.Listbox(config_frame, height=8)
        self.template_list.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        config_btn_frame = ttk.Frame(config_frame)
        config_btn_frame.grid(row=1, column=0, sticky="ew", pady=5)
        ttk.Button(config_btn_frame, text="Remove Selected", command=self.remove_template).grid(row=0, column=0, padx=5)

        ocr_frame = ttk.LabelFrame(self.config_tab, text="OCR Settings", padding=5)
        ocr_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        ttk.Label(ocr_frame, text="Tesseract Path:").grid(row=0, column=0, sticky="w")
        self.tesseract_entry = ttk.Entry(ocr_frame)
        self.tesseract_entry.grid(row=0, column=1, sticky="ew", padx=5)
        ocr_frame.columnconfigure(1, weight=1)

        # --- About Tab Layout ---
        about_frame = ttk.Frame(self.about_tab, padding=5)
        about_frame.grid(row=0, column=0, sticky="nsew")
        about_frame.rowconfigure(0, weight=1)
        about_frame.columnconfigure(0, weight=1)

        try:
            banner_image = Image.open("assets/banner.png")
            banner_image.thumbnail((780, 200))  # Resize to fit the window
            self.banner_photo = ImageTk.PhotoImage(banner_image)
            banner_label = ttk.Label(about_frame, image=self.banner_photo)
            banner_label.grid(row=0, column=0, pady=10)
        except FileNotFoundError:
            ttk.Label(about_frame, text="Banner image not found.", font=("Arial", 12)).grid(
                row=0, column=0, pady=10
            )

        about_text = (
            "DLS macros\n"
            "Version 0.0.1 (test)\n"
            "A Python-based automation tool for doomsday last survivors.\n"
            "For Update, visit our GitHub repository."
        )
        ttk.Label(about_frame, text=about_text, justify="center", font=("Arial", 10)).grid(
            row=1, column=0, pady=10
        )

    def update_playback_speed(self, value):
        try:
            self.playback_speed = float(value)
        except ValueError:
            self.playback_speed = 1.0

    # --- Utility Functions ---
    def log_message(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        print(f"[{level}] {log_entry.strip()}")

    def clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def save_log(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Text Files", "*.txt")]
        )
        if filename:
            with open(filename, "w") as f:
                f.write(self.log_text.get(1.0, tk.END))

    def load_config(self):
        # Placeholder for configuration loading if needed.
        pass

    def update_window_list(self):
        windows = [w.title for w in gw.getAllWindows() if w.title]
        self.window_list["values"] = windows
        if windows:
            self.window_list.current(0)
            self.game_window = self.get_selected_window()

    def get_selected_window(self):
        selected_title = self.window_list.get()
        if selected_title:
            try:
                return gw.getWindowsWithTitle(selected_title)[0]
            except IndexError:
                return None
        return None

    def on_window_select(self, event):
        self.game_window = self.get_selected_window()
        if self.game_window:
            self.log_message(f"Selected window: {self.game_window.title}")

    def toggle_preview(self):
        window = self.get_selected_window()
        if not window:
            self.log_message("No game window selected for preview", "ERROR")
            return
        self.preview_running = not self.preview_running
        self.preview_btn.config(text="Stop Preview" if self.preview_running else "Start Preview")
        if self.preview_running:
            threading.Thread(target=self.update_preview, daemon=True).start()

    def update_preview(self):
        while self.preview_running:
            self.capture_preview()
            time.sleep(0.2)

    def capture_preview(self):
        """
        Captures the game window screenshot, performs OCR, and displays the annotated image in the preview.
        """
        window = self.get_selected_window()
        if window:
            try:
                # Step 1: Capture the game window screenshot
                img = pyautogui.screenshot(region=(window.left, window.top, window.width, window.height))
                img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                # Step 2: Perform OCR with Tesseract
                if pytesseract:
                    # Ensure Tesseract path is set (if not already configured)
                    tesseract_path = self.tesseract_entry.get().strip()
                    if tesseract_path:
                        pytesseract.pytesseract.tesseract_cmd = tesseract_path

                    # Use pytesseract.image_to_data to get bounding boxes for detected text
                    data = pytesseract.image_to_data(img_cv, output_type=pytesseract.Output.DICT)
                    n_boxes = len(data['text'])

                    # Step 3: Draw rectangles around detected text
                    for i in range(n_boxes):
                        if int(data['conf'][i]) > 60:  # Confidence threshold
                            x, y, w, h = (
                                data['left'][i],
                                data['top'][i],
                                data['width'][i],
                                data['height'][i],
                            )
                            cv2.rectangle(img_cv, (x, y), (x + w, y + h), (0, 255, 0), 2)  # Green box

                # Step 4: Convert the annotated image back to PIL format
                img_annotated = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
                img_annotated.thumbnail((800, 600))  # Resize to fit the preview

                # Step 5: Display the annotated image in the preview label
                self.preview_image = ImageTk.PhotoImage(img_annotated)
                self.preview_label.config(image=self.preview_image)

            except Exception as e:
                self.log_message(f"Preview error: {str(e)}", "ERROR")
        else:
            self.log_message("No game window selected for preview", "ERROR")

    # --- Macro Recording & Playback Functions ---
    def load_templates(self):
        """
        Automatically load template images from the 'templates/' folder.
        """
        # Define the path to the templates folder
        templates_folder = os.path.join(os.getcwd(), "templates")

        # Check if the folder exists
        if not os.path.exists(templates_folder):
            self.log_message("Templates folder not found. Please create a 'templates/' folder and add your template images.", "ERROR")
            return

        # Get all supported image files in the folder
        supported_extensions = [".png", ".jpg", ".jpeg"]
        template_files = [
            f for f in os.listdir(templates_folder)
            if os.path.isfile(os.path.join(templates_folder, f)) and os.path.splitext(f)[1].lower() in supported_extensions
        ]

        if not template_files:
            self.log_message("No template images found in the 'templates/' folder.", "ERROR")
            return

        # Load each template image
        for file in template_files:
            # Normalize the file name to lowercase
            name = os.path.splitext(file)[0].lower()
            file_path = os.path.join(templates_folder, file)
            try:
                # Attempt to load the image using OpenCV
                template = cv2.imread(file_path)
                if template is None:
                    self.log_message(f"Failed to load template: {file} (invalid file or format)", "ERROR")
                    continue
                # Store the template in the dictionary with its normalized name
                self.templates[name] = template
                self.template_list.insert(tk.END, name)
                self.log_message(f"Successfully loaded template: {name}")
            except Exception as e:
                self.log_message(f"Error loading template: {file} ({str(e)})", "ERROR")

    def remove_template(self):
        selection = self.template_list.curselection()
        if selection:
            name = self.template_list.get(selection[0])
            del self.templates[name]
            self.template_list.delete(selection[0])
            self.log_message(f"Removed template: {name}")

    def start_recording_macro(self):
        self.recorded_macro = []
        self.record_start_time = time.time()

        def on_press(key):
            event = {
                "type": "key_press",
                "key": str(key),
                "time": time.time() - self.record_start_time,
            }
            self.recorded_macro.append(event)

        def on_release(key):
            event = {
                "type": "key_release",
                "key": str(key),
                "time": time.time() - self.record_start_time,
            }
            self.recorded_macro.append(event)

        def on_click(x, y, button, pressed):
            event = {
                "type": "mouse_click",
                "x": x,
                "y": y,
                "button": str(button),
                "pressed": pressed,
                "time": time.time() - self.record_start_time,
            }
            self.recorded_macro.append(event)

        def on_scroll(x, y, dx, dy):
            event = {
                "type": "mouse_scroll",
                "x": x,
                "y": y,
                "dx": dx,
                "dy": dy,
                "time": time.time() - self.record_start_time,
            }
            self.recorded_macro.append(event)

        self.k_listener = pynput_keyboard.Listener(on_press=on_press, on_release=on_release)
        self.m_listener = mouse.Listener(on_click=on_click, on_scroll=on_scroll)
        self.k_listener.start()
        self.m_listener.start()
        self.log_message("Macro recording started.")

    def stop_recording_macro(self):
        if self.k_listener:
            self.k_listener.stop()
            self.k_listener = None
        if self.m_listener:
            self.m_listener.stop()
            self.m_listener = None
        self.log_message(f"Macro recording stopped. {len(self.recorded_macro)} events recorded.")

    def toggle_recording(self):
        self.recording = not self.recording
        if self.recording:
            self.record_btn.config(text="Stop Recording")
            self.start_recording_macro()
        else:
            self.record_btn.config(text="Record Macro")
            self.stop_recording_macro()

    def play_macro(self):
        sel = self.macro_listbox.curselection()
        if sel:
            macro_name = self.macro_listbox.get(sel[0])
            events = self.loaded_macros.get(macro_name, [])
            if not events:
                self.log_message("Selected macro is empty.", "ERROR")
                return
        elif self.recorded_macro:
            events = self.recorded_macro
            macro_name = "Current Recorded Macro"
        else:
            self.log_message("No macro available. Please record or load a macro.", "ERROR")
            return
        self.log_message(f"Starting playback of macro: {macro_name}")
        threading.Thread(target=self._play_macro_thread, args=(events,), daemon=True).start()

    def _play_macro_thread(self, events):
        kb = KeyboardController()
        last_time = 0
        for event in events:
            delay = event["time"] - last_time
            if delay > 0:
                # Adjust delay based on playback speed multiplier.
                time.sleep(delay / self.playback_speed)
            last_time = event["time"]
            etype = event["type"]
            if etype == "key_press":
                key_val = convert_key_str(event["key"])
                try:
                    kb.press(key_val)
                except Exception as e:
                    self.log_message(f"Error playing key press {event['key']}: {e}", "ERROR")
            elif etype == "key_release":
                key_val = convert_key_str(event["key"])
                try:
                    kb.release(key_val)
                except Exception as e:
                    self.log_message(f"Error playing key release {event['key']}: {e}", "ERROR")
            elif etype == "mouse_click":
                x, y = event["x"], event["y"]
                button_str = event["button"]
                if "left" in button_str:
                    button = "left"
                elif "right" in button_str:
                    button = "right"
                elif "middle" in button_str:
                    button = "middle"
                else:
                    button = "left"
                if event["pressed"]:
                    pyautogui.mouseDown(x=x, y=y, button=button)
                else:
                    pyautogui.mouseUp(x=x, y=y, button=button)
            elif etype == "mouse_scroll":
                dy = event["dy"]
                pyautogui.scroll(dy)
        self.log_message("Macro playback finished.")

    def save_macro_to_file(self):
        if not self.recorded_macro:
            messagebox.showerror("Error", "No macro recorded to save.")
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON Files", "*.json")]
        )
        if filename:
            try:
                with open(filename, "w") as f:
                    json.dump(self.recorded_macro, f, indent=2)
                self.log_message(f"Macro saved to {filename}")
                macro_name = os.path.basename(filename)
                self.loaded_macros[macro_name] = self.recorded_macro.copy()
                self.macro_listbox.insert(tk.END, macro_name)
            except Exception as e:
                self.log_message(f"Error saving macro: {e}", "ERROR")

    def load_macro_from_file(self):
        filename = filedialog.askopenfilename(
            title="Select Macro File", filetypes=[("JSON Files", "*.json")]
        )
        if filename:
            try:
                with open(filename, "r") as f:
                    macro = json.load(f)
                macro_name = os.path.basename(filename)
                self.loaded_macros[macro_name] = macro
                self.macro_listbox.insert(tk.END, macro_name)
                self.log_message(f"Macro {macro_name} loaded.")
            except Exception as e:
                self.log_message(f"Error loading macro: {e}", "ERROR")

    # def check_game_status(self):
    #     if self.game_window and not self.game_window.isActive:
    #         self.stop_automation()
    #     self.root.after(1000, self.check_game_status)

    def on_closing(self):
        # self.stop_automation()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AutoBotApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()