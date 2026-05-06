def detect_webhook_type(webhook_url):
    if "discord" in webhook_url.lower():
        return "discord"
    elif "larksuite.com" in webhook_url.lower() or "feishu" in webhook_url.lower():
        return "lark"
    else:
        return "unknown"


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


def create_discord_message(title, content, color=65280):
    return {
        "content": f"⚽ **{title}**",
        "embeds": [{
            "title": title,
            "description": content,
            "color": color,
            "footer": {"text": "由 GitHub Actions 自动监控"}
        }]
    }
