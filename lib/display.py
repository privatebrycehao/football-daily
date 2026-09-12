def get_home_away_competitors(event):
    competitions = event.get('competitions', [])
    if not competitions:
        return None, None
    competitors = competitions[0].get('competitors', [])
    home = next((team for team in competitors if team.get('homeAway') == 'home'), None)
    away = next((team for team in competitors if team.get('homeAway') == 'away'), None)
    return home, away


def format_match_result(match):
    try:
        event = match['event']
        competitions = event.get('competitions', [{}])
        if not competitions:
            return "比赛信息不完整"
        home_team, away_team = get_home_away_competitors(event)
        if not home_team or not away_team:
            return "队伍信息不完整"
        home_name = home_team.get('team', {}).get('displayName', 'Unknown')
        away_name = away_team.get('team', {}).get('displayName', 'Unknown')
        home_score = home_team.get('score', 0)
        away_score = away_team.get('score', 0)
        return f"主队 **{home_name}** {home_score} - {away_score} {away_name} 客队"
    except Exception as e:  # noqa: BLE001
        return f"解析比赛数据失败 - {e}"


def format_standings(entries, league_name, top_n=8):
    if not entries:
        return ""
    lines = [f"\n📊 **{league_name} 积分榜**"]
    for entry in entries[:top_n]:
        team_name = entry.get('team', '')
        stats = {s['name']: s.get('displayValue', '') for s in entry.get('stats', [])}
        rank = stats.get('rank', '')
        gp = stats.get('gamesPlayed', '')
        wins = stats.get('wins', '')
        draws = stats.get('ties', '')
        losses = stats.get('losses', '')
        gd = stats.get('pointDifferential', '')
        points = stats.get('points', '')
        lines.append(
            f"- **{rank}. {team_name}**｜{points} 分｜{gp} 场｜{wins}胜 {draws}平 {losses}负｜净胜球 {gd}"
        )
    return "\n".join(lines)


def build_match_detail_text(match):
    return format_match_result(match)
