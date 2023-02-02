from typing import Any


class StrToBytesDecoder:
    def __call__(self, result: str, *args: Any, **kwds: Any) -> Any:
        return result.encode("utf-8")
