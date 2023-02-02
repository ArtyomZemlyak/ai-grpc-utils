import inspect
import os
import json
import logging
import dataclasses
from functools import wraps, partial
import pathlib
from typing import List, Type, Union
from concurrent import futures

from grpc_tools import protoc
import grpc

from ai_common_utils.json import NumpyEncoder


def get_decorated_methods(cls: List[Type], decorator_tag: str = "grpc_runner") -> set:
    if type(cls) != list:
        class_instancies = [cls]
    else:
        class_instancies = cls

    return {
        name
        # get all attributes, including methods, properties, and builtins
        for class_instance in class_instancies
        for name in dir(class_instance)
        # but we only want methods
        if callable(getattr(class_instance, name))
        # and we don't need builtins
        and not name.startswith("__")
        # and we only want the cool methods
        and hasattr(getattr(class_instance, name), decorator_tag)
    }


def get_protos_and_services(cls: List[Type], package_name: str):
    grpc_methods = get_decorated_methods(cls)

    proto_funcs = "".join(
        f"rpc {func_name}(DataSendRequest) returns (DataResponse);\n"
        for func_name in grpc_methods
    )

    PROTO = f"""syntax = "proto3";
    package {package_name};


    message DataSendRequest{{
        string data = 1;
    }}

    message DataResponse{{
        string data = 1;
    }}

    message Empty {{

    }}

    service {package_name}gRPC{{
    {proto_funcs}
    }}
    """

    PROTO_NAME = f"{package_name}_messages_gen.proto"
    path_executor = pathlib.Path(
        os.path.abspath(inspect.stack()[-1].filename)
    ).parent.resolve()
    PROTO_PATH = os.path.join(path_executor, PROTO_NAME)

    with open(PROTO_PATH, "w") as f:
        f.write(PROTO)

    protos, services = protoc._protos_and_services(PROTO_NAME)

    os.remove(PROTO_PATH)

    return (protos, services)


GRPC_PROTOS = None
GRPC_SERVICES = None


def grpc_runner(func=None, encoder=None, decoder=None):
    """
    Use for send function execution to remote server (gRPC).
    """
    if func is None:
        return partial(grpc_runner, encoder=encoder, decoder=decoder)

    global GRPC_PROTOS
    func.grpc_runner = True

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.grpc_client:
            logging.info(f"Run grpc function {func.__name__}.")
            data = {
                "args": args,
                "kwargs": kwargs,
            }
            grpc_func = getattr(self.grpc_client, func.__name__)
            try:
                request = GRPC_PROTOS.DataSendRequest(
                    data=json.dumps(data, cls=encoder)
                )
                response: GRPC_PROTOS.DataResponse = grpc_func(request)
                result = json.loads(response.data)
                if decoder:
                    decoder_exe = decoder()
                    result = decoder_exe(result)
                return result
            except Exception as e:
                logging.error(f"Fail to compute {func.__name__} gRPC function: {e}")
                return {"error": e}
        else:
            return func(self, *args, **kwargs)

    return wrapper


def connect_to_grpc_server(
    cls: Union[Type, List[Type]],
    package_name: str,
    host: str = "localhost",
    port: str = "50051",
):
    """
    Connect to specific grpc server.

    Parameters
    ----------
    cls: Union[Type, List[Type]]
        Types to generate client.

    package_name: str
        Need for appropriate generating proto.

    host: str, optional, default="localhost"
        Str host of grpc server.

    port: str, optional, default="50051"
        Str port of grpc server.

    Returns
    -------
    grpc_client: gRPCStub
        gRPC client for gRPC server.
    """
    global GRPC_PROTOS
    global GRPC_SERVICES
    GRPC_PROTOS, GRPC_SERVICES = get_protos_and_services(cls, package_name)
    grpc_stub = getattr(GRPC_SERVICES, f"{package_name}gRPCStub")

    logging.info(f"{package_name}gRPC: prepeare connection to grpc server...")

    GRPC_HOST = os.environ.get("GRPC_HOST", host)
    GRPC_PORT = os.environ.get("GRPC_PORT", port)

    connection_string = f"{GRPC_HOST}:{GRPC_PORT}"

    channel_opt = [
        ("grpc.max_send_message_length", 1024 * 1024 * 1024),
        ("grpc.max_receive_message_length", 1024 * 1024 * 1024),
    ]
    grpc_client = grpc_stub(
        grpc.insecure_channel(connection_string, options=channel_opt)
    )

    logging.info(
        f"{package_name}gRPC: Prepearing connection to grpc server done! (its not opened directly connection!)"
    )
    return grpc_client


DataResponse = None


def template(self, request, context, cls_func):
    global DataResponse
    req_data = json.loads(request.data)
    data = cls_func(*req_data["args"], **req_data["kwargs"])
    return DataResponse(data=json.dumps(data, cls=NumpyEncoder))


def func(self, cls_func):
    funcs = lambda request, context: template(self, request, context, cls_func)
    return funcs


def create_service(service_name, ref_cls):
    if type(ref_cls) != list:
        ref_cls = [ref_cls]

    cls_methods = get_decorated_methods(ref_cls)

    existed_fields = set([])

    fields = [
        (
            name,
            existed_fields.add(name),
            dataclasses.field(default=func(ref, getattr(ref, name))),
        )
        for ref in ref_cls
        for name in dir(ref)
        if name in cls_methods and name not in existed_fields
    ]

    new_cls = dataclasses.make_dataclass(service_name, fields=fields)
    return new_cls


def serve(
    package_name: str,
    ref_classes: List[Type],
    host: str = "localhost",
    port: str = "50052",
    **kwargs,
):
    """
    Connect to specific grpc server.

    Parameters
    ----------
    package_name: str
        Need for appropriate generating proto.

    ref_classes: Union[Type, List[Type]]
        Types to generate server.
    """
    global DataResponse
    PACKAGE_NAME = package_name
    REF_CLASSES = ref_classes

    GRPC_HOST = os.environ.get("GRPC_HOST", host)
    GRPC_PORT = os.environ.get("GRPC_PORT", port)

    protos, services = get_protos_and_services(REF_CLASSES, package_name=PACKAGE_NAME)

    DataResponse = protos.DataResponse

    channel_opt = [
        ("grpc.max_send_message_length", 1024 * 1024 * 1024),
        ("grpc.max_receive_message_length", 1024 * 1024 * 1024),
    ]
    if "options" not in kwargs:
        kwargs["options"] = channel_opt
    else:
        kwargs["options"].extend(channel_opt)

    server = grpc.server(futures.ThreadPoolExecutor(), **kwargs)

    adder = getattr(services, f"add_{PACKAGE_NAME}gRPCServicer_to_server")

    ServerService = create_service("ServerService", ref_classes)

    adder(ServerService(), server)

    server.add_insecure_port(f"{GRPC_HOST}:{GRPC_PORT}")
    logging.info(f"{PACKAGE_NAME}: Sarting gRPC server...")
    server.start()
    logging.info(f"{PACKAGE_NAME}: Server started! port={GRPC_PORT}")
    server.wait_for_termination()
