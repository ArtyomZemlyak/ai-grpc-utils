"""
File contains example for gRPC server realization using ai-grpc-utils.generation.
"""

# It is needed so that there are no errors with typing during runtime, when a reference to itself or a type/module is not imported.
from __future__ import annotations

from ai_grpc_utils.generators import grpc_runner, connect_to_grpc_server


PACKAGE_NAME = "ai_grpc_utils_server_test"


class TestRealization:
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
