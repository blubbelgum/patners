import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageSequence


def setup_ui(self):
    # Main Window
    self.root.title("DLS macros")
    self.root.rowconfigure(0, weight=1)
    self.root.columnconfigure(0, weight=1)

    # Main Frame
    main_frame = ttk.Frame(self.root, padding=5)
    main_frame.grid(row=0, column=0, sticky="nsew")
    main_frame.rowconfigure(0, weight=1)
    main_frame.rowconfigure(1, weight=0)  # Logs section
    main_frame.columnconfigure(0, weight=1)

    # Scrollable Notebook Frame
    notebook_frame = ttk.Frame(main_frame)
    notebook_frame.grid(row=0, column=0, sticky="nsew")
    notebook_frame.rowconfigure(0, weight=1)
    notebook_frame.columnconfigure(0, weight=1)

    # Canvas for Scrollable Content
    canvas = tk.Canvas(notebook_frame)
    canvas.grid(row=0, column=0, sticky="nsew")

    # Scrollbar
    scrollbar = ttk.Scrollbar(notebook_frame, orient=tk.VERTICAL, command=canvas.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Inner Frame for Notebook
    inner_frame = ttk.Frame(canvas)
    canvas.create_window((0, 0), window=inner_frame, anchor="nw")

    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    inner_frame.bind("<Configure>", on_frame_configure)

    # Notebook for Tabs
    self.notebook = ttk.Notebook(inner_frame)
    self.notebook.pack(fill=tk.BOTH, expand=True)

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
    self.log_text = tk.Text(log_container, wrap=tk.WORD, state=tk.DISABLED, height=10)
    self.log_text.grid(row=0, column=0, sticky="nsew")

    # Vertical Scrollbar
    log_scrollbar = ttk.Scrollbar(
        log_container, orient=tk.VERTICAL, command=self.log_text.yview
    )
    log_scrollbar.grid(row=0, column=1, sticky="ns")
    self.log_text.config(yscrollcommand=log_scrollbar.set)

    # Log Controls
    log_controls = ttk.Frame(logs_frame)
    log_controls.grid(row=1, column=0, pady=5)
    ttk.Button(log_controls, text="Clear Log", command=self.clear_log).grid(
        row=0, column=0, padx=5
    )
    ttk.Button(log_controls, text="Save Log", command=self.save_log).grid(
        row=0, column=1, padx=5
    )
    # --- Automation Tab Layout ---
    top_frame = ttk.Frame(self.automation_tab, padding=5)
    top_frame.grid(row=0, column=0, sticky="ew")
    top_frame.columnconfigure(1, weight=1)
    ttk.Label(top_frame, text="Select Game Window:").grid(row=0, column=0, sticky="w")
    self.window_list = ttk.Combobox(top_frame)
    self.window_list.grid(row=0, column=1, sticky="ew", padx=5)
    self.window_list.bind("<<ComboboxSelected>>", self.on_window_select)
    ttk.Button(top_frame, text="Refresh", command=self.update_window_list).grid(
        row=0, column=2, padx=5
    )

    # Preview Frame
    preview_frame = ttk.LabelFrame(self.automation_tab, text="Game Preview", padding=5)
    preview_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
    preview_frame.rowconfigure(0, weight=1)
    preview_frame.columnconfigure(0, weight=1)
    # Replace Label with Canvas for ROI drawing
    self.preview_canvas = tk.Canvas(
        preview_frame, bg="white", height=0, width=0
    )  # Use Canvas instead of Label
    self.preview_canvas.grid(row=0, column=0, sticky="nsew")
    preview_controls = ttk.Frame(preview_frame)
    preview_controls.grid(row=1, column=0, pady=5)
    self.preview_btn = ttk.Button(
        preview_controls, text="Start Preview", command=self.toggle_preview
    )
    self.preview_btn.grid(row=0, column=0, padx=5)
    ttk.Button(
        preview_controls, text="Load Templates", command=self.load_templates
    ).grid(row=0, column=1, padx=5)

    # ROI BUTTONs
    ttk.Button(preview_controls, text="Select ROI", command=self.show_roi_popup).grid(
        row=0, column=3, padx=5
    )
    ttk.Button(preview_controls, text="Reset ROI", command=self.reset_roi).grid(
        row=0, column=2, padx=5
    )

    # ROI Display Frame
    roi_display_frame = ttk.LabelFrame(
        self.automation_tab, text="Selected ROI", padding=5
    )
    roi_display_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
    roi_display_frame.rowconfigure(0, weight=1)
    roi_display_frame.columnconfigure(0, weight=1)
    self.roi_display_label = ttk.Label(roi_display_frame)
    self.roi_display_label.grid(row=0, column=0, sticky="nsew")

    # # Magnifier Frame
    # magnifier_frame = ttk.LabelFrame(self.automation_tab, text="Magnifier", padding=5)
    # magnifier_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
    # magnifier_frame.rowconfigure(0, weight=1)
    # magnifier_frame.columnconfigure(0, weight=1)
    # self.magnifier_label = ttk.Label(magnifier_frame)
    # self.magnifier_label.grid(row=0, column=0, sticky="nsew")

    # automation_ctrl_frame = ttk.LabelFrame(self.automation_tab, text="Automation Controls", padding=5)
    # automation_ctrl_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
    # automation_ctrl_frame.columnconfigure(0, weight=1)
    # self.start_btn = ttk.Button(automation_ctrl_frame, text="Start Automation", command=None)
    # self.start_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

    macro_frame = ttk.LabelFrame(self.automation_tab, text="Macro Controls", padding=5)
    macro_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=5)
    self.record_btn = ttk.Button(
        macro_frame, text="Record Macro", command=self.toggle_recording
    )
    self.record_btn.grid(row=0, column=0, padx=5, pady=5)
    self.play_btn = ttk.Button(macro_frame, text="Play Macro", command=self.play_macro)
    self.play_btn.grid(row=0, column=1, padx=5, pady=5)
    self.save_macro_btn = ttk.Button(
        macro_frame, text="Save Macro", command=self.save_macro_to_file
    )
    self.save_macro_btn.grid(row=0, column=2, padx=5, pady=5)
    self.load_macro_btn = ttk.Button(
        macro_frame, text="Load Macro", command=self.load_macro_from_file
    )
    self.load_macro_btn.grid(row=0, column=3, padx=5, pady=5)

    # --- Macro Controls ---
    repeat_frame = ttk.Frame(macro_frame)
    repeat_frame.grid(row=4, column=0, columnspan=4, sticky="ew", pady=5)
    ttk.Label(repeat_frame, text="Repeat Macro:").grid(row=0, column=0, sticky="w")
    self.repeat_count = ttk.Entry(repeat_frame)
    self.repeat_count.insert(0, "1")  # Default to 1 repetition
    self.repeat_count.grid(row=0, column=1, sticky="ew", padx=5)
    repeat_frame.columnconfigure(1, weight=1)

    speed_frame = ttk.Frame(macro_frame)
    speed_frame.grid(row=1, column=0, columnspan=4, sticky="ew", pady=5)
    ttk.Label(speed_frame, text="Playback Speed:").grid(row=0, column=0, sticky="w")
    self.speed_slider = ttk.Scale(
        speed_frame,
        from_=0.5,
        to=3.0,
        orient=tk.HORIZONTAL,
        command=self.update_playback_speed,
    )
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

    # --- Delay Settings ---
    delay_frame = ttk.Frame(macro_frame)
    delay_frame.grid(row=5, column=0, columnspan=4, sticky="ew", pady=5)
    ttk.Label(delay_frame, text="Delay Between Actions (ms):").grid(
        row=0, column=0, sticky="w"
    )
    self.delay_slider = ttk.Scale(delay_frame, from_=0, to=1000, orient=tk.HORIZONTAL)
    self.delay_slider.set(200)  # Default delay of 200ms
    self.delay_slider.grid(row=0, column=1, sticky="ew", padx=5)
    delay_frame.columnconfigure(1, weight=1)

    # --- Configuration Tab Layout ---
    config_frame = ttk.LabelFrame(self.config_tab, text="Image Templates", padding=5)
    config_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    self.template_list = tk.Listbox(config_frame, height=8)
    self.template_list.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    config_btn_frame = ttk.Frame(config_frame)
    config_btn_frame.grid(row=1, column=0, sticky="ew", pady=5)
    ttk.Button(
        config_btn_frame, text="Remove Selected", command=self.remove_template
    ).grid(row=0, column=0, padx=5)

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
        banner_image = Image.open("assets/banner.gif")
        self.frames = [
            ImageTk.PhotoImage(
                frame.convert("RGBA").resize(
                    (200, int(200 * frame.height / frame.width))
                )
            )
            for frame in ImageSequence.Iterator(banner_image)
        ]
        self.banner_label = ttk.Label(about_frame)
        self.banner_label.grid(row=0, column=0, pady=10)

        def animate(counter):
            frame = self.frames[counter]
            self.banner_label.configure(image=frame)
            counter += 1
            if counter == len(self.frames):
                counter = 0
            self.root.after(100, animate, counter)

        animate(0)
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

    # Center align the content
    about_frame.grid_columnconfigure(0, weight=1)
    about_frame.grid_rowconfigure(0, weight=1)
    about_frame.grid_rowconfigure(1, weight=1)
