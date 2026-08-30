# -*- coding: utf-8 -*-
"""
🌱 [ENERGY-AWARE & CARBON-AWARE SCHEDULER v1.0]
File: core/energy/green_scheduler.py

Bộ Điều Phối Xanh & Tối Ưu Hóa Năng Lượng (Trụ Cột 11):
  1. Adaptive Energy Modes: Chế độ Siêu Tốc (TURBO) vs Chế độ Xanh (ECO_GREEN ban đêm).
  2. Power Capping & Batching: Giới hạn tải CPU ban đêm cho các tác vụ compact/học nền.
  3. Carbon Footprint Estimator: Đo lường mức tiêu thụ điện năng (kWh) và dấu chân carbon.
"""

import time
import datetime
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

logger = logging.getLogger("JKAI.GreenEnergy")


class EnergyProfile(Enum):
    TURBO_PERFORMANCE = "TURBO"  # Tối đa công suất (Ban ngày / Tác vụ khẩn cấp)
    BALANCED = "BALANCED"        # Cân bằng tối ưu
    ECO_GREEN = "ECO_GREEN"      # Tiết kiệm điện (Ban đêm / Giờ cao điểm)


@dataclass
class EnergyConsumptionMetrics:
    total_inferences: int = 0
    total_cpu_seconds: float = 0.0
    estimated_kwh_consumed: float = 0.0
    estimated_co2_grams: float = 0.0


class GreenEnergyScheduler:
    """
    🌱 Bộ Điều Phối Năng Lượng & AI Bền Vững
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.metrics = EnergyConsumptionMetrics()
        # Hệ số ước lượng tiêu thụ điện năng cho máy Xeon 22 Cores (TDP ~145W)
        self._watts_per_core_hour = 6.5
        self._grams_co2_per_kwh = 400.0  # Mức trung bình lưới điện

    def get_recommended_energy_mode(self, override_mode: Optional[str] = None) -> EnergyProfile:
        """
        Tự động xác định chế độ năng lượng dựa trên thời gian thực tế.
        Ban đêm (23h - 05h): Chuyển sang ECO_GREEN để tiết kiệm điện.
        """
        if override_mode:
            try:
                return EnergyProfile(override_mode.upper())
            except ValueError:
                pass

        current_hour = datetime.datetime.now().hour
        if 23 <= current_hour or current_hour <= 5:
            return EnergyProfile.ECO_GREEN
        return EnergyProfile.TURBO_PERFORMANCE

    def get_max_worker_threads_budget(self) -> int:
        """Tính toán số luồng CPU cho phép sử dụng dựa trên hồ sơ năng lượng."""
        mode = self.get_recommended_energy_mode()
        if mode == EnergyProfile.ECO_GREEN:
            return 8   # Giới hạn 8 luồng ban đêm
        elif mode == EnergyProfile.BALANCED:
            return 16  # 16 luồng
        return 20      # 20 luồng công suất tối đa trên Xeon

    def record_compute_energy(self, cpu_duration_seconds: float, thread_count: int = 4) -> None:
        """Ghi nhận mức năng lượng tiêu thụ của một tác vụ."""
        self.metrics.total_inferences += 1
        self.metrics.total_cpu_seconds += cpu_duration_seconds

        # Tính kWh = (Công suất Watts * Số giờ) / 1000
        watts = thread_count * self._watts_per_core_hour
        kwh = (watts * (cpu_duration_seconds / 3600.0)) / 1000.0
        self.metrics.estimated_kwh_consumed += kwh
        self.metrics.estimated_co2_grams += kwh * self._grams_co2_per_kwh

    def get_carbon_telemetry(self) -> Dict[str, Any]:
        """Xuất báo cáo xanh về môi trường."""
        return {
            "mode": self.get_recommended_energy_mode().value,
            "allocated_threads": self.get_max_worker_threads_budget(),
            "total_cpu_seconds": round(self.metrics.total_cpu_seconds, 2),
            "estimated_kwh": round(self.metrics.estimated_kwh_consumed, 6),
            "estimated_co2_grams": round(self.metrics.estimated_co2_grams, 4),
            "is_eco_active": self.get_recommended_energy_mode() == EnergyProfile.ECO_GREEN
        }


green_scheduler = GreenEnergyScheduler()
