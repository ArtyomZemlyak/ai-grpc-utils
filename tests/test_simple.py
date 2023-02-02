# It is needed so that there are no errors with typing during runtime, when a reference to itself or a type/module is not imported.
from __future__ import annotations

import os
import time
import signal
from multiprocessing import Process

import sys

sys.path.append("./")

from ai_grpc_utils.generators import grpc_runner, connect_to_grpc_server, serve


PACKAGE_NAME = "ai_gu_simple"


class RealizationSimple:
    def __init__(self) -> None:
        self.grpc_client = None

    def connect_to_grpc_server(self, host: str = "localhost", port: str = "50052"):
        self.grpc_client = connect_to_grpc_server(
            cls=self,
            package_name=PACKAGE_NAME,
            host=host,
            port=port,
        )

    @grpc_runner
    def process(self, arg: str):
        return f"Processed! ({arg=})"


def serving():
    client = RealizationSimple()
    serve(package_name=PACKAGE_NAME, ref_classes=[client])


def run_server(wait: int = 2) -> Process:
    proc = Process(
        target=serving,
        args=(),
        kwargs={},
    )
    proc.start()
    time.sleep(wait)
    assert proc.is_alive()
    return proc


def shutdown_server(proc: Process):
    os.kill(proc.pid, signal.SIGINT)
    for _ in range(5):
        if proc.is_alive():
            time.sleep(1)
        else:
            return
    else:
        raise Exception("Process still alive")


def test_processing_on_grpc_server():
    time.sleep(1)
    proc = run_server()

    GRPC_HOST = "localhost"
    GRPC_PORT = "50052"

    esa = RealizationSimple()

    esa.connect_to_grpc_server(
        host=GRPC_HOST,
        port=GRPC_PORT,
    )

    res = esa.process("Some text")

    shutdown_server(proc)

    assert res == "Processed! (arg='Some text')"
