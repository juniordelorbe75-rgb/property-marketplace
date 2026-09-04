import json


DEFAULT_BODY_LIMIT = 1 * 1024 * 1024
IMAGE_UPLOAD_BODY_LIMIT = 8 * 1024 * 1024
BODY_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class RequestBodyLimitMiddleware:
    """Reject oversized write bodies before validation or route processing."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") not in BODY_METHODS:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        limit = (
            IMAGE_UPLOAD_BODY_LIMIT
            if path == "/uploads/property-images"
            else DEFAULT_BODY_LIMIT
        )
        content_length = _content_length(scope.get("headers", []))
        if content_length is not None and content_length > limit:
            await _send_too_large(send, limit)
            return

        buffered_messages = []
        total = 0
        while True:
            message = await receive()
            buffered_messages.append(message)
            if message["type"] == "http.disconnect":
                break
            if message["type"] != "http.request":
                continue
            total += len(message.get("body", b""))
            if total > limit:
                await _send_too_large(send, limit)
                return
            if not message.get("more_body", False):
                break

        message_index = 0

        async def replay_receive():
            nonlocal message_index
            if message_index < len(buffered_messages):
                message = buffered_messages[message_index]
                message_index += 1
                return message
            return {"type": "http.disconnect"}

        await self.app(scope, replay_receive, send)


def _content_length(headers) -> int | None:
    for key, value in headers:
        if key.lower() != b"content-length":
            continue
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0 else None
    return None


async def _send_too_large(send, limit: int) -> None:
    body = json.dumps({
        "detail": f"Request body is too large. Maximum size is {limit // (1024 * 1024)} MB."
    }).encode()
    await send({
        "type": "http.response.start",
        "status": 413,
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
            (b"cache-control", b"no-store"),
        ],
    })
    await send({"type": "http.response.body", "body": body})
