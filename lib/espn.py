import traceback
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Referer': 'https://www.espn.com/'
}

LEAGUES = {
    "UEFA Champions League": "uefa.champions",
    "UEFA Europa League": "uefa.europa",
    "English Premier League": "eng.1",
    "Spanish La Liga": "esp.1",
    "German Bundesliga": "ger.1",
    "Italian Serie A": "ita.1"
}


def get_pacific_time_date():
    utc_now = datetime.now(timezone.utc)
    pacific_now = utc_now.astimezone(ZoneInfo('America/Los_Angeles'))
    print(f"🕐 UTC时间: {utc_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"🕐 美西时间: {pacific_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"🕐 时区偏移: {pacific_now.strftime('%z')}")
    return pacific_now.date()


def get_football_matches_from_espn():
    print("⚽ 尝试使用ESPN API获取足球比赛数据...")

    pacific_today = get_pacific_time_date()

    check_dates = [
        pacific_today,
        pacific_today - timedelta(days=1),
        pacific_today - timedelta(days=2)
    ]

    print(f"📅 将检查以下美西时间日期: {[d.strftime('%Y-%m-%d') for d in check_dates]}")
    print("💡 注意：欧洲比赛时间可能跨越多个美西日期")

    all_matches = []
    all_standings = {}
    successful_requests = 0

    for league_name, league_id in LEAGUES.items():
        print(f"\n🏆 检查联赛: {league_name}")
        try:
            league_matches_found = 0
            standings_collected = False

            for check_date in check_dates:
                date_str = check_date.strftime('%Y%m%d')
                espn_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_id}/scoreboard?dates={date_str}"

                print(f"  📅 检查日期: {date_str} ({check_date.strftime('%Y-%m-%d')})")
                print(f"  🔗 API URL: {espn_url}")

                response = requests.get(espn_url, timeout=30, headers=headers)
                if response.status_code != 200:
                    print(f"    ❌ ESPN API响应错误: {response.status_code}")
                    continue

                data = response.json()
                successful_requests += 1
                events = data.get('events', [])

                print(f"    📊 API返回 {len(events)} 个事件")

                status_counts = {}
                completed_matches = []

                for event in events:
                    status = event.get('status', {}).get('type', {}).get('name', '')
                    status_counts[status] = status_counts.get(status, 0) + 1

                    if status in ['STATUS_FINAL', 'STATUS_FULL_TIME']:
                        completed_matches.append({
                            'league': league_name,
                            'league_id': league_id,
                            'event': event,
                            'date': check_date
                        })

                print(f"    📈 比赛状态统计: {status_counts}")

                if events:
                    for i, event in enumerate(events):
                        name = event.get('name', 'Unknown Match')
                        status = event.get('status', {}).get('type', {}).get('name', '')
                        print(f"      {i+1}. {name} - {status}")

                if completed_matches:
                    print(f"    ✅ 找到 {len(completed_matches)} 场已完成的比赛")

                    if not standings_collected and league_name not in all_standings:
                        first_match = completed_matches[0]
                        event_id = first_match['event'].get('id')
                        if event_id:
                            print(f"    📊 获取 {league_name} 积分榜...")
                            summary = get_match_summary(event_id, league_id)
                            standings_entries = extract_standings_from_summary(summary)
                            if standings_entries:
                                all_standings[league_name] = standings_entries
                                standings_collected = True
                                print(f"    ✅ 获取到 {len(standings_entries)} 支球队的积分数据")

                    all_matches.extend(completed_matches)
                    league_matches_found += len(completed_matches)
                else:
                    print("    ⚪ 没有找到已完成的比赛")

            print(f"  🎯 {league_name} 总计找到: {league_matches_found} 场比赛")

        except Exception as e:  # noqa: BLE001
            print(f"  ❌ 获取 {league_name} 数据失败: {e}")
            print(f"  📝 详细错误: {traceback.format_exc()}")
            continue

    if successful_requests == 0:
        raise RuntimeError("ESPN 足球数据请求全部失败")

    now_utc = datetime.now(timezone.utc)
    window_start = now_utc - timedelta(hours=24)
    recent_matches = {}
    for match in all_matches:
        event = match['event']
        event_id = event.get('id')
        event_date = event.get('date')
        if not event_id or not event_date:
            continue
        try:
            event_time = datetime.fromisoformat(event_date.replace('Z', '+00:00')).astimezone(timezone.utc)
        except (TypeError, ValueError):
            print(f"  ⚠️ 跳过时间无效的事件: {event_id}")
            continue
        if window_start <= event_time <= now_utc:
            recent_matches[event_id] = match

    print(f"🕐 日报窗口: {window_start.isoformat()} 至 {now_utc.isoformat()}，去重后 {len(recent_matches)} 场")
    return list(recent_matches.values()), all_standings


@lru_cache(maxsize=128)
def get_match_summary(event_id, league_id):
    try:
        summary_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_id}/summary?event={event_id}"
        response = requests.get(summary_url, timeout=30, headers=headers)
        if response.status_code != 200:
            print(f"    Summary API错误: {response.status_code}")
            return None
        return response.json()
    except Exception as e:  # noqa: BLE001
        print(f"    获取摘要失败: {e}")
        return None


def extract_standings_from_summary(summary):
    if not summary:
        return []
    standings_data = summary.get('standings', {})
    if isinstance(standings_data, dict):
        groups = standings_data.get('groups', [])
        if groups:
            return groups[0].get('standings', {}).get('entries', [])
    return []


def extract_key_events_from_summary(summary):
    if not summary:
        return []
    events_list = []
    for ke in summary.get('keyEvents', []):
        event_type = ke.get('type', {}).get('text', '')
        if not event_type:
            continue
        clock = ke.get('clock', {}).get('displayValue', '')
        short_text = ke.get('shortText', '')
        if not short_text:
            continue
        emoji_map = {'Goal': '⚽', 'Yellow Card': '🟨', 'Yellow': '🟨', 'Red Card': '🟥', 'Red': '🟥', 'Substitution': '🔃', 'Penalty': '🥅'}
        emoji = emoji_map.get(event_type, '')
        if not emoji:
            continue
        events_list.append(f"  {emoji} {clock}' {short_text}")
    return events_list
