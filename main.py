import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
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
from modules.ui import setup_ui

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
        pytesseract.pytesseract.tesseract_cmd = (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        )
        if pytesseract is None:
            self.log_message("Tesseract OCR is not available.", "ERROR")
            return None
        try:
            gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
            text = pytesseract.image_to_string(gray)
            if not text.strip():  # Check if the extracted text is empty
                self.log_message("No text detected in the image.", "INFO")
                return None
            match = re.search(pattern, text)
            if match:
                self.log_message(
                    f"Detected text matching pattern '{pattern}': {match.group()}"
                )
                return match.groups()
            self.log_message(f"No text matching pattern '{pattern}' found.")
            return None
        except Exception as e:
            self.log_message(f"Error during text detection: {str(e)}", "ERROR")
            return None

    def get_screenshot(self, game_window):
        try:
            self.log_message("Capturing screenshot...")
            screenshot = pyautogui.screenshot(
                region=(
                    game_window.left,
                    game_window.top,
                    game_window.width,
                    game_window.height,
                )
            )
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
        self.root.geometry("510x700")  # Adjusted for vertical layout
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

        # Add ROI-related attributes
        self.roi_start = None  # Start point of ROI selection
        self.roi_end = None  # End point of ROI selection
        self.roi_rect = None  # Tkinter rectangle object for drawing the ROI
        self.selected_roi = None  # Stores the final ROI coordinates

        setup_ui(self)
        self.load_config()
        self.update_window_list()
        self.resource_rois = {
            "food": None,  # Example: ROI for food tracking
            "wood": None,  # Example: ROI for wood tracking
        }
        self.tracked_values = {
            "food": None,
            "wood": None,
        }
        # self.root.after(1000, self.check_game_status)

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
        self.preview_btn.config(
            text="Stop Preview" if self.preview_running else "Start Preview"
        )
        if self.preview_running:
            threading.Thread(target=self.update_preview, daemon=True).start()

    def update_preview(self):
        while self.preview_running:
            self.capture_preview()
            time.sleep(0.2)

    def get_client_area(self, window):
        """
        Calculate the client area (game screen) dimensions of the given window.
        Returns (left, top, width, height) of the client area.
        """
        try:
            # Get the full window dimensions
            left, top, width, height = (
                window.left,
                window.top,
                window.width,
                window.height,
            )

            # Approximate title bar and border sizes
            # These values may need adjustment based on the operating system
            title_bar_height = 30  # Approximate height of the title bar
            border_width = 8  # Approximate width of the borders

            # Adjust the region to exclude the title bar and borders
            client_left = left + border_width
            client_top = top + title_bar_height
            client_width = width - 2 * border_width
            client_height = height - title_bar_height - border_width

            return client_left, client_top, client_width, client_height

        except Exception as e:
            self.log_message(f"Error calculating client area: {str(e)}", "ERROR")
            return left, top, width, height

    def capture_preview(self):
        """
        Captures the game window screenshot and displays it on the Canvas.
        """
        window = self.get_selected_window()
        if window:
            try:
                # Get the client area dimensions (excluding title bar and borders)
                client_left, client_top, client_width, client_height = (
                    self.get_client_area(window)
                )

                # Capture the full game window screenshot
                img = pyautogui.screenshot(
                    region=(client_left, client_top, client_width, client_height)
                )

                # Scale down the image for preview
                img.thumbnail((460, 320))
                self.preview_image = ImageTk.PhotoImage(img)

                # Clear the Canvas and display the new image
                self.preview_canvas.delete("all")  # Clear previous content
                self.preview_canvas.config(
                    width=img.width, height=img.height
                )  # Adjust Canvas size
                self.preview_canvas.create_image(
                    0, 0, anchor=tk.NW, image=self.preview_image
                )  # Display image

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
            self.log_message(
                "Templates folder not found. Please create a 'templates/' folder and add your template images.",
                "ERROR",
            )
            return

        # Get all supported image files in the folder
        supported_extensions = [".png", ".jpg", ".jpeg"]
        template_files = [
            f
            for f in os.listdir(templates_folder)
            if os.path.isfile(os.path.join(templates_folder, f))
            and os.path.splitext(f)[1].lower() in supported_extensions
        ]

        if not template_files:
            self.log_message(
                "No template images found in the 'templates/' folder.", "ERROR"
            )
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
                    self.log_message(
                        f"Failed to load template: {file} (invalid file or format)",
                        "ERROR",
                    )
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

        self.k_listener = pynput_keyboard.Listener(
            on_press=on_press, on_release=on_release
        )
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
        self.log_message(
            f"Macro recording stopped. {len(self.recorded_macro)} events recorded."
        )

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
            self.log_message(
                "No macro available. Please record or load a macro.", "ERROR"
            )
            return
        self.log_message(f"Starting playback of macro: {macro_name}")
        threading.Thread(
            target=self._play_macro_thread, args=(events,), daemon=True
        ).start()

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
                    self.log_message(
                        f"Error playing key press {event['key']}: {e}", "ERROR"
                    )
            elif etype == "key_release":
                key_val = convert_key_str(event["key"])
                try:
                    kb.release(key_val)
                except Exception as e:
                    self.log_message(
                        f"Error playing key release {event['key']}: {e}", "ERROR"
                    )
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

    def start_roi_selection(self, event):
        """Start selecting the ROI."""
        self.roi_start = (event.x, event.y)
        self.roi_rect = None

    def update_roi_selection(self, event):
        """
        Update the ROI rectangle as the user drags the mouse.
        """
        if self.roi_start:
            x1, y1 = self.roi_start
            x2, y2 = event.x, event.y
            if self.roi_rect:
                self.roi_canvas.delete(self.roi_rect)  # Clear previous rectangle
            self.roi_rect = self.roi_canvas.create_rectangle(
                x1, y1, x2, y2, outline="red", width=2
            )

    def end_roi_selection(self, event):
        """
        Finalize the ROI selection and validate its dimensions.
        """
        if self.roi_start:
            self.roi_end = (event.x, event.y)
            x1, y1 = self.roi_start
            x2, y2 = self.roi_end
            # Normalize coordinates to ensure top-left and bottom-right
            roi_x1, roi_y1 = min(x1, x2), min(y1, y2)
            roi_x2, roi_y2 = max(x1, x2), max(y1, y2)

            # Check if the ROI is too small
            if (
                roi_x2 - roi_x1 <= 10 or roi_y2 - roi_y1 <= 10
            ):  # Arbitrary threshold for "too small"
                self.log_message(
                    "Selected ROI is too small. Using the entire game window.",
                    "WARNING",
                )
                self.selected_roi = None
            else:
                self.selected_roi = (roi_x1, roi_y1, roi_x2, roi_y2)
                self.log_message(
                    f"Selected ROI: ({roi_x1}, {roi_y1}) -> ({roi_x2}, {roi_y2})"
                )

                # Capture and display the cropped ROI image
                window = self.get_selected_window()
                if window:
                    try:
                        img = pyautogui.screenshot(
                            region=(
                                window.left + roi_x1,
                                window.top + roi_y1,
                                roi_x2 - roi_x1,
                                roi_y2 - roi_y1,
                            )
                        )
                        img.thumbnail((480, 480))  # Resize for display
                        self.roi_image = ImageTk.PhotoImage(img)
                        self.roi_display_label.config(image=self.roi_image)
                    except Exception as e:
                        self.log_message(
                            f"Error capturing ROI image: {str(e)}", "ERROR"
                        )

            # Prompt user to associate the ROI with a resource
            resource = simpledialog.askstring(
                "Resource Selection", "Enter resource name (e.g., food, wood):"
            )
            if resource:
                self.resource_rois[resource.lower()] = (roi_x1, roi_y1, roi_x2, roi_y2)
                self.log_message(
                    f"ROI for '{resource}' set: ({roi_x1}, {roi_y1}) -> ({roi_x2}, {roi_y2})"
                )
            else:
                self.log_message("ROI selection canceled.")

            self.roi_start = None
            self.roi_end = None

    def show_roi_popup(self):
        """
        Show a popup window for ROI selection with a frozen preview.
        """
        if not self.game_window:
            self.log_message("No game window selected for ROI selection.", "ERROR")
            return

        # Capture the game window screenshot
        img = pyautogui.screenshot(
            region=(
                self.game_window.left,
                self.game_window.top,
                self.game_window.width,
                self.game_window.height,
            )
        )
        # TODO: make this more dynamic later.
        # for now we just following the game window size
        img.thumbnail((1280, 720))  # Scale down the preview to fit the popup window

        # Create a popup window
        self.roi_popup = tk.Toplevel(self.root)
        self.roi_popup.title("ROI Selection")
        self.roi_popup.geometry("800x600")  # Set the size of the popup
        self.roi_popup.resizable(False, False)

        # Center the popup window on the screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 800) // 2
        y = (screen_height - 600) // 2
        self.roi_popup.geometry(f"+{x}+{y}")

        # Add a Canvas for the preview
        self.roi_canvas = tk.Canvas(self.roi_popup, bg="gray", width=800, height=600)
        self.roi_canvas.pack(fill=tk.BOTH, expand=True)

        # Display the frozen preview image
        self.roi_preview_image = ImageTk.PhotoImage(img)
        self.roi_canvas.create_image(0, 0, anchor=tk.NW, image=self.roi_preview_image)

        # Bind mouse events for ROI selection
        self.roi_canvas.bind("<ButtonPress-1>", self.start_roi_selection)
        self.roi_canvas.bind("<B1-Motion>", self.update_roi_selection)
        self.roi_canvas.bind("<ButtonRelease-1>", self.end_roi_selection)

        # Add a Reset ROI button
        reset_button = ttk.Button(
            self.roi_popup, text="Reset ROI", command=self.reset_roi
        )
        reset_button.pack(pady=5)

        # Add a Done button to close the popup
        done_button = ttk.Button(
            self.roi_popup, text="Done", command=self.roi_popup.destroy
        )
        done_button.pack(pady=5)

    def reset_roi(self):
        """Reset the selected ROI."""
        self.selected_roi = None
        self.roi_start = None
        self.roi_end = None
        self.preview_canvas.delete("all")  # Clear the Canvas
        self.log_message("ROI selection reset.")

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
