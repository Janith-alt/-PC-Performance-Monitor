"""
PC Performance Monitor - User Interface
PySide6 desktop interface displaying real-time CPU, GPU, RAM, Disk, Network,
and System Information using a clean dark aesthetic.
"""

from __future__ import annotations

import time
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from monitor import (
    SystemMetrics,
    SystemMonitor,
    format_bytes,
    format_speed,
    format_uptime,
)

# Design Tokens
COLOR_BG = "#121214"
COLOR_PANEL = "#1c1c21"
COLOR_BORDER = "#2b2b35"
COLOR_TEXT_PRIMARY = "#f9fafb"
COLOR_TEXT_SECONDARY = "#9ca3af"
COLOR_ACCENT = "#38bdf8"  # Subtle sky blue accent
COLOR_PROGRESS_BG = "#26262e"

STYLESHEET = f"""
QMainWindow {{
    background-color: {COLOR_BG};
}}

QWidget#CentralWidget {{
    background-color: {COLOR_BG};
}}

QScrollArea {{
    background-color: transparent;
    border: none;
}}

QScrollBar:vertical {{
    background-color: {COLOR_BG};
    width: 6px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background-color: #33333d;
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: #4a4a58;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* Card Panels */
QFrame.panel-card {{
    background-color: {COLOR_PANEL};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
}}

/* Typography */
QLabel {{
    color: {COLOR_TEXT_PRIMARY};
}}

QLabel.section-title {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 11px;
    font-weight: 600;
}}

QLabel.metric-value {{
    color: {COLOR_ACCENT};
    font-size: 15px;
    font-weight: 700;
}}

QLabel.stat-subtext {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 11px;
}}

QLabel.info-key {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 12px;
    font-weight: 500;
}}

QLabel.info-value {{
    color: {COLOR_TEXT_PRIMARY};
    font-size: 12px;
    font-weight: 500;
}}

/* Progress Bars */
QProgressBar {{
    background-color: {COLOR_PROGRESS_BG};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    height: 9px;
    text-align: right;
}}

QProgressBar::chunk {{
    background-color: {COLOR_ACCENT};
    border-radius: 3px;
}}

/* Buttons */
QPushButton.btn-refresh {{
    background-color: #24242d;
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 5px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 500;
}}

QPushButton.btn-refresh:hover {{
    background-color: #2d2d38;
    border-color: #3f3f4e;
}}

QPushButton.btn-refresh:pressed {{
    background-color: #1a1a22;
}}
"""


class MonitorWorker(QThread):
    """Background worker collecting system metrics every second."""

    metrics_updated = Signal(SystemMetrics)

    def __init__(self, monitor: SystemMonitor):
        super().__init__()
        self.monitor = monitor
        self._running = True
        self._trigger_immediate = False

    def trigger_refresh(self) -> None:
        """Trigger an immediate sample collection."""
        self._trigger_immediate = True

    def run(self) -> None:
        while self._running:
            try:
                metrics = self.monitor.collect()
                self.metrics_updated.emit(metrics)
            except Exception:
                pass

            self._trigger_immediate = False
            for _ in range(10):
                if not self._running or self._trigger_immediate:
                    break
                time.sleep(0.1)

    def stop(self) -> None:
        """Gracefully stop the worker thread."""
        self._running = False
        self.wait(2000)


class MainWindow(QMainWindow):
    """Main window for PC Performance Monitor."""

    def __init__(self, monitor: Optional[SystemMonitor] = None):
        super().__init__()
        self.setWindowTitle("PC Performance Monitor")
        self.resize(480, 720)
        self.setMinimumSize(400, 580)
        self.setStyleSheet(STYLESHEET)

        self.monitor = monitor or SystemMonitor()
        self._init_ui()

        # Start background collector thread
        self.worker = MonitorWorker(self.monitor)
        self.worker.metrics_updated.connect(self.on_metrics_updated)
        self.worker.start()

        # Initial collect to populate UI immediately
        initial_data = self.monitor.collect()
        self.on_metrics_updated(initial_data)

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(10)

        # Header bar
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 4)

        title_label = QLabel("PC Performance Monitor")
        title_font = QFont("Segoe UI", 13, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        self.live_indicator = QLabel("● Live (1s)")
        self.live_indicator.setStyleSheet(
            f"color: {COLOR_ACCENT}; font-size: 11px; font-weight: 600;"
        )
        header_layout.addWidget(self.live_indicator)

        root_layout.addLayout(header_layout)

        # Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        cards_layout = QVBoxLayout(container)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(10)

        # 1. System Information Panel
        self.panel_sys = self._build_system_info_panel()
        cards_layout.addWidget(self.panel_sys)

        # 2. CPU Usage Panel
        self.panel_cpu = self._build_cpu_panel()
        cards_layout.addWidget(self.panel_cpu)

        # 3. GPU Usage Panel
        self.panel_gpu = self._build_gpu_panel()
        cards_layout.addWidget(self.panel_gpu)

        # 4. RAM Usage Panel
        self.panel_ram = self._build_ram_panel()
        cards_layout.addWidget(self.panel_ram)

        # 5. Disk Usage Panel
        self.panel_disk = self._build_disk_panel()
        cards_layout.addWidget(self.panel_disk)

        # 6. Network Usage Panel
        self.panel_net = self._build_network_panel()
        cards_layout.addWidget(self.panel_net)

        cards_layout.addStretch()
        scroll_area.setWidget(container)
        root_layout.addWidget(scroll_area)

        # Footer Bar
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(2, 4, 2, 0)

        self.footer_label = QLabel("Waiting for data...")
        self.footer_label.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-size: 10px;"
        )
        footer_layout.addWidget(self.footer_label)

        footer_layout.addStretch()

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setProperty("class", "btn-refresh")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self._manual_refresh)
        footer_layout.addWidget(self.btn_refresh)

        root_layout.addLayout(footer_layout)

    # -------------------------------------------------------------------------
    # Panel Builders
    # -------------------------------------------------------------------------
    def _create_card_frame(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "panel-card")
        return card

    def _build_system_info_panel(self) -> QFrame:
        card = self._create_card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(7)

        title = QLabel("SYSTEM INFORMATION")
        title.setProperty("class", "section-title")
        layout.addWidget(title)

        # OS Row
        row_os = QHBoxLayout()
        key_os = QLabel("Operating System")
        key_os.setProperty("class", "info-key")
        self.val_os = QLabel("—")
        self.val_os.setProperty("class", "info-value")
        self.val_os.setAlignment(Qt.AlignmentFlag.AlignRight)
        row_os.addWidget(key_os)
        row_os.addStretch()
        row_os.addWidget(self.val_os)
        layout.addLayout(row_os)

        # Processor Row
        row_proc = QHBoxLayout()
        key_proc = QLabel("Processor")
        key_proc.setProperty("class", "info-key")
        self.val_proc = QLabel("—")
        self.val_proc.setProperty("class", "info-value")
        self.val_proc.setAlignment(Qt.AlignmentFlag.AlignRight)
        row_proc.addWidget(key_proc)
        row_proc.addStretch()
        row_proc.addWidget(self.val_proc)
        layout.addLayout(row_proc)

        # Uptime Row
        row_up = QHBoxLayout()
        key_up = QLabel("System Uptime")
        key_up.setProperty("class", "info-key")
        self.val_uptime = QLabel("—")
        self.val_uptime.setProperty("class", "info-value")
        self.val_uptime.setAlignment(Qt.AlignmentFlag.AlignRight)
        row_up.addWidget(key_up)
        row_up.addStretch()
        row_up.addWidget(self.val_uptime)
        layout.addLayout(row_up)

        # Battery Row (shows on laptops/battery PCs)
        self.row_bat_widget = QWidget()
        row_bat = QHBoxLayout(self.row_bat_widget)
        row_bat.setContentsMargins(0, 0, 0, 0)
        key_bat = QLabel("Power / Battery")
        key_bat.setProperty("class", "info-key")
        self.val_battery = QLabel("—")
        self.val_battery.setProperty("class", "info-value")
        self.val_battery.setAlignment(Qt.AlignmentFlag.AlignRight)
        row_bat.addWidget(key_bat)
        row_bat.addStretch()
        row_bat.addWidget(self.val_battery)
        layout.addWidget(self.row_bat_widget)

        return card

    def _build_cpu_panel(self) -> QFrame:
        card = self._create_card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Header row
        header = QHBoxLayout()
        title = QLabel("CPU USAGE")
        title.setProperty("class", "section-title")
        self.val_cpu = QLabel("0.0%")
        self.val_cpu.setProperty("class", "metric-value")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.val_cpu)
        layout.addLayout(header)

        # Progress bar
        self.bar_cpu = QProgressBar()
        self.bar_cpu.setRange(0, 100)
        self.bar_cpu.setValue(0)
        self.bar_cpu.setTextVisible(False)
        layout.addWidget(self.bar_cpu)

        # CPU extra details (Frequency & Cores)
        self.val_cpu_details = QLabel("Clock: — | Cores: —")
        self.val_cpu_details.setProperty("class", "stat-subtext")
        layout.addWidget(self.val_cpu_details)

        return card

    def _build_gpu_panel(self) -> QFrame:
        card = self._create_card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Header row
        header = QHBoxLayout()
        self.title_gpu = QLabel("GPU USAGE")
        self.title_gpu.setProperty("class", "section-title")
        self.val_gpu_util = QLabel("—")
        self.val_gpu_util.setProperty("class", "metric-value")
        header.addWidget(self.title_gpu)
        header.addStretch()
        header.addWidget(self.val_gpu_util)
        layout.addLayout(header)

        # Progress bar
        self.bar_gpu = QProgressBar()
        self.bar_gpu.setRange(0, 100)
        self.bar_gpu.setValue(0)
        self.bar_gpu.setTextVisible(False)
        layout.addWidget(self.bar_gpu)

        # VRAM & Temperature
        self.val_gpu_details = QLabel("VRAM: — | Temp: —")
        self.val_gpu_details.setProperty("class", "stat-subtext")
        layout.addWidget(self.val_gpu_details)

        # Secondary GPU (e.g. integrated graphics)
        self.val_gpu_secondary = QLabel("")
        self.val_gpu_secondary.setProperty("class", "stat-subtext")
        self.val_gpu_secondary.setVisible(False)
        layout.addWidget(self.val_gpu_secondary)

        return card

    def _build_ram_panel(self) -> QFrame:
        card = self._create_card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Header row
        header = QHBoxLayout()
        title = QLabel("RAM USAGE")
        title.setProperty("class", "section-title")
        self.val_ram_percent = QLabel("0.0%")
        self.val_ram_percent.setProperty("class", "metric-value")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.val_ram_percent)
        layout.addLayout(header)

        # Progress bar
        self.bar_ram = QProgressBar()
        self.bar_ram.setRange(0, 100)
        self.bar_ram.setValue(0)
        self.bar_ram.setTextVisible(False)
        layout.addWidget(self.bar_ram)

        # Subtext details (Used / Available / Total)
        self.val_ram_details = QLabel("Used: — | Available: — | Total: —")
        self.val_ram_details.setProperty("class", "stat-subtext")
        layout.addWidget(self.val_ram_details)

        # Swap memory details
        self.val_swap_details = QLabel("Swap: —")
        self.val_swap_details.setProperty("class", "stat-subtext")
        layout.addWidget(self.val_swap_details)

        return card

    def _build_disk_panel(self) -> QFrame:
        card = self._create_card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Header row
        header = QHBoxLayout()
        self.title_disk = QLabel("DISK USAGE (MAIN DRIVE)")
        self.title_disk.setProperty("class", "section-title")
        self.val_disk_percent = QLabel("0.0%")
        self.val_disk_percent.setProperty("class", "metric-value")
        header.addWidget(self.title_disk)
        header.addStretch()
        header.addWidget(self.val_disk_percent)
        layout.addLayout(header)

        # Progress bar
        self.bar_disk = QProgressBar()
        self.bar_disk.setRange(0, 100)
        self.bar_disk.setValue(0)
        self.bar_disk.setTextVisible(False)
        layout.addWidget(self.bar_disk)

        # Subtext details (Used / Available / Total)
        self.val_disk_details = QLabel("Used: — | Available: — | Total: —")
        self.val_disk_details.setProperty("class", "stat-subtext")
        layout.addWidget(self.val_disk_details)

        # Disk I/O Activity
        self.val_disk_io = QLabel("Read: 0 B/s   •   Write: 0 B/s")
        self.val_disk_io.setProperty("class", "stat-subtext")
        layout.addWidget(self.val_disk_io)

        return card

    def _build_network_panel(self) -> QFrame:
        card = self._create_card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        title = QLabel("NETWORK USAGE")
        title.setProperty("class", "section-title")
        layout.addWidget(title)

        # Side-by-side speeds
        speeds_layout = QHBoxLayout()
        speeds_layout.setSpacing(12)

        # Download block
        dl_block = QVBoxLayout()
        dl_block.setSpacing(2)
        dl_label = QLabel("Download Speed")
        dl_label.setProperty("class", "stat-subtext")
        self.val_net_dl = QLabel("0 B/s")
        self.val_net_dl.setProperty("class", "metric-value")
        dl_block.addWidget(dl_label)
        dl_block.addWidget(self.val_net_dl)
        speeds_layout.addLayout(dl_block)

        # Vertical divider line
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setFrameShadow(QFrame.Shadow.Plain)
        divider.setStyleSheet(f"color: {COLOR_BORDER}; background-color: {COLOR_BORDER};")
        speeds_layout.addWidget(divider)

        # Upload block
        ul_block = QVBoxLayout()
        ul_block.setSpacing(2)
        ul_label = QLabel("Upload Speed")
        ul_label.setProperty("class", "stat-subtext")
        self.val_net_ul = QLabel("0 B/s")
        self.val_net_ul.setProperty("class", "metric-value")
        ul_block.addWidget(ul_label)
        ul_block.addWidget(self.val_net_ul)
        speeds_layout.addLayout(ul_block)

        layout.addLayout(speeds_layout)

        # Total session transfer
        self.val_net_totals = QLabel("Total: 0 B In   •   0 B Out")
        self.val_net_totals.setProperty("class", "stat-subtext")
        layout.addWidget(self.val_net_totals)

        return card

    # -------------------------------------------------------------------------
    # Updates & Event Handling
    # -------------------------------------------------------------------------
    def on_metrics_updated(self, metrics: SystemMetrics) -> None:
        """Slot called whenever fresh metrics are received."""
        # 1. System Info
        self.val_os.setText(metrics.os_info)
        self.val_proc.setText(metrics.processor_info)
        self.val_uptime.setText(format_uptime(metrics.uptime_seconds))

        if metrics.battery_percent is not None:
            self.row_bat_widget.setVisible(True)
            status = "Plugged in" if metrics.battery_plugged else "On Battery"
            self.val_battery.setText(f"{int(metrics.battery_percent)}% ({status})")
        else:
            self.row_bat_widget.setVisible(False)

        # 2. CPU
        self.val_cpu.setText(f"{metrics.cpu_percent:.1f}%")
        self.bar_cpu.setValue(int(round(metrics.cpu_percent)))

        freq_str = f"Clock: {metrics.cpu_freq_ghz:.2f} GHz" if metrics.cpu_freq_ghz else "Clock: N/A"
        cores_str = f"{metrics.cpu_physical_cores} Cores / {metrics.cpu_logical_cores} Threads"
        self.val_cpu_details.setText(f"{freq_str}   •   {cores_str}")

        # 3. GPU
        gpu = metrics.gpu
        # Truncate or clean title if too long
        gpu_short_name = gpu.name.replace("NVIDIA ", "").replace("AMD ", "")
        self.title_gpu.setText(f"GPU USAGE ({gpu_short_name})")

        if gpu.utilization_percent is not None:
            self.val_gpu_util.setText(f"{gpu.utilization_percent:.1f}%")
            self.bar_gpu.setValue(int(round(gpu.utilization_percent)))
            self.bar_gpu.setVisible(True)
        else:
            self.val_gpu_util.setText("Active")
            self.bar_gpu.setVisible(False)

        # GPU Details
        detail_parts = []
        if gpu.vram_total_bytes > 0:
            used_vram = format_bytes(gpu.vram_used_bytes)
            tot_vram = format_bytes(gpu.vram_total_bytes)
            vram_pct = f" ({gpu.vram_percent:.1f}%)" if gpu.vram_percent is not None else ""
            detail_parts.append(f"VRAM: {used_vram} / {tot_vram}{vram_pct}")
        if gpu.temp_c is not None:
            detail_parts.append(f"Temp: {int(gpu.temp_c)}°C")
        if gpu.power_watts is not None:
            detail_parts.append(f"Power: {gpu.power_watts:.1f}W")

        if detail_parts:
            self.val_gpu_details.setText("   •   ".join(detail_parts))
            self.val_gpu_details.setVisible(True)
        else:
            self.val_gpu_details.setVisible(False)

        if gpu.secondary_gpus:
            self.val_gpu_secondary.setText(f"Secondary: {', '.join(gpu.secondary_gpus)}")
            self.val_gpu_secondary.setVisible(True)
        else:
            self.val_gpu_secondary.setVisible(False)

        # 4. RAM
        self.val_ram_percent.setText(f"{metrics.ram_percent:.1f}%")
        self.bar_ram.setValue(int(round(metrics.ram_percent)))
        used_ram = format_bytes(metrics.ram_used_bytes)
        avail_ram = format_bytes(metrics.ram_avail_bytes)
        total_ram = format_bytes(metrics.ram_total_bytes)
        self.val_ram_details.setText(
            f"Used: {used_ram}   •   Available: {avail_ram}   •   Total: {total_ram}"
        )

        if metrics.ram_swap_total_bytes > 0:
            used_swap = format_bytes(metrics.ram_swap_used_bytes)
            tot_swap = format_bytes(metrics.ram_swap_total_bytes)
            self.val_swap_details.setText(
                f"Swap: {used_swap} / {tot_swap} ({metrics.ram_swap_percent:.1f}%)"
            )
            self.val_swap_details.setVisible(True)
        else:
            self.val_swap_details.setVisible(False)

        # 5. Disk
        drive_name = metrics.disk_drive.rstrip("\\")
        self.title_disk.setText(f"DISK USAGE ({drive_name})")
        self.val_disk_percent.setText(f"{metrics.disk_percent:.1f}%")
        self.bar_disk.setValue(int(round(metrics.disk_percent)))
        used_disk = format_bytes(metrics.disk_used_bytes)
        free_disk = format_bytes(metrics.disk_free_bytes)
        total_disk = format_bytes(metrics.disk_total_bytes)
        self.val_disk_details.setText(
            f"Used: {used_disk}   •   Available: {free_disk}   •   Total: {total_disk}"
        )
        r_speed = format_speed(metrics.disk_read_bytes_sec)
        w_speed = format_speed(metrics.disk_write_bytes_sec)
        self.val_disk_io.setText(f"Activity: Read {r_speed}   •   Write {w_speed}")

        # 6. Network
        self.val_net_dl.setText(format_speed(metrics.net_download_bytes_sec))
        self.val_net_ul.setText(format_speed(metrics.net_upload_bytes_sec))
        tot_in = format_bytes(metrics.net_total_recv_bytes)
        tot_out = format_bytes(metrics.net_total_sent_bytes)
        self.val_net_totals.setText(f"Session: {tot_in} Received   •   {tot_out} Sent")

        # Footer update
        timestr = time.strftime("%H:%M:%S", time.localtime(metrics.timestamp))
        if metrics.errors:
            self.footer_label.setText(f"Last updated {timestr} ({len(metrics.errors)} sensor note)")
        else:
            self.footer_label.setText(f"Last updated {timestr}")

    def _manual_refresh(self) -> None:
        """Trigger immediate data refresh on demand."""
        self.worker.trigger_refresh()

    def closeEvent(self, event) -> None:
        """Ensure background worker stops cleanly on window exit."""
        if hasattr(self, "worker") and self.worker.isRunning():
            self.worker.stop()
        super().closeEvent(event)
