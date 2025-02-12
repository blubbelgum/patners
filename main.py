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
from PIL import Image, ImageTk, ImageSequence
import threading
from pynput import mouse, keyboard as pynput_keyboard
from pynput.keyboard import Key, Controller as KeyboardController
import os
import re
import easyocr
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
    def __init__(self, templates, log_message, reader):
        self.templates = templates
        self.log_message = log_message
        self.reader = reader

    def detect_template(self, game_window, template_name):
        template = self.templates.get(template_name)
        if template is None:
            self.log_message(f"Template '{template_name}' not found.", "ERROR")
            return False
        #     return False
        screenshot = self.get_screenshot(game_window)
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        return np.max(result) > 0.8

    def detect_text(self, image, pattern):
        """
        Detect text in the given image using EasyOCR and match it against a regex pattern.
        """
        try:
            # Convert the image to grayscale (optional, but improves performance)
            gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)

            # Use EasyOCR to extract text
            results = self.reader.readtext(gray)

            # Combine all detected text into a single string
            detected_text = " ".join([result[1] for result in results])

            # Log the detected text for debugging
            self.log_message(f"Detected text: {detected_text}")

            # Match the detected text against the provided regex pattern
            match = re.search(pattern, detected_text)
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
            img = pyautogui.screenshot(
                region=(
                    game_window.left,
                    game_window.top,
                    game_window.width,
                    game_window.height,
                )
            )
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
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

        # Macro Controls
        self.macro_system = None
        self.k_listener = None
        self.m_listener = None
        self.recorded_macro = []
        self.loaded_macros = {}
        self.record_start_time = None
        self.playback_speed = 1.0
        self.setup_kill_switch()
        self.repeat_count_var = tk.IntVar(value=1)  # Default to 1 repetition
        # Initialize the macro system
        self.reader = easyocr.Reader(["en"])  # Add more languages if needed
        self.macro_system = ImageMacroSystem(
            self.templates, self.log_message, self.reader
        )

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

    def show_splash_screen(self, macro_name):
        """
        Show the splash screen as a popup window with the same geometry as the main window.
        """
        # Minimize the main application window
        self.root.iconify()

        # Create a new Toplevel window for the splash screen
        self.splash_popup = tk.Toplevel(self.root)
        self.splash_popup.title("Running Macro")

        # Get the geometry of the main window
        main_geometry = self.root.geometry()  # Format: "widthxheight+x+y"
        self.splash_popup.geometry(
            main_geometry
        )  # Apply the same geometry to the popup

        # Add GIF animation
        gif_path = "assets/loading.gif"  # Replace with your GIF path
        try:
            gif = Image.open(gif_path)
            frames = [
                ImageTk.PhotoImage(
                    frame.convert("RGBA").resize(
                        (200, int(200 * frame.height / frame.width))
                    )
                )
                for frame in ImageSequence.Iterator(gif)
            ]
            self.gif_label = ttk.Label(self.splash_popup)
            self.gif_label.pack(pady=20)
            self.animate_gif(frames, 0)
        except FileNotFoundError:
            ttk.Label(
                self.splash_popup, text="GIF not found.", font=("Arial", 16)
            ).pack(pady=20)

        # Add centered text for the macro name and latest log
        ttk.Label(
            self.splash_popup, text=f"Running Macro: {macro_name}", font=("Arial", 12)
        ).pack(pady=10)
        self.splash_log_label = ttk.Label(
            self.splash_popup, text="Latest Log: Waiting...", font=("Arial", 10)
        )
        self.splash_log_label.pack(pady=10)

        # Ensure the popup closes when the macro finishes
        self.splash_popup.protocol(
            "WM_DELETE_WINDOW", lambda: None
        )  # Disable manual closing

    def animate_gif(self, frames, index):
        """
        Animate the GIF by cycling through its frames.
        """
        self.gif_label.config(image=frames[index])
        self.root.after(
            100, lambda: self.animate_gif(frames, (index + 1) % len(frames))
        )

    def restore_main_frame(self):
        """
        Restore the main application window and close the splash screen popup.
        """
        if hasattr(self, "splash_popup"):
            self.splash_popup.destroy()  # Close the splash screen popup
        self.root.deiconify()  # Restore the main application window

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

        # Update the splash screen log if it's visible
        if hasattr(self, "splash_log_label"):
            self.splash_log_label.config(text=f"Latest Log: {message}")

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
            self.window_list.current(0)  # Use set method instead of current
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
        Captures the game window screenshot, performs OCR using EasyOCR,
        and displays the image with bounding boxes on the Canvas.
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

                # Convert the image to OpenCV format for OCR processing
                img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

                # Perform OCR using EasyOCR
                results = self.reader.readtext(img_cv)

                # Draw bounding boxes around detected text
                for result in results:
                    bbox, text, confidence = result
                    top_left = tuple(map(int, bbox[0]))
                    bottom_right = tuple(map(int, bbox[2]))
                    cv2.rectangle(img_cv, top_left, bottom_right, (0, 255, 0), 2)

                # Convert the annotated image back to PIL format
                img_annotated = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))

                # Scale down the image for preview
                img_annotated.thumbnail((460, 320))

                # Update the preview canvas with the annotated image
                self.preview_image = ImageTk.PhotoImage(img_annotated)
                self.preview_canvas.delete("all")  # Clear previous content
                self.preview_canvas.config(
                    width=img_annotated.width, height=img_annotated.height
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
            # Ignore clicks within the application window
            app_window = gw.getWindowsWithTitle(self.root.title())
            if app_window:
                app_window = app_window[0]
                if (
                    app_window.left <= x <= app_window.left + app_window.width
                    and app_window.top <= y <= app_window.top + app_window.height
                ):
                    return  # Ignore clicks within the app window

            # Record valid clicks
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

        # Show splash screen
        self.show_splash_screen(macro_name)
        self.running.set()  # Set the running flag to True
        # Start macro playback in a thread
        threading.Thread(
            target=self._play_macro_with_repeat, args=(events,), daemon=True
        ).start()

    def stop_macro_playback(self):
        """
        Stop macro playback safely.
        """
        self.running.clear()  # Stop any running threads
        self.preview_running = False
        self.recording = False
        if self.k_listener:
            self.k_listener.stop()
        if self.m_listener:
            self.m_listener.stop()
        self.restore_main_frame()  # Restore the main application frame

    def _play_macro_with_repeat(self, events):
        """
        Play back a macro with optional repetitions.
        Handles both finite and infinite repeats.
        """
        repeat_count = self.repeat_count_var.get()
        for _ in range(repeat_count):
            if not self.running.is_set():  # Check if playback should stop
                break
            self._play_macro_thread(events)
        if self.repeat_infinite_var.get():
            while self.running.is_set():
                self._play_macro_thread(events)

        # Restore the main frame after playback ends (TODO: test this)
        self.restore_main_frame()

    def _play_macro_thread(self, events):
        """
        Play back a macro with delays between actions.
        Checks for the kill switch during playback.
        """
        kb = KeyboardController()
        last_time = 0
        for event in events:
            if not self.running.is_set():  # Check if the kill switch was activated
                self.log_message("Macro playback stopped by user.")
                return

            delay = event["time"] - last_time
            if delay > 0:
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
                button = (
                    "left"
                    if "left" in button_str
                    else "right" if "right" in button_str else "middle"
                )
                if event["pressed"]:
                    pyautogui.mouseDown(x=x, y=y, button=button)
                else:
                    pyautogui.mouseUp(x=x, y=y, button=button)
            elif etype == "mouse_scroll":
                dy = event["dy"]
                pyautogui.scroll(dy)

        self.log_message("Macro playback finished.")

    def setup_kill_switch(self):
        """
        Set up a global hotkey to stop macro playback using the Windows key.
        """

        def on_press(key):
            try:
                if key == Key.cmd:  # Check for Windows key
                    self.log_message("Kill switch activated. Stopping macro playback.")
                    self.stop_macro_playback()
            except AttributeError:
                pass

        self.kill_switch_listener = pynput_keyboard.Listener(on_press=on_press)
        self.kill_switch_listener.start()

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

    def conditional_play_macro(self, events):
        """
        Play a macro with conditional execution based on screen content.
        """
        for event in events:
            if event.get("condition"):
                template_name = event["condition"].get("template")
                text_pattern = event["condition"].get("text")

                screenshot = self.macro_system.get_screenshot(self.game_window)
                if template_name and not self.macro_system.detect_template(
                    screenshot, template_name
                ):
                    continue  # Skip this action if the template is not found
                if text_pattern and not self.macro_system.detect_text(
                    screenshot, text_pattern
                ):
                    continue  # Skip this action if the text pattern is not found

            # Execute the action
            self._execute_macro_event(event)

    def click_template(self, game_window, template_name):
        """
        Click on a detected template image.
        """
        template = self.templates.get(template_name)
        if not template:
            self.log_message(f"Template '{template_name}' not found.", "ERROR")
            return False

        screenshot = self.macro_system.get_screenshot(game_window)
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > 0.8:  # Confidence threshold
            x = game_window.left + max_loc[0] + template.shape[1] // 2
            y = game_window.top + max_loc[1] + template.shape[0] // 2
            pyautogui.click(x, y)
            return True

        self.log_message(f"Failed to click template '{template_name}'.")
        return False

    def get_arrow_region(self, game_window):
        """
        Calculate the region near the arrow image for OCR.
        """
        arrow_template = "arrow"
        screenshot = self.macro_system.get_screenshot(game_window)
        template = self.templates.get(arrow_template)
        if template is None:
            self.log_message("Arrow template not loaded.", "ERROR")
            return None

        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_loc = cv2.minMaxLoc(result)

        # Define a region around the arrow (adjust offsets as needed)
        arrow_x, arrow_y = max_loc
        offset_x, offset_y = 50, 50  # Offset from the arrow position
        region_width, region_height = 200, 50  # Size of the region

        return (
            game_window.left + arrow_x - offset_x,
            game_window.top + arrow_y - offset_y,
            region_width,
            region_height,
        )

    def auto_farm_macro(self):
        """
        Auto-farm macro preset using OCR and image recognition.
        """
        self.log_message("Starting auto-farm macro...")
        game_window = self.get_selected_window()
        if not game_window:
            self.log_message("No game window selected.", "ERROR")
            return

        # Step 1: Check for the arrow image
        arrow_template = "arrow"  # Template name for the arrow image
        if not self.macro_system.detect_template(game_window, arrow_template):
            self.log_message("Arrow image not found. Stopping macro.")
            return
        self.log_message(
            "Arrow image detected. Capturing game window for text extraction..."
        )

        # Step 2: Capture the entire game window (excluding title bar and borders)
        try:
            # Get the client area dimensions (excluding title bar and borders)
            client_left, client_top, client_width, client_height = self.get_client_area(
                game_window
            )

            # Capture the screenshot of the client area
            screenshot = pyautogui.screenshot(
                region=(client_left, client_top, client_width, client_height)
            )
            # export screenshot for debugging
            gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)

            # Save the screenshot for debugging with the bounding box on text region
            cv2.imwrite("screenshot.png", gray)
            cv2.rectangle(
                gray,
                (client_left, client_top),
                (client_left + client_width, client_top + client_height),
                (0, 255, 0),
                2,
            )
            cv2.imwrite("screenshot_bbox.png", gray)

            # Perform OCR on the screenshot
            pytesseract.pytesseract.tesseract_cmd = (
                r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            )
            text = pytesseract.image_to_string(gray)
            match = re.search(
                r"(\d)/5", text
            )  # Look for patterns like "1/5", "2/5", etc.

            if not match:
                self.log_message("No squad count text detected in the game window.")
                return

            current_squads, total_squads = int(match.group(1)), 5
            available_squads = total_squads - current_squads

            if available_squads <= 0:
                self.log_message(
                    f"No squads available for farming ({current_squads}/5). Stopping macro."
                )
                return

            self.log_message(f"{available_squads} squads available for farming.")
        except Exception as e:
            self.log_message(f"Error during text detection: {str(e)}", "ERROR")
            return

        # Step 3: Check for the region image and click if it exists
        region_image_template = "region_image"  # Template name for the region image
        if self.macro_system.detect_template(game_window, region_image_template):
            self.log_message("Region image detected. Clicking...")
            self.click_template(game_window, region_image_template)
        else:
            self.log_message("Region image not found. Skipping click.")

        # Step 4: Perform farming actions (e.g., repeat based on available squads)
        for i in range(available_squads):
            self.log_message(f"Farming with squad {i + 1}...")
            # Simulate farming actions here (e.g., clicks, key presses)
            time.sleep(1)  # Simulate delay between actions

        self.log_message("Auto-farm macro completed.")

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
            if roi_x2 - roi_x1 <= 10 or roi_y2 - roi_y1 <= 10:  # Arbitrary threshold
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
                    self.log_message(f"Error capturing ROI image: {str(e)}", "ERROR")

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
        client_left, client_top, client_width, client_height = self.get_client_area(
            self.game_window
        )
        img = pyautogui.screenshot(
            region=(client_left, client_top, client_width, client_height)
        )

        # Create a popup window
        self.roi_popup = tk.Toplevel(self.root)
        self.roi_popup.title("ROI Selection")

        # Set the popup size to match the client area dimensions
        self.roi_popup.geometry(f"{client_width}x{client_height + 80}")
        self.roi_popup.resizable(False, False)

        # Center the popup window on the screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - client_width) // 2
        y = (screen_height - client_height) // 2
        self.roi_popup.geometry(f"+{x}+{y}")

        # Add a Canvas for the preview
        self.roi_canvas = tk.Canvas(
            self.roi_popup, bg="gray", width=client_width, height=client_height
        )
        self.roi_canvas.pack(fill=tk.BOTH, expand=True)

        # Display the screenshot in the Canvas
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

        # Add a Done button to save the ROI and close the popup
        done_button = ttk.Button(
            self.roi_popup, text="Done", command=self.save_roi_and_close_popup
        )
        done_button.pack(pady=5)

    def reset_roi(self):
        """Reset the selected ROI."""
        self.selected_roi = None
        self.roi_start = None
        self.roi_end = None
        self.roi_canvas.delete("all")  # Clear the Canvas
        self.roi_canvas.create_image(0, 0, anchor=tk.NW, image=self.roi_preview_image)
        self.log_message("ROI selection reset.")

    def save_roi_and_close_popup(self):
        """
        Save the selected ROI and close the ROI selection popup.
        """
        if self.selected_roi:
            # Prompt the user to associate the ROI with a resource
            resource = simpledialog.askstring(
                "Resource Selection", "Enter resource name (e.g., food, wood):"
            )
            if resource:
                self.resource_rois[resource.lower()] = self.selected_roi
                self.log_message(f"ROI for '{resource}' set: {self.selected_roi}")
            else:
                self.log_message("ROI selection canceled.")
        else:
            self.log_message("No ROI selected.")

        # Close the popup
        self.roi_popup.destroy()

    def on_closing(self):
        # self.stop_automation()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AutoBotApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
