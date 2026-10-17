"""
Unit and integration tests for PC Performance Monitor.
Verifies system metrics collection, formatters, fallbacks, GPU handling, and UI components.
"""

from __future__ import annotations

import sys
import time
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication

from monitor import (
    GpuMetrics,
    SystemMetrics,
    SystemMonitor,
    format_bytes,
    format_speed,
    format_uptime,
    get_installed_gpus,
    get_main_drive,
    get_os_info,
    get_processor_name,
)
from ui import MainWindow


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single QApplication instance exists for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


# =============================================================================
# Formatter Tests
# =============================================================================

def test_format_bytes():
    assert format_bytes(0) == "0 B"
    assert format_bytes(500) == "500 B"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1024 * 1024) == "1.0 MB"
    assert format_bytes(1024 * 1024 * 1024) == "1.0 GB"
    assert format_bytes(16 * 1024 * 1024 * 1024) == "16.0 GB"
    assert format_bytes(-5) == "0.0 B"


def test_format_speed():
    assert format_speed(0) == "0 B/s"
    assert format_speed(500) == "500 B/s"
    assert format_speed(1024) == "1.0 KB/s"
    assert format_speed(1024 * 1024 * 2.5) == "2.5 MB/s"
    assert format_speed(1024 * 1024 * 1024) == "1.0 GB/s"
    assert format_speed(-10) == "0 B/s"


def test_format_uptime():
    assert format_uptime(0) == "0s"
    assert format_uptime(45) == "45s"
    assert format_uptime(125) == "2m 5s"
    assert format_uptime(3665) == "1h 1m 5s"
    assert format_uptime(90061) == "1d 1h 1m 1s"
    assert format_uptime(-10) == "0s"


# =============================================================================
# System Info & Hardware Detection Tests
# =============================================================================

def test_get_os_info():
    os_info = get_os_info()
    assert isinstance(os_info, str)
    assert len(os_info) > 0


def test_get_processor_name():
    proc = get_processor_name()
    assert isinstance(proc, str)
    assert len(proc) > 0


def test_get_main_drive():
    drive = get_main_drive()
    assert isinstance(drive, str)
    assert len(drive) > 0


def test_get_installed_gpus():
    gpus = get_installed_gpus()
    assert isinstance(gpus, list)


# =============================================================================
# SystemMonitor Collection Tests
# =============================================================================

def test_system_monitor_live_collection():
    mon = SystemMonitor()
    metrics = mon.collect()

    assert isinstance(metrics, SystemMetrics)
    # CPU
    assert 0.0 <= metrics.cpu_percent <= 100.0
    assert metrics.cpu_physical_cores >= 1
    assert metrics.cpu_logical_cores >= 1
    # GPU
    assert isinstance(metrics.gpu, GpuMetrics)
    assert len(metrics.gpu.name) > 0
    # RAM
    assert metrics.ram_total_bytes > 0
    assert metrics.ram_used_bytes > 0
    assert 0.0 <= metrics.ram_percent <= 100.0
    # Disk
    assert metrics.disk_total_bytes > 0
    assert 0.0 <= metrics.disk_percent <= 100.0
    # System Info
    assert len(metrics.os_info) > 0
    assert len(metrics.processor_info) > 0
    assert metrics.uptime_seconds >= 0.0


def test_network_speed_delta_calculation():
    mon = SystemMonitor()

    counter1 = MagicMock(bytes_recv=1000, bytes_sent=500)
    counter2 = MagicMock(bytes_recv=1000 + 1024 * 1024, bytes_sent=500 + 512 * 1024)

    with patch("psutil.net_io_counters", side_effect=[counter1, counter2]):
        mon.collect()
        time.sleep(0.1)
        m2 = mon.collect()

        assert m2.net_download_bytes_sec > 0
        assert m2.net_upload_bytes_sec > 0


def test_graceful_handling_missing_sensors():
    """Ensure that if psutil raises exceptions for any sensor, the collector handles it gracefully."""
    mon = SystemMonitor()

    with patch("psutil.cpu_percent", side_effect=RuntimeError("CPU sensor unavailable")), \
         patch("psutil.virtual_memory", side_effect=PermissionError("RAM access denied")), \
         patch("psutil.disk_usage", side_effect=FileNotFoundError("Drive not found")), \
         patch("psutil.net_io_counters", side_effect=RuntimeError("Net unavailable")), \
         patch("psutil.boot_time", side_effect=RuntimeError("Boot time error")):

        metrics = mon.collect()
        assert metrics is not None
        assert metrics.cpu_percent == 0.0
        assert metrics.ram_percent == 0.0
        assert metrics.disk_percent == 0.0
        assert len(metrics.errors) > 0


# =============================================================================
# UI Tests
# =============================================================================

def test_ui_initialization_and_update(qapp):
    """Test that MainWindow creates all widgets and safely processes metric updates."""
    mon = SystemMonitor()
    window = MainWindow(monitor=mon)
    try:
        assert window.windowTitle() == "PC Performance Monitor"

        # Check widget references exist
        assert window.val_cpu is not None
        assert window.bar_cpu is not None
        assert window.val_cpu_details is not None
        assert window.val_gpu_util is not None
        assert window.bar_gpu is not None
        assert window.val_gpu_details is not None
        assert window.val_ram_percent is not None
        assert window.bar_ram is not None
        assert window.val_swap_details is not None
        assert window.val_disk_percent is not None
        assert window.bar_disk is not None
        assert window.val_disk_io is not None
        assert window.val_net_dl is not None
        assert window.val_net_ul is not None
        assert window.val_net_totals is not None
        assert window.val_os is not None
        assert window.val_proc is not None
        assert window.val_uptime is not None

        # Feed custom metrics
        test_metric = SystemMetrics(
            cpu_percent=42.5,
            cpu_freq_ghz=3.5,
            cpu_physical_cores=8,
            cpu_logical_cores=16,
            gpu=GpuMetrics(
                name="NVIDIA GeForce RTX 5050 Laptop GPU",
                utilization_percent=22.0,
                vram_used_bytes=2 * 1024**3,
                vram_total_bytes=8 * 1024**3,
                vram_percent=25.0,
                temp_c=45.0,
                power_watts=35.0,
                secondary_gpus=["AMD Radeon 780M Graphics"],
            ),
            ram_used_bytes=8 * 1024**3,
            ram_total_bytes=16 * 1024**3,
            ram_avail_bytes=8 * 1024**3,
            ram_percent=50.0,
            ram_swap_used_bytes=512 * 1024 * 1024,
            ram_swap_total_bytes=4 * 1024**3,
            ram_swap_percent=12.5,
            disk_drive="C:\\",
            disk_used_bytes=100 * 1024**3,
            disk_free_bytes=150 * 1024**3,
            disk_total_bytes=250 * 1024**3,
            disk_percent=40.0,
            disk_read_bytes_sec=1024 * 1024 * 5,
            disk_write_bytes_sec=1024 * 1024 * 2,
            net_download_bytes_sec=1024 * 1024 * 3.5,
            net_upload_bytes_sec=512 * 1024,
            net_total_recv_bytes=1024 * 1024 * 500,
            net_total_sent_bytes=1024 * 1024 * 120,
            os_info="Test OS 1.0",
            processor_info="Test Core Ultra",
            uptime_seconds=3665,
            battery_percent=85.0,
            battery_plugged=True,
        )

        window.on_metrics_updated(test_metric)

        assert window.val_cpu.text() == "42.5%"
        assert window.bar_cpu.value() == int(round(test_metric.cpu_percent))
        assert "3.50 GHz" in window.val_cpu_details.text()
        assert "8 Cores / 16 Threads" in window.val_cpu_details.text()

        # GPU
        assert window.val_gpu_util.text() == "22.0%"
        assert window.bar_gpu.value() == 22
        assert "2.0 GB / 8.0 GB" in window.val_gpu_details.text()
        assert "45°C" in window.val_gpu_details.text()
        assert "35.0W" in window.val_gpu_details.text()
        assert "AMD Radeon 780M Graphics" in window.val_gpu_secondary.text()

        # RAM & Swap
        assert window.val_ram_percent.text() == "50.0%"
        assert window.bar_ram.value() == 50
        assert "8.0 GB" in window.val_ram_details.text()
        assert "Swap:" in window.val_swap_details.text()

        # Disk
        assert window.val_disk_percent.text() == "40.0%"
        assert window.bar_disk.value() == 40
        assert "Read 5.0 MB/s" in window.val_disk_io.text()

        # Net
        assert "3.5 MB/s" in window.val_net_dl.text()
        assert "512.0 KB/s" in window.val_net_ul.text()

        # System Info & Battery
        assert window.val_os.text() == "Test OS 1.0"
        assert window.val_proc.text() == "Test Core Ultra"
        assert window.val_uptime.text() == "1h 1m 5s"
        assert "85%" in window.val_battery.text()

    finally:
        window.close()
