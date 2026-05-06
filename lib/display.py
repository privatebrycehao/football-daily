def format_match_result(match):
    try:
        event = match['event']
        competitions = event.get('competitions', [{}])
        if not competitions:
            return "比赛信息不完整"
        competition = competitions[0]
        competitors = competition.get('competitors', [])
        if len(competitors) < 2:
            return "队伍信息不完整"
        home_team = competitors[0]
        away_team = competitors[1]
        home_name = home_team.get('team', {}).get('displayName', 'Unknown')
        away_name = away_team.get('team', {}).get('displayName', 'Unknown')
        home_score = home_team.get('score', 0)
        away_score = away_team.get('score', 0)
        return f"**{home_name}** {home_score} - {away_score} {away_name}"
    except Exception as e:
        return f"解析比赛数据失败 - {e}"


def format_standings(entries, league_name, top_n=8):
    if not entries:
        return ""
    lines = [f"\n📊 **{league_name} 积分榜**"]
    lines.append("```")
    lines.append(f"{'#':<2} {'球队':<22} {'场':<3} {'胜':<3} {'平':<3} {'负':<3} {'GD':<5} {'积分':<4}")
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
        lines.append(f"{rank:<2} {team_name:<22} {gp:<3} {wins:<3} {draws:<3} {losses:<3} {gd:<5} {points:<4}")
    lines.append("```")
    return "\n".join(lines)


def build_match_detail_text(match, summary):
    return format_match_result(match)
