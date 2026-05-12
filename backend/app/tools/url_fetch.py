from urllib.parse import urlparse

import httpx
import trafilatura


async def fetch_url_as_text(url: str, timeout_s: float = 15.0, max_bytes: int = 2_000_000) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("invalid scheme")

    headers = {"User-Agent": "agent-room/0.1"}
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=timeout_s,
        headers=headers,
    ) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").split(";")[0].lower()
            if not (content_type.startswith("text/") or content_type == "application/xhtml+xml"):
                raise ValueError("unsupported content-type")

            chunks: list[bytes] = []
            total = 0
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError("too large")
                chunks.append(chunk)

    html = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
    extracted = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        no_fallback=False,
    )
    text = extracted or html
    return f"# {url}\n\n{text[:20000]}"
