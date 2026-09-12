import json
from urllib.parse import urlparse

import requests

DISCORD_DESCRIPTION_LIMIT = 4096
LARK_REQUEST_BODY_LIMIT = 25_000


def _is_domain(hostname, domain):
    return hostname == domain or hostname.endswith(f".{domain}")


def detect_webhook_type(webhook_url):
    hostname = (urlparse(webhook_url).hostname or "").lower().rstrip(".")
    if any(_is_domain(hostname, domain) for domain in ("discord.com", "discordapp.com")):
        return "discord"
    if any(_is_domain(hostname, domain) for domain in
           ("open.larksuite.com", "open.larkoffice.com", "open.feishu.cn")):
        return "lark"
    raise ValueError("不支持的 webhook 类型")


def create_lark_message(title, content, color="green"):
    color_map = {
        "green": "green",
        "red": "red",
        "blue": "blue",
        "yellow": "yellow",
        "grey": "grey"
    }
    return {
        "msg_type": "interactive",
        "card": {
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": f"**{title}**\n\n{content}",
                        "tag": "lark_md"
                    }
                }
            ],
            "header": {
                "title": {
                    "content": title,
                    "tag": "plain_text"
                },
                "template": color_map.get(color, "green")
            }
        }
    }


def _payload_size(payload):
    return len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _largest_lark_chunk(title, content, color, limit):
    low, high = 1, len(content)
    while low < high:
        middle = (low + high + 1) // 2
        if _payload_size(create_lark_message(title, content[:middle], color)) <= limit:
            low = middle
        else:
            high = middle - 1
    if _payload_size(create_lark_message(title, content[:low], color)) > limit:
        raise ValueError("Lark 消息标题过长")
    return low


def create_lark_messages(title, content, color="green", limit=LARK_REQUEST_BODY_LIMIT):
    if _payload_size(create_lark_message(title, content, color)) <= limit:
        return [create_lark_message(title, content, color)]

    payloads = []
    remaining = content
    while remaining:
        part_title = title if not payloads else f"{title}（续）"
        split_at = _largest_lark_chunk(part_title, remaining, color, limit)
        newline = remaining.rfind("\n", 0, split_at)
        if newline > split_at // 2:
            split_at = newline + 1
        chunk = remaining[:split_at]
        payloads.append(create_lark_message(part_title, chunk, color))
        remaining = remaining[split_at:]
    return payloads


def _split_discord_content(content, limit=DISCORD_DESCRIPTION_LIMIT):
    chunks = []
    remaining = content
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        split_at = remaining.rfind("\n", 0, limit + 1)
        if split_at <= 0:
            split_at = limit
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")
    return chunks or [""]


def create_discord_messages(title, content, color=65280):
    chunks = _split_discord_content(content)
    return [{
        "content": f"**{title}**" if index == 0 else "",
        "embeds": [{
            "title": title if index == 0 else f"{title}（续 {index + 1}/{len(chunks)}）",
            "description": chunk,
            "color": color,
            "footer": {"text": "由 GitHub Actions 自动监控"}
        }]
    } for index, chunk in enumerate(chunks)]


def create_discord_message(title, content, color=65280):
    return create_discord_messages(title, content, color)[0]


def send_webhook(webhook_url, webhook_type, payloads, timeout=10):
    if webhook_type not in ("discord", "lark"):
        raise ValueError("不支持的 webhook 类型")
    if isinstance(payloads, dict):
        payloads = [payloads]

    for payload in payloads:
        try:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            response = requests.post(
                webhook_url,
                data=body,
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"webhook 请求失败 ({type(exc).__name__})") from None

        if webhook_type == "discord":
            if response.status_code != 204:
                raise RuntimeError(f"Discord webhook 返回 HTTP {response.status_code}")
        else:
            if response.status_code != 200:
                raise RuntimeError(f"Lark webhook 返回 HTTP {response.status_code}")
            try:
                body = response.json()
            except ValueError as exc:
                raise RuntimeError("Lark webhook 返回了无效 JSON") from exc
            code = body.get("code", body.get("StatusCode"))
            if code != 0:
                raise RuntimeError(f"Lark webhook 业务失败，code={code}")
