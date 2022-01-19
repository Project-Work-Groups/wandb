"""Router - handle message router (queue)

Router to manage responses from a queue.

"""

import queue
from typing import Optional
from typing import TYPE_CHECKING

from .router import MessageRouter
from ..lib import debug_log

if TYPE_CHECKING:
    from queue import Queue
    from wandb.proto import wandb_internal_pb2 as pb


class MessageQueueRouter(MessageRouter):
    _request_queue: "Queue[pb.Record]"
    _response_queue: "Queue[pb.Result]"

    def __init__(
        self, request_queue: "Queue[pb.Record]", response_queue: "Queue[pb.Result]"
    ) -> None:
        self._request_queue = request_queue
        self._response_queue = response_queue
        super(MessageQueueRouter, self).__init__()

    def _read_message(self) -> "Optional[pb.Result]":
        try:
            msg = self._response_queue.get(timeout=1)
        except queue.Empty:
            return None
        debug_log.log_message_dequeue(msg, self._response_queue)
        return msg

    def _send_message(self, record: "pb.Record") -> None:
        debug_log.log_message_queue(record, self._request_queue)
        self._request_queue.put(record)
