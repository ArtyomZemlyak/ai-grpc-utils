import sys

sys.path.append("./")

from examples.realization import TestRealization


GRPC_HOST = "localhost"
GRPC_PORT = "50052"


esa = TestRealization()

esa.connect_to_grpc_server(
    host=GRPC_HOST,
    port=GRPC_PORT,
)

res = esa.process("Some text")

print(res)
