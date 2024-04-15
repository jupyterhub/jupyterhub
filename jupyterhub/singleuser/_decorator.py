from typing import Any, Callable, TypeVar

try:
    from jupyter_server.auth.decorator import allow_unauthenticated
except ImportError:
    FuncT = TypeVar("FuncT", bound=Callable[..., Any])

    # if using an older jupyter-server version this can be a no-op,
    # as these do not support marking endpoints anyways
    def allow_unauthenticated(method: FuncT) -> FuncT:
        return method


__all__ = ["allow_unauthenticated"]
