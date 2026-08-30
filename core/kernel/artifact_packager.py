# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — ARTIFACT PACKAGER & DELIVERY ENGINE v2.0         ║
║   Đóng Gói Giao Hàng Chuyên Nghiệp, Checksums & TTL Janitor      ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Tối Ưu Hóa Giao Hàng & Bằng Chứng Toàn Vẹn. 📦🏛️⚡*
"""

from __future__ import annotations
import os
import shutil
import time
import json
import zipfile
import hashlib
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from core.kernel.decision_ledger import decision_ledger

logger = logging.getLogger("JKAI.ArtifactPackager")


@dataclass
class DeliveryPackage:
    package_id: str
    task_id: str
    package_dir: str
    manifest_path: str
    zip_path: Optional[str]
    artifact_files: List[str]
    file_checksums: Dict[str, str]
    total_size_bytes: int
    created_at: float = field(default_factory=time.time)


class ArtifactPackager:
    """
    📦 Bộ Đóng Gói Sản Phẩm Đầu Ra (Artifact Packaging & Delivery Engine) v2.0
    - Gom nhóm toàn bộ tệp tin được sinh ra vào thư mục giao hàng.
    - Sinh file `manifest.json` chứa mã băm SHA-256 từng file.
    - Tự động nén `.zip` nếu có nhiều hơn 1 tệp tin.
    - Cơ chế TTL Janitor tự động dọn dẹp các packages cũ quá hạn.
    - Ghi nhận lịch sử bàn giao vào DecisionLedger.
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
        self.default_packages_dir = os.path.join(os.getcwd(), "workspace", "outputs", "packages")

    def package_artifacts(
        self,
        task_id: str,
        artifact_paths: List[str],
        output_base_dir: Optional[str] = None
    ) -> DeliveryPackage:
        """
        Đóng gói danh sách tệp tin vào package giao hàng hoàn chỉnh.
        """
        import uuid
        pkg_id = f"pkg_{uuid.uuid4().hex[:12]}"
        base_dir = output_base_dir or os.path.join(self.default_packages_dir, pkg_id)
        os.makedirs(base_dir, exist_ok=True)

        checksums = {}
        valid_files = []
        total_size = 0

        # 1. Tính toán checksums cho từng artifact
        for fpath in artifact_paths:
            if fpath and os.path.exists(fpath):
                valid_files.append(fpath)
                fsize = os.path.getsize(fpath)
                total_size += fsize
                with open(fpath, "rb") as f:
                    fhash = hashlib.sha256(f.read()).hexdigest()
                checksums[os.path.basename(fpath)] = fhash

        # 2. Sinh Manifest JSON
        manifest_data = {
            "package_id": pkg_id,
            "task_id": task_id,
            "created_at": time.time(),
            "file_count": len(valid_files),
            "total_size_bytes": total_size,
            "files": checksums
        }
        manifest_path = os.path.join(base_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)

        # 3. Tạo file Zip nếu có nhiều file
        zip_path = None
        if len(valid_files) > 1:
            zip_path = os.path.join(base_dir, f"delivery_{task_id}.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for vf in valid_files:
                    zipf.write(vf, os.path.basename(vf))
                zipf.write(manifest_path, "manifest.json")

        pkg = DeliveryPackage(
            package_id=pkg_id,
            task_id=task_id,
            package_dir=base_dir,
            manifest_path=manifest_path,
            zip_path=zip_path,
            artifact_files=valid_files,
            file_checksums=checksums,
            total_size_bytes=total_size
        )

        # 4. Ghi nhận vào DecisionLedger
        decision_ledger.record_decision(
            decision_type="ARTIFACT_PACKAGING",
            task_id=task_id,
            input_summary=f"Artifacts count: {len(valid_files)}",
            output_decision=f"Package ID: {pkg_id}",
            reason="Đóng gói hoàn tất với SHA-256 Manifest.",
            metadata={"package_id": pkg_id, "files": list(checksums.keys())}
        )

        logger.info(f"[ARTIFACT-PACKAGER]: Đã đóng gói {len(valid_files)} tệp tin cho task '{task_id}' -> Package: '{pkg_id}'.")
        return pkg

    def cleanup_expired_packages(self, max_age_days: float = 7.0, target_dir: Optional[str] = None) -> int:
        """
        🧹 TTL Janitor: Dọn dẹp các thư mục package cũ hơn max_age_days.
        Trả về số lượng package đã được giải phóng.
        """
        root_dir = target_dir or self.default_packages_dir
        if not os.path.exists(root_dir):
            return 0

        now = time.time()
        max_age_seconds = max_age_days * 86400.0
        cleaned_count = 0

        for entry in os.listdir(root_dir):
            entry_path = os.path.join(root_dir, entry)
            if os.path.isdir(entry_path) and entry.startswith("pkg_"):
                manifest_file = os.path.join(entry_path, "manifest.json")
                pkg_time = os.path.getmtime(entry_path)
                
                if os.path.exists(manifest_file):
                    try:
                        with open(manifest_file, "r", encoding="utf-8") as f:
                            m_data = json.load(f)
                            pkg_time = m_data.get("created_at", pkg_time)
                    except Exception:
                        pass

                if now - pkg_time > max_age_seconds:
                    try:
                        shutil.rmtree(entry_path, ignore_errors=True)
                        cleaned_count += 1
                        logger.info(f"[TTL-JANITOR]: Đã dọn dẹp package hết hạn: '{entry}'.")
                    except Exception as e:
                        logger.error(f"[TTL-JANITOR]: Lỗi xóa '{entry}': {e}")

        return cleaned_count


artifact_packager = ArtifactPackager()
