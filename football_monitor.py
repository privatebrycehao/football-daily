import os
from datetime import datetime, timezone

from lib.ai import analyze_matches_with_ai, build_match_ai_info
from lib.display import build_match_detail_text, format_standings
from lib.espn import get_football_matches_from_espn, get_match_summary
from lib.webhook import (
    create_discord_messages,
    create_lark_messages,
    detect_webhook_type,
    send_webhook,
)


def generate_football_summary(matches, standings_by_league=None):
    if not matches:
        return "今日没有足球比赛结果"

    if standings_by_league is None:
        standings_by_league = {}

    leagues_matches = {}
    for match in matches:
        league = match['league']
        if league not in leagues_matches:
            leagues_matches[league] = []
        leagues_matches[league].append(match)

    summary_lines = []
    total_matches = len(matches)

    summary_lines.append(f"📊 **今日足球比赛总结** ({total_matches} 场比赛)")
    summary_lines.append("")

    match_details_for_ai = []

    for league, league_matches in leagues_matches.items():
        if league in standings_by_league:
            summary_lines.append(format_standings(standings_by_league[league], league))
            summary_lines.append("")

        summary_lines.append(f"🏆 **{league}** ({len(league_matches)} 场)")

        for match in league_matches:
            event_id = match['event'].get('id')
            league_id = match.get('league_id', '')

            summary = None
            if event_id and league_id:
                summary = get_match_summary(event_id, league_id)

            detail_text = build_match_detail_text(match)
            summary_lines.append(f"   {detail_text}")
            summary_lines.append("")

            match_detail_info = build_match_ai_info(match, summary, standings_by_league)
            if match_detail_info:
                match_details_for_ai.append(match_detail_info)

        summary_lines.append("")

    print("🤖 开始AI分析...")
    ai_analysis = analyze_matches_with_ai(matches, standings_by_league, match_details_for_ai)
    if ai_analysis and "遇到技术问题" not in ai_analysis:
        summary_lines.append("🤖 **AI分析**:")
        summary_lines.append("")
        summary_lines.append(ai_analysis)
        summary_lines.append("")
    elif ai_analysis:
        print(f"ℹ️ {ai_analysis}")

    return "\n".join(summary_lines)


def send_football_summary(matches, standings_by_league=None):
    webhook_url = os.getenv('DISCORD_WEBHOOK')
    if not webhook_url:
        raise RuntimeError("未设置 DISCORD_WEBHOOK 环境变量")

    webhook_type = detect_webhook_type(webhook_url)
    print(f"🔍 检测到webhook类型: {webhook_type}")

    summary = generate_football_summary(matches, standings_by_league)

    title = "⚽ 欧洲足球比赛日报"
    content = f"{summary}\n\n⏰ 生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"

    if webhook_type == "lark":
        payloads = create_lark_messages(title, content, "blue")
    else:
        payloads = create_discord_messages(title, content, 3447003)

    print(f"📤 正在发送足球比赛摘要（{len(payloads)} 条）...")
    send_webhook(webhook_url, webhook_type, payloads)
    print("✅ 成功发送足球比赛摘要")


def main():
    print("⚽ 欧洲足球比赛监控启动...")
    try:
        matches, standings = get_football_matches_from_espn()
        print(f"📊 总共找到 {len(matches)} 场最近24小时已完成的比赛")
        print(f"📊 获取到 {len(standings)} 个联赛的积分榜")
        send_football_summary(matches, standings)
        print("✅ 足球监控完成")
    except Exception as exc:
        print(f"❌ 足球监控出错: {type(exc).__name__}: {exc}")
        raise


if __name__ == "__main__":
    main()
