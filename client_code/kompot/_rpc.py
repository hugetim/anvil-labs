# SPDX-License-Identifier: MIT
# Copyright (c) 2021 anvilistas
import json as _json
from functools import wraps as _wraps

import anvil.server as _server
from anvil import is_server_side

from ._serialize import UNHANDLED, reconstruct, serialize

__version__ = "0.0.1"


def _dumps(obj):
    serialized = serialize(obj)
    unhandled = serialized.pop(UNHANDLED)
    return _json.dumps(serialized), unhandled


def _loads(serialized, unhandled):
    obj = _json.loads(serialized)
    obj[UNHANDLED] = unhandled
    return reconstruct(obj)


def call(fn_name, *args, **kws):
    rv = _server.call(fn_name, *_dumps([args, kws]))
    return _loads(*rv)


def call_s(fn_name, *args, **kws):
    rv = _server.call_s(fn_name, *_dumps([args, kws]))
    return _loads(*rv)


def callable(fn):
    @_wraps(fn)
    def wrapped(json_obj, unhandled):
        args, kws = _loads(json_obj, unhandled)
        rv = fn(*args, **kws)
        return _dumps(rv)

    return _server.callable(wrapped)


def call_async(fn_name, *args, **kws):
    from .. import non_blocking

    # non_blocking is client side only
    # we don't want this import to be top level if we're on the server

    return non_blocking.call_async(call_s, fn_name, *args, **kws)
