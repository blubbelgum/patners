# Partners

DLS Helper app is an automation tool designed to assist users in automating repetitive tasks in DLS. It supports macro recording and playback, image-based automation, and OCR (Optical Character Recognition) for text detection.

This README provides detailed instructions for installation, configuration, and usage of the application.

## Table of Contents

- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Installing Dependencies](#installing-dependencies)
  - [Setting Up Tesseract OCR](#setting-up-tesseract-ocr)
- [Usage](#usage)
  - [Launching the Application](#launching-the-application)
  - [Configuring Templates](#configuring-templates)
  - [Using Macros](#using-macros)
  - [Automation Controls](#automation-controls)
  - [Logs and Debugging](#logs-and-debugging)
- [Advanced Features](#advanced-features)
  - [OCR with Tesseract](#ocr-with-tesseract)
  - [Playback Speed Adjustment](#playback-speed-adjustment)
  - [Multi-Macro Support](#multi-macro-support)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Installation

### Prerequisites

Before installing the application, ensure your system meets the following requirements:

- **Operating System**: Windows 10/11 (Linux and macOS support may vary)
- **Python Version**: Python 3.8 or higher
- **Screen Resolution**: Minimum 1024x768 (higher resolutions are recommended for better UI experience)

### Installing Dependencies

#### 1. Clone the Repository

```bash
git clone https://github.com/blubbelgum/patners.git
cd patners
```

#### 2. Install Required Python Libraries

Use pip to install the required dependencies:

```bash
pip install -r requirements.txt
```

The `requirements.txt` file includes the following libraries:
- tkinter
- pyautogui
- opencv-python
- numpy
- pygetwindow
- pynput
- pytesseract
- Pillow

If you encounter issues with pytesseract, refer to the [Tesseract OCR Setup](#setting-up-tesseract-ocr) section below.

#### 3. Verify Installation

Run the following command to verify that all dependencies are installed correctly:

```bash
python -c "import tkinter; import pyautogui; import cv2; import pytesseract"
```

If no errors occur, the installation was successful.

### Setting Up Tesseract OCR

To enable OCR functionality, you must install Tesseract OCR and configure its path in the application.

1. **Download and Install Tesseract**:
   - Download Tesseract from the official repository: [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
   - Follow the installation instructions for your operating system

2. **Set Tesseract Path**:
   - After installation, locate the Tesseract executable (`tesseract.exe` on Windows)
   - Example path: `C:\Program Files\Tesseract-OCR\tesseract.exe`
   - Open the Configuration Tab in the application
   - Enter the full path to the Tesseract executable in the "Tesseract Path" field

3. **Test OCR**:
   - Load an image template and use the OCR feature to detect text
   - If the setup is correct, the application will display the detected text in the logs

## Usage

### Launching the Application

1. Navigate to the project directory:
   ```bash
   cd patners
   ```

2. Run the application:
   ```bash
   python main.py
   ```

The main window will appear with three tabs: **Automation**, **Configuration**, and **Logs**.

### Configuring Templates

Templates are images used for image-based automation. Follow these steps to configure templates:

1. Go to the **Configuration Tab**
2. Click **Add Template** and select one or more image files (.png, .jpg, .jpeg)
3. The template names will appear in the Image Templates list
4. To remove a template, select it from the list and click **Remove Selected**

#### Tips for Creating Templates:
- Use high-resolution screenshots of specific UI elements (e.g., buttons, icons)
- Ensure the template matches the exact appearance of the target element in the game/application
- Crop templates to contain only the relevant visual elements
- Maintain consistent resolution and scaling

### Using Macros

Macros allow you to record and replay sequences of keyboard and mouse actions.

#### Recording a Macro:
1. Click **Record Macro** in the Macro Controls section
2. Perform the desired actions (e.g., clicking buttons, typing text)
3. Click **Stop Recording** when finished

#### Playing a Macro:
1. Select a macro from the Macro Library or use the currently recorded macro
2. Click **Play Macro** to execute the sequence

#### Saving and Loading Macros:
- Save macros to a .json file by clicking **Save Macro**
- Load previously saved macros using **Load Macro**
- Macros include timing information and action sequences

### Automation Controls

#### Select Game Window:
1. Use the dropdown menu in the Automation Tab to select the target application window
2. Click **Refresh** to update the list of available windows

#### Start Automation:
1. Ensure templates are loaded and configured
2. Click **Start Automation** to begin the automation process

#### Stop Automation:
- Click **Stop Automation** to halt the process
- The application will complete the current action before stopping

### Logs and Debugging

The Logs Tab displays real-time activity logs. Use this tab to monitor automation progress and debug issues.

#### Log Controls:
- **Clear Log**: Removes all log entries
- **Save Log**: Exports the log to a .txt file
- Log entries include timestamps and detailed action information

## Advanced Features

### OCR with Tesseract

OCR is used to detect text within images. This feature is particularly useful for identifying dynamic content like scores, timers, or status messages.

#### Setup and Usage:
1. Ensure Tesseract is installed and configured (see [Setting Up Tesseract OCR](#setting-up-tesseract-ocr))
2. Use templates with text regions to trigger OCR-based actions
3. Configure text recognition settings in the Configuration Tab

### Playback Speed Adjustment

Adjust the playback speed of macros using the slider in the Macro Controls section:
- Values range from 0.5x (slower) to 3.0x (faster)
- Speed affects all actions in the macro sequence
- Real-time adjustment during playback is supported

### Multi-Macro Support

You can string together multiple macros into a workflow:

1. Record or load individual macros
2. Play them sequentially by selecting each macro from the library
3. Click **Play Macro** to execute each sequence
4. Create complex automation workflows by combining macros

## Troubleshooting

### Common Issues and Solutions

#### Tesseract Not Found:
- Ensure the Tesseract path is correctly set in the Configuration Tab
- Verify that Tesseract is installed and accessible
- Check system environment variables

#### Template Matching Fails:
- Check the resolution and quality of the template image
- Ensure the target application window matches the template exactly
- Verify window scaling settings

#### Automation Stops Unexpectedly:
- Ensure the target window remains active during automation
- Check the logs for error messages
- Verify system resources and permissions

#### Performance Issues:
- Reduce the screen resolution or limit the preview size
- Avoid running other resource-intensive applications simultaneously
- Monitor system resource usage during automation

## Contributing

We welcome contributions to improve Game AutoBot Pro! To contribute:

1. Fork the repository
2. Create a new branch for your changes:
   ```bash
   git checkout -b feature/YourFeature
   ```
3. Make your changes and commit them:
   ```bash
   git commit -m 'Add some feature'
   ```
4. Push to your branch:
   ```bash
   git push origin feature/YourFeature
   ```
5. Submit a pull request with a detailed description of your updates

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

For additional support, feature requests, or bug reports, please open an issue in the GitHub repository.