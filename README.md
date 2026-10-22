# PC Performance Monitor App

A clean, lightweight, and modern desktop application built with Python and PySide6 to monitor real-time system performance on Windows.

---

## Features

1. **CPU Usage & Frequency**
   - Live CPU utilization percentage with progress bar.
   - Live CPU clock frequency (e.g. `3.30 GHz`).
   - Hardware topology (`8 Cores / 16 Threads`).

2. **GPU Performance (Dedicated & Integrated)**
   - Automatic GPU detection (e.g., `NVIDIA GeForce RTX 5050 Laptop GPU` + `AMD Radeon 780M Graphics`).
   - Real-time GPU utilization percentage with progress bar.
   - VRAM Memory usage (Used / Total and percentage).
   - Core Temperature (`°C`) and Power consumption (`Watts`).
   - Secondary / Integrated GPU identification.

3. **RAM & Virtual Memory**
   - Physical memory usage percentage, used RAM, available RAM, and total RAM.
   - Virtual / Pagefile memory usage (Swap Used / Total).

4. **Disk Storage & Real-time I/O Activity**
   - Primary drive capacity (`C:\`) showing percentage used, used GB, and free GB.
   - Real-time Disk I/O throughput (Live Read and Write speeds in KB/s or MB/s).

5. **Network Speeds & Cumulative Data**
   - Live Download and Upload transfer speeds.
   - Cumulative session data transferred (Total Received / Total Sent).

6. **System Information & Power**
   - Operating system version and build.
   - Processor commercial model name.
   - System uptime (`d`, `h`, `m`, `s`).
   - Laptop Battery percentage and power status (`Plugged in` / `On Battery`).

7. **Automatic 1-Second Refresh & Manual Trigger**
   - Background worker thread collects statistics every second without freezing the UI.
   - On-demand "Refresh" button in the footer for instantaneous updates.

8. **Clean, Minimalist Dark Design**
   - Dark charcoal background (`#121214`), subtle gray card panels (`#1c1c21`), white typography, and sky-blue accent (`#38bdf8`).
   - Simple progress bars, clean layout, no unnecessary animations or clutter.

---

## Tech Stack

- **Python 3.10+** (tested on Python 3.14 on Windows)
- **PySide6 (Qt 6)** — Modern desktop GUI framework
- **psutil** — Hardware and system statistics library
- **NVIDIA System Management Interface (`nvidia-smi`)** & Windows Registry — GPU hardware metrics and display adapter discovery
- **pytest** — Unit and integration test suite

---

## Project Structure

```
happy-faraday/
├── main.py              # Application entry point & Qt event loop
├── ui.py                # PySide6 MainWindow, card panels, and worker thread
├── monitor.py           # psutil polling, GPU stats, metric calculation & formatters
├── requirements.txt     # Python package dependencies
├── README.md            # Documentation and instructions
└── tests/
    ├── __init__.py
    └── test_monitor.py  # Unit tests for metrics, formatting, fallbacks & UI
```

---

## Installation & Setup

### 1. Prerequisites
- Python 3.10 or newer on Windows.
- Ensure `pip` is available in your PATH.

### 2. (Optional) Create a Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## Launching the Application

Run the application directly using Python:

```powershell
python main.py
```

The application window will open and begin displaying your live CPU, GPU, RAM, Disk, Network, and System performance metrics immediately.

---


