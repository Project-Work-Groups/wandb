import datetime
from typing import Deque, List, Tuple, TypeVar

try:
    from typing import Literal, Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Literal, Protocol, runtime_checkable


TimeStamp = TypeVar("TimeStamp", bound=datetime.datetime)
Reading = TypeVar("Reading", float, int, str, bytes, list, tuple, dict)
MetricType = Literal["counter", "gauge", "histogram", "summary"]
# MetricType = Literal["gauge"]


class Metric(Protocol):
    name: str
    # at first, we will only support the gauge type
    metric_type: MetricType
    #
    readings: Deque[Tuple[TimeStamp, Reading]]

    def sample(self) -> None:
        ...

    def serialize(self) -> dict:
        ...


@runtime_checkable
class Asset(Protocol):
    # Base protocol to encapsulate everything relating to e.g. CPU, GPU, TPU, Network, I/O etc.
    # A collection of metrics.
    # - Use typing.Protocol’s to define and gently enforce interfaces
    # - poll method to collect metrics with a customizable polling interval
    # - Auto-discover stuff at startup to track metrics automatically
    # - Provide a class method to (lazily) construct a resource from a Prometheus?
    #   (and later other providers?) endpoint: poll once
    name: str
    metrics: List[Metric]
    # polling_interval: float = 1.0

    def probe(cls) -> dict:
        ...

    def poll(self) -> None:
        ...

    def serialize(self) -> dict:
        ...
