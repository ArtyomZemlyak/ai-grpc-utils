import logging

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)

import sys

sys.path.append("./")

from ai_grpc_utils.generators import serve

from examples.realization import TestRealization, PACKAGE_NAME


client = TestRealization()


serve(package_name=PACKAGE_NAME, ref_classes=[client])
