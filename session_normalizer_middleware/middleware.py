# Custom Middleware for Coercing Session Data into Serializable Formats
#
# The following is the original copyright notice for Starlette, from which the
# proceeding code is mostly derived:
# https://github.com/encode/starlette/blob/master/LICENSE.md
#
# Copyright © 2018, Encode OSS Ltd. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted
# provided that the following conditions are met:
#
# Redistributions of source code must retain the above copyright notice, this list of conditions
# and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright notice, this list of conditions
# and the following disclaimer in the documentation and/or other materials provided with the distribution.
#
# Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote
# products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


from fasthtml.core import MiddlewareBase
from fastcore.basics import AttrDict
from starlette.requests import HTTPConnection
from starlette.datastructures import MutableHeaders
from itsdangerous import BadSignature
from base64 import b64decode, b64encode
import json
from typing import Optional, Callable, any


def _session_normalize(obj: any):
    if isinstance(obj, list):
        return [_session_normalize(o) for o in obj]
    elif isinstance(obj, dict):
        return {
            _session_normalize(key): _session_normalize(val)
            for key, val in obj.items()
        }
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif hasattr(obj, "__json__"):
        return obj.__json__()
    elif hasattr(obj, "__str__"):
        return str(obj)
    elif hasattr(obj, "__dict__"):
        return obj.__dict__
    raise TypeError(
        f"Object of type {obj.__class__.__name__} is not JSON serializable"
    )


class SessionNormalizerMiddleware(MiddlewareBase):
    """
    Provides automatic coercion of stored data inside Starlette Session objects.
    Intended to be used with FastHTML as an optional replacement for its own
    default SessionMiddleware class.
    Allows users to provide objects like UUIDs or custom dataclasses that might
    be coercible to a data format capable of being easily serialized.
    """

    def __init__(self, app, normalizer: Optional[Callable] = None):
        """
        Args:
        `normalizer`: an optional Callable that serves as a drop-in replacement
        for the default normalization strategy. Should be designed to act on
        and return a serializable value for each individual key and value
        in the session dictionary.
        """
        self.app = app
        self.normalizer = normalizer

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] not in ("http", "websocket"):  # pragma: no cover
            await self.app(scope, receive, send)
            return

        connection = HTTPConnection(scope)
        initial_session_was_empty = True

        if self.session_cookie in connection.cookies:
            data = connection.cookies[self.session_cookie].encode("utf-8")
            try:
                data = self.signer.unsign(data, max_age=self.max_age)
                scope["session"] = json.loads(b64decode(data))
                initial_session_was_empty = False
            except BadSignature:
                scope["session"] = {}
        else:
            scope["session"] = {}

        async def receive_wrapper():
            message = await receive()
            if "session" in scope and not isinstance(
                scope["session"], AttrDict
            ):
                scope["session"] = AttrDict(scope["session"])
            return message

        async def send_wrapper(message) -> None:
            if message["type"] == "http.response.start":
                if scope["session"]:
                    for key, val in scope["session"].items():
                        scope["session"][_session_normalize(key)] = (
                            _session_normalize(val)
                            if not self.normalizer
                            else self.normalizer(val)
                        )
                    data = b64encode(
                        json.dumps(scope["session"]).encode("utf-8")
                    )
                    data = self.signer.sign(data)
                    headers = MutableHeaders(scope=message)
                    header_value = "{session_cookie}={data}; path={path}; {max_age}{security_flags}".format(  # noqa E501
                        session_cookie=self.session_cookie,
                        data=data.decode("utf-8"),
                        path=self.path,
                        max_age=(
                            f"Max-Age={self.max_age}; " if self.max_age else ""
                        ),
                        security_flags=self.security_flags,
                    )
                    headers.append("Set-Cookie", header_value)
                elif not initial_session_was_empty:
                    headers = MutableHeaders(scope=message)
                    header_value = "{session_cookie}={data}; path={path}; {expires}{security_flags}".format(  # noqa E501
                        session_cookie=self.session_cookie,
                        data="null",
                        path=self.path,
                        expires="expires=Thu, 01 Jan 1970 00:00:00 GMT; ",
                        security_flags=self.security_flags,
                    )
                    headers.append("Set-Cookie", header_value)
            await send(message)

        await self.app(scope, receive_wrapper, send_wrapper)
