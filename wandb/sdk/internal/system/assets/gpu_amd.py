import json
import logging
import shutil
import subprocess
import sys
import threading
from collections import deque
from typing import TYPE_CHECKING, Any, Dict, List, Union

if sys.version_info >= (3, 8):
    from typing import Final, TypedDict
else:
    from typing_extensions import Final, TypedDict

from wandb.sdk.lib import telemetry

from .aggregators import aggregate_mean
from .asset_registry import asset_registry
from .interfaces import Interface, Metric, MetricsMonitor

if TYPE_CHECKING:
    from typing import Deque

    from wandb.sdk.internal.settings_static import SettingsStatic


logger = logging.getLogger(__name__)


ROCM_SMI_CMD: Final[str] = shutil.which("rocm-smi") or "/usr/bin/rocm-smi"


def get_rocm_smi_stats() -> Dict[str, Any]:
    command = [str(ROCM_SMI_CMD), "-a", "--json"]
    output = (
        subprocess.check_output(command, universal_newlines=True).strip().split("\n")
    )[0]
    return json.loads(output)  # type: ignore


class _Stats(TypedDict):
    gpu: float
    memoryAllocated: float  # noqa: N815
    temp: float
    powerWatts: float  # noqa: N815
    powerPercent: float  # noqa: N815


_InfoDict = Dict[str, Union[int, List[Dict[str, Any]]]]


class GPUAMDStats:
    """Stats for AMD GPU devices."""

    name = "gpu.{gpu_id}.{key}"
    samples: "Deque[List[_Stats]]"

    def __init__(self) -> None:
        self.samples = deque()

    def sample(self) -> None:
        try:
            raw_stats = get_rocm_smi_stats()
            cards = []

            for key in sorted(raw_stats.keys()):
                if not key.startswith("card"):
                    continue
                card_stats = raw_stats[key]

                stats: _Stats = {
                    "gpu": float(card_stats["GPU use (%)"]),
                    "memoryAllocated": float(card_stats["GPU memory use (%)"]),
                    "temp": float(card_stats["Temperature (Sensor memory) (C)"]),
                    "powerWatts": float(
                        card_stats["Average Graphics Package Power (W)"]
                    ),
                    "powerPercent": (
                        float(card_stats["Average Graphics Package Power (W)"])
                        / float(card_stats["Max Graphics Package Power (W)"])
                        * 100
                    ),
                }

                cards.append(stats)

            self.samples.append(cards)

        except (OSError, ValueError, TypeError, subprocess.CalledProcessError) as e:
            logger.exception(f"GPU stats error: {e}")

    def clear(self) -> None:
        self.samples.clear()

    def aggregate(self) -> dict:
        if not self.samples:
            return {}
        stats = {}
        device_count = len(self.samples[0])

        for i in range(device_count):
            samples = [sample[i] for sample in self.samples]

            for key in samples[0].keys():
                samples_key = [s[key] for s in samples]  # type: ignore
                aggregate = aggregate_mean(samples_key)
                stats[self.name.format(gpu_id=i, key=key)] = aggregate

        return stats


@asset_registry.register
class GPUAMD:
    """GPUAMD is a class for monitoring AMD GPU devices.

    Uses AMD's rocm_smi tool to get GPU stats.
    For the list of supported environments and devices, see
    https://github.com/RadeonOpenCompute/ROCm/blob/develop/docs/deploy/
    """

    def __init__(
        self,
        interface: "Interface",
        settings: "SettingsStatic",
        shutdown_event: threading.Event,
    ) -> None:
        self.name = self.__class__.__name__.lower()
        self.metrics: List[Metric] = [
            GPUAMDStats(),
        ]
        self.metrics_monitor = MetricsMonitor(
            self.name,
            self.metrics,
            interface,
            settings,
            shutdown_event,
        )
        telemetry_record = telemetry.TelemetryRecord()
        telemetry_record.env.amd_gpu = True
        interface._publish_telemetry(telemetry_record)

    @classmethod
    def is_available(cls) -> bool:
        rocm_smi_available = shutil.which(ROCM_SMI_CMD) is not None
        if rocm_smi_available:
            try:
                _ = get_rocm_smi_stats()
                return True
            except Exception:
                pass
        return False

    def start(self) -> None:
        self.metrics_monitor.start()

    def finish(self) -> None:
        self.metrics_monitor.finish()

    def probe(self) -> dict:
        info: _InfoDict = {}
        try:
            stats = get_rocm_smi_stats()

            info["gpu_count"] = len(
                [key for key in stats.keys() if key.startswith("card")]
            )
            key_mapping = {
                "id": "GPU ID",
                "unique_id": "Unique ID",
                "vbios_version": "VBIOS version",
                "performance_level": "Performance Level",
                "gpu_overdrive": "GPU OverDrive value (%)",
                "gpu_memory_overdrive": "GPU Memory OverDrive value (%)",
                "max_power": "Max Graphics Package Power (W)",
                "series": "Card series",
                "model": "Card model",
                "vendor": "Card vendor",
                "sku": "Card SKU",
                "sclk_range": "Valid sclk range",
                "mclk_range": "Valid mclk range",
            }

            info["gpu_devices"] = [
                {k: stats[key][v] for k, v in key_mapping.items() if stats[key].get(v)}
                for key in stats.keys()
                if key.startswith("card")
            ]
        except Exception as e:
            logger.exception(f"GPUAMD probe error: {e}")
        return info
