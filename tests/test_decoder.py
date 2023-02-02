# It is needed so that there are no errors with typing during runtime, when a reference to itself or a type/module is not imported.
from __future__ import annotations
import io
import json

import os
import time
import signal
from multiprocessing import Process

import sys
from typing import Any

sys.path.append("./")


def test_get_bytes_from_grpc_server():

    from ai_common_utils.files import convert_from, convert_to
    from ai_grpc_utils.generators import grpc_runner, connect_to_grpc_server, serve
    from ai_grpc_utils.decoders import StrToBytesDecoder as Decoder

    PACKAGE_NAME = "ai_gu_serialization"

    class RealizationDecoder:
        def __init__(self) -> None:
            self.grpc_client = None

        def connect_to_grpc_server(self, host: str = "localhost", port: str = "50052"):
            self.grpc_client = connect_to_grpc_server(
                cls=self,
                package_name=PACKAGE_NAME,
                host=host,
                port=port,
            )

        @grpc_runner(decoder=Decoder)
        def process(self, arg: str):
            return f"Processed! ({arg=})"

    def serving():
        client = RealizationDecoder()
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

    def get_bytes_from_grpc_server():
        time.sleep(1)
        proc = run_server()

        GRPC_HOST = "localhost"
        GRPC_PORT = "50052"

        esa = RealizationDecoder()

        esa.connect_to_grpc_server(
            host=GRPC_HOST,
            port=GRPC_PORT,
        )

        res = esa.process("Some text")

        shutdown_server(proc)

        assert res == b"Processed! (arg='Some text')"

    get_bytes_from_grpc_server()


if __name__ == "__main__":
    test_get_bytes_from_grpc_server()
