"""
PC Performance Monitor - System Monitoring Engine
Uses psutil, Windows APIs, and hardware utilities to safely collect comprehensive
CPU, GPU, RAM, Disk, Network, Battery, and OS performance metrics.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

import psutil


@dataclass
class GpuMetrics:
    """Snapshot of GPU hardware metrics."""
    name: str = "No GPU Detected"
    utilization_percent: Optional[float] = None
    vram_used_bytes: int = 0
    vram_total_bytes: int = 0
    vram_percent: Optional[float] = None
    temp_c: Optional[float] = None
    power_watts: Optional[float] = None
    secondary_gpus: list[str] = field(default_factory=list)


@dataclass
class SystemMetrics:
    """Snapshot of system performance and hardware metrics."""
    # CPU
    cpu_percent: float = 0.0
    cpu_freq_ghz: Optional[float] = None
    cpu_physical_cores: int = 0
    cpu_logical_cores: int = 0

    # GPU
    gpu: GpuMetrics = field(default_factory=GpuMetrics)

    # RAM
    ram_used_bytes: int = 0
    ram_total_bytes: int = 0
    ram_avail_bytes: int = 0
    ram_percent: float = 0.0
    ram_swap_used_bytes: int = 0
    ram_swap_total_bytes: int = 0
    ram_swap_percent: float = 0.0

    # Disk
    disk_drive: str = "C:\\"
    disk_used_bytes: int = 0
    disk_free_bytes: int = 0
    disk_total_bytes: int = 0
    disk_percent: float = 0.0
    disk_read_bytes_sec: float = 0.0
    disk_write_bytes_sec: float = 0.0

    # Network
    net_download_bytes_sec: float = 0.0
    net_upload_bytes_sec: float = 0.0
    net_total_recv_bytes: int = 0
    net_total_sent_bytes: int = 0

    # System Info & Power
    os_info: str = "Unknown OS"
    processor_info: str = "Unknown Processor"
    uptime_seconds: float = 0.0
    battery_percent: Optional[float] = None
    battery_plugged: Optional[bool] = None

    # Metadata
    timestamp: float = field(default_factory=time.time)
    errors: list[str] = field(default_factory=list)


def format_bytes(num_bytes: float, precision: int = 1) -> str:
    """Format byte counts into human-readable units (B, KB, MB, GB, TB)."""
    if num_bytes < 0:
        return "0.0 B"
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(num_bytes) < 1024.0 or unit == "PB":
            if unit == "B":
                return f"{int(num_bytes)} B"
            return f"{num_bytes:.{precision}f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.{precision}f} PB"


def format_speed(bytes_per_sec: float) -> str:
    """Format data transfer speed into human-readable B/s, KB/s, MB/s, or GB/s."""
    if bytes_per_sec <= 0:
        return "0 B/s"
    for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
        if bytes_per_sec < 1024.0 or unit == "GB/s":
            if unit == "B/s":
                return f"{int(bytes_per_sec)} B/s"
            return f"{bytes_per_sec:.1f} {unit}"
        bytes_per_sec /= 1024.0
    return f"{bytes_per_sec:.1f} GB/s"


def format_uptime(seconds: float) -> str:
    """Format uptime seconds into a clean, human-readable string (e.g., 2d 5h 32m 10s)."""
    if seconds < 0:
        return "0s"
    total_secs = int(seconds)
    days, rem = divmod(total_secs, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)

    parts: list[str] = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")

    return " ".join(parts)


def get_processor_name() -> str:
    """Retrieve a friendly processor model name, with Windows Registry fallback."""
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            cleaned = name.strip()
            if cleaned:
                return cleaned
        except Exception:
            pass

    proc = platform.processor()
    if proc and proc.strip():
        return proc.strip()

    env_proc = os.environ.get("PROCESSOR_IDENTIFIER")
    if env_proc and env_proc.strip():
        return env_proc.strip()

    return platform.machine() or "Unknown Processor"


def get_installed_gpus() -> list[str]:
    """Enumerate display adapter names directly from Windows Registry."""
    gpus: list[str] = []
    if sys.platform == "win32":
        try:
            import winreg
            class_key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}",
            )
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(class_key, i)
                    if sub.isdigit():
                        subkey = winreg.OpenKey(class_key, sub)
                        try:
                            name, _ = winreg.QueryValueEx(subkey, "DriverDesc")
                            name_str = name.strip() if isinstance(name, str) else ""
                            if name_str and name_str not in gpus:
                                gpus.append(name_str)
                        except Exception:
                            pass
                        winreg.CloseKey(subkey)
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(class_key)
        except Exception:
            pass
    return gpus


def get_os_info() -> str:
    """Retrieve operating system release and build information."""
    try:
        sys_name = platform.system()
        release = platform.release()
        version = platform.version()

        if sys_name == "Windows":
            return f"Windows {release} (Build {version})"
        return f"{sys_name} {release}".strip()
    except Exception:
        return "Unknown OS"


def get_main_drive() -> str:
    """Identify the primary storage drive on the host machine."""
    if sys.platform == "win32":
        drive = os.getenv("SystemDrive", "C:") + "\\"
        if os.path.exists(drive):
            return drive
        return "C:\\"

    # Unix-like fallback
    return "/"


class SystemMonitor:
    """Polls real-time hardware metrics with safe fallback handling."""

    def __init__(self, main_drive: Optional[str] = None):
        self.main_drive = main_drive or get_main_drive()
        self.cached_os = get_os_info()
        self.cached_processor = get_processor_name()
        self.cached_installed_gpus = get_installed_gpus()

        # Cores count
        try:
            self.physical_cores = psutil.cpu_count(logical=False) or 1
            self.logical_cores = psutil.cpu_count(logical=True) or 1
        except Exception:
            self.physical_cores = 1
            self.logical_cores = 1

        # Check for nvidia-smi tool availability
        self._nvidia_smi_path = shutil.which("nvidia-smi")

        # Network speed tracking
        self._prev_net_time: Optional[float] = None
        self._prev_bytes_recv: Optional[int] = None
        self._prev_bytes_sent: Optional[int] = None

        # Disk I/O speed tracking
        self._prev_disk_time: Optional[float] = None
        self._prev_disk_read: Optional[int] = None
        self._prev_disk_write: Optional[int] = None

        # Prime CPU percent reading
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass

        # Prime network counters
        try:
            counters = psutil.net_io_counters()
            if counters:
                self._prev_bytes_recv = counters.bytes_recv
                self._prev_bytes_sent = counters.bytes_sent
                self._prev_net_time = time.time()
        except Exception:
            pass

        # Prime disk I/O counters
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io:
                self._prev_disk_read = disk_io.read_bytes
                self._prev_disk_write = disk_io.write_bytes
                self._prev_disk_time = time.time()
        except Exception:
            pass

    def _query_gpu(self) -> GpuMetrics:
        """Query GPU statistics using nvidia-smi with Windows Registry fallbacks."""
        gpu = GpuMetrics()
        installed = self.cached_installed_gpus

        if self._nvidia_smi_path:
            try:
                cmd = [
                    self._nvidia_smi_path,
                    "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
                    "--format=csv,noheader,nounits",
                ]
                flags = 0x08000000 if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
                out = subprocess.check_output(cmd, creationflags=flags, timeout=1.5).decode().strip()
                lines = [l.strip() for l in out.splitlines() if l.strip()]
                if lines:
                    parts = [p.strip() for p in lines[0].split(",")]
                    gpu.name = parts[0]
                    if len(parts) > 1 and parts[1].replace(".", "", 1).isdigit():
                        gpu.utilization_percent = float(parts[1])
                    if len(parts) > 2 and parts[2].replace(".", "", 1).isdigit():
                        gpu.vram_used_bytes = int(float(parts[2]) * 1024 * 1024)
                    if len(parts) > 3 and parts[3].replace(".", "", 1).isdigit():
                        gpu.vram_total_bytes = int(float(parts[3]) * 1024 * 1024)
                    if gpu.vram_total_bytes > 0:
                        gpu.vram_percent = (gpu.vram_used_bytes / gpu.vram_total_bytes) * 100.0
                    if len(parts) > 4 and parts[4].replace(".", "", 1).isdigit():
                        gpu.temp_c = float(parts[4])
                    if len(parts) > 5 and parts[5].replace(".", "", 1).isdigit():
                        gpu.power_watts = float(parts[5])

                    # Secondary GPUs (e.g. integrated graphics)
                    gpu.secondary_gpus = [g for g in installed if g != gpu.name]
                    return gpu
            except Exception:
                pass

        # Fallback to installed GPUs from Registry if nvidia-smi failed or not present
        if installed:
            gpu.name = installed[0]
            gpu.secondary_gpus = installed[1:]
        return gpu

    def collect(self) -> SystemMetrics:
        """Collect current system performance data across all components."""
        metrics = SystemMetrics(
            os_info=self.cached_os,
            processor_info=self.cached_processor,
            disk_drive=self.main_drive,
            cpu_physical_cores=self.physical_cores,
            cpu_logical_cores=self.logical_cores,
        )

        now = time.time()
        metrics.timestamp = now

        # 1. CPU Usage & Frequency
        try:
            metrics.cpu_percent = float(psutil.cpu_percent(interval=None))
        except Exception as err:
            metrics.errors.append(f"CPU: {err}")
            metrics.cpu_percent = 0.0

        try:
            freq = psutil.cpu_freq()
            if freq and freq.current > 0:
                metrics.cpu_freq_ghz = freq.current / 1000.0
        except Exception:
            pass

        # 2. GPU Usage
        try:
            metrics.gpu = self._query_gpu()
        except Exception as err:
            metrics.errors.append(f"GPU: {err}")

        # 3. RAM & Swap Memory
        try:
            mem = psutil.virtual_memory()
            metrics.ram_used_bytes = mem.used
            metrics.ram_total_bytes = mem.total
            metrics.ram_avail_bytes = mem.available
            metrics.ram_percent = float(mem.percent)
        except Exception as err:
            metrics.errors.append(f"RAM: {err}")

        try:
            swap = psutil.swap_memory()
            metrics.ram_swap_used_bytes = swap.used
            metrics.ram_swap_total_bytes = swap.total
            metrics.ram_swap_percent = float(swap.percent)
        except Exception:
            pass

        # 4. Disk Usage & Disk I/O Activity
        try:
            disk = psutil.disk_usage(self.main_drive)
            metrics.disk_used_bytes = disk.used
            metrics.disk_free_bytes = disk.free
            metrics.disk_total_bytes = disk.total
            metrics.disk_percent = float(disk.percent)
        except Exception as err:
            metrics.errors.append(f"Disk ({self.main_drive}): {err}")
            try:
                partitions = psutil.disk_partitions()
                if partitions:
                    alt_drive = partitions[0].mountpoint
                    disk = psutil.disk_usage(alt_drive)
                    metrics.disk_drive = alt_drive
                    metrics.disk_used_bytes = disk.used
                    metrics.disk_free_bytes = disk.free
                    metrics.disk_total_bytes = disk.total
                    metrics.disk_percent = float(disk.percent)
            except Exception:
                pass

        try:
            disk_io = psutil.disk_io_counters()
            if disk_io is not None:
                cur_read = disk_io.read_bytes
                cur_write = disk_io.write_bytes
                if (
                    self._prev_disk_time is not None
                    and self._prev_disk_read is not None
                    and self._prev_disk_write is not None
                ):
                    dt_disk = now - self._prev_disk_time
                    if dt_disk > 0.05:
                        metrics.disk_read_bytes_sec = max(0.0, (cur_read - self._prev_disk_read) / dt_disk)
                        metrics.disk_write_bytes_sec = max(0.0, (cur_write - self._prev_disk_write) / dt_disk)
                self._prev_disk_read = cur_read
                self._prev_disk_write = cur_write
                self._prev_disk_time = now
        except Exception:
            pass

        # 5. Network Usage & Cumulative Counters
        try:
            counters = psutil.net_io_counters()
            if counters is not None:
                cur_recv = counters.bytes_recv
                cur_sent = counters.bytes_sent
                metrics.net_total_recv_bytes = cur_recv
                metrics.net_total_sent_bytes = cur_sent

                if (
                    self._prev_net_time is not None
                    and self._prev_bytes_recv is not None
                    and self._prev_bytes_sent is not None
                ):
                    dt_net = now - self._prev_net_time
                    if dt_net > 0.05:
                        dl_delta = cur_recv - self._prev_bytes_recv
                        ul_delta = cur_sent - self._prev_bytes_sent
                        metrics.net_download_bytes_sec = max(0.0, dl_delta / dt_net)
                        metrics.net_upload_bytes_sec = max(0.0, ul_delta / dt_net)

                self._prev_bytes_recv = cur_recv
                self._prev_bytes_sent = cur_sent
                self._prev_net_time = now
        except Exception as err:
            metrics.errors.append(f"Network: {err}")

        # 6. System Uptime
        try:
            boot_time = psutil.boot_time()
            if boot_time > 0:
                metrics.uptime_seconds = max(0.0, now - boot_time)
        except Exception as err:
            metrics.errors.append(f"Uptime: {err}")

        # 7. Battery & Power Status
        try:
            battery = psutil.sensors_battery()
            if battery is not None:
                metrics.battery_percent = float(battery.percent)
                metrics.battery_plugged = bool(battery.power_plugged)
        except Exception:
            pass

        return metrics
