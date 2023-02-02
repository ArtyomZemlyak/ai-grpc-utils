import io
import json

import numpy as np
from ai_common_utils.files import convert_to


class BytesEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return convert_to(obj, ["base64", "json"])
        if isinstance(obj, io.BytesIO):
            return convert_to(obj.getvalue(), ["base64", "json"])
        return json.JSONEncoder.default(self, obj)


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, float):
            return str(obj)
        return json.JSONEncoder.default(self, obj)
