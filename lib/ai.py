import os
from openai import OpenAI
from .display import format_match_result


def analyze_matches_with_ai(matches, standings_by_league=None, match_details=None):
    api_key = os.getenv('DEEPSEEK_KEY')
    if not api_key:
        print("⚠️ 未设置DEEPSEEK_KEY，使用简单分析")
        return analyze_matches_simple(matches)

    if not matches:
        return "没有比赛数据可供分析"

    try:
        print("📊 准备AI分析数据...")
        match_data = []

        if standings_by_league:
            match_data.append("📊 **各联赛积分榜**:")
            for league_name, entries in standings_by_league.items():
                if entries:
                    top_teams = []
                    for entry in entries[:6]:
                        rank = entry.get('stats', [{}])[0].get('displayValue', '?')
                        team = entry.get('team', '?')
                        pts = entry.get('stats', [{}])[0].get('displayValue', '?')
                        if len(entry.get('stats', [])) > 3:
                            pts = next((s.get('displayValue', '?') for s in entry['stats'] if s.get('name') == 'points'), '?')
                        top_teams.append(f"{rank}. {team} ({pts}分)")
                    match_data.append(f"\n{league_name}: {' | '.join(top_teams)}")
            match_data.append("")

        if match_details:
            match_data.append("⚽ **今日比赛详情**:")
            match_data.extend(match_details)
        else:
            match_data.append("⚽ **今日比赛**:")
            for match in matches:
                basic_result = format_match_result(match)
                match_data.append(basic_result)

                event = match['event']
                competitions = event.get('competitions', [{}])
                if competitions:
                    competitors = competitions[0].get('competitors', [])
                    if len(competitors) >= 2:
                        home_score = int(competitors[0].get('score', 0) or 0)
                        away_score = int(competitors[1].get('score', 0) or 0)
                        total = home_score + away_score
                        diff = abs(home_score - away_score)
                        if total >= 5:
                            match_data.append(f"  🔥 进球大战: {total}球")
                        if diff >= 3:
                            match_data.append(f"  💪 大比分胜利: 净胜{diff}球")

        matches_text = "\n".join(match_data)

        prompt = f"""请分析以下足球比赛数据：

积分榜和比赛详细信息如下，所有比分格式为"客队 比分 - 比分 主队"：

{matches_text}

请提供以下内容：

1. **整体赛况总结**（1-2段）：
   - 今日比赛的整体特点和亮点
   - 意外结果、冷门和惊喜表现
   - 各联赛的竞争态势概述

2. **重点比赛复盘**（按联赛，重点分析2-3场关键比赛）：
   - 根据比赛进程（进球时间线、换人时机等）分析比赛转折点
   - 根据球队数据（控球率、射门、传球等）分析场面优劣
   - 根据红黄牌情况分析比赛激烈程度和纪律问题
   - 结合赛前排名分析结果是否符合预期

3. **联赛形势分析**：
   - 结合积分榜，分析比赛结果对争冠、欧战资格、保级形势的影响
   - 指出积分榜的关键变化

4. **球队和球员表现点评**（亮点和低谷）：
   - 表现亮眼的球队和关键球员（进球、助攻等）
   - 状态低迷的球队，及其问题所在
   - 红黄牌停赛对后续比赛的影响

请用专业且生动的中文撰写，基于实际数据深入分析，避免泛泛而谈。每个部分的篇幅要均衡。"""

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=3000,
        )

        ai_analysis = response.choices[0].message.content.strip()
        print("✅ AI分析完成")
        return ai_analysis

    except Exception as e:
        print(f"❌ AI分析失败: {e}")
        print("🔄 回退到简单分析")
        return analyze_matches_simple(matches)


def analyze_matches_simple(matches):
    if not matches:
        return "没有比赛数据可供分析"

    try:
        analysis_points = []
        total_matches = len(matches)

        league_counts = {}
        high_scoring_games = []
        big_wins = []
        close_games = []

        for match in matches:
            league = match['league']
            league_counts[league] = league_counts.get(league, 0) + 1

            event = match['event']
            competitions = event.get('competitions', [{}])
            if competitions:
                competitors = competitions[0].get('competitors', [])
                if len(competitors) >= 2:
                    home_score = int(competitors[0].get('score', 0))
                    away_score = int(competitors[1].get('score', 0))
                    total_goals = home_score + away_score
                    score_diff = abs(home_score - away_score)

                    home_name = competitors[0].get('team', {}).get('displayName', 'Unknown')
                    away_name = competitors[1].get('team', {}).get('displayName', 'Unknown')

                    if total_goals >= 5:
                        high_scoring_games.append(f"{away_name} {away_score}-{home_score} {home_name}")

                    if score_diff >= 3:
                        big_wins.append(f"{away_name} {away_score}-{home_score} {home_name}")

                    if score_diff == 1:
                        close_games.append(f"{away_name} {away_score}-{home_score} {home_name}")

        analysis_points.append(f"📊 今日共有 {total_matches} 场精彩比赛结束")

        active_leagues = [league for league, count in league_counts.items() if count > 0]
        if len(active_leagues) > 1:
            analysis_points.append(f"🏆 涉及 {len(active_leagues)} 个联赛，足球日程丰富")

        if high_scoring_games:
            analysis_points.append(f"⚽ 进球大战: {len(high_scoring_games)} 场比赛总进球数≥5个")
            if len(high_scoring_games) <= 2:
                for game in high_scoring_games:
                    analysis_points.append(f"   • {game}")

        if big_wins:
            analysis_points.append(f"🎯 碾压式胜利: {len(big_wins)} 场比赛净胜球≥3个")
            if len(big_wins) <= 2:
                for game in big_wins[:2]:
                    analysis_points.append(f"   • {game}")

        if close_games:
            analysis_points.append(f"🔥 激烈对决: {len(close_games)} 场比赛仅1球分胜负")

        if high_scoring_games and big_wins:
            analysis_points.append("⭐ 今日比赛既有进球大战，又有实力悬殊的较量，精彩纷呈！")
        elif high_scoring_games:
            analysis_points.append("⭐ 今日比赛进球如雨，攻势足球让球迷大饱眼福！")
        elif len(close_games) > len(big_wins):
            analysis_points.append("⭐ 今日比赛竞争激烈，多场比赛胜负难分！")
        else:
            analysis_points.append("⭐ 今日各队发挥稳定，比赛结果符合预期。")

        return "\n".join(analysis_points)

    except Exception as e:
        print(f"❌ 比赛分析失败: {e}")
        return "比赛分析遇到技术问题，请查看详细比赛结果。"


def build_match_ai_info(match, summary, standings_by_league=None):
    lines = []
    event = match['event']
    league = match['league']
    result = format_match_result(match)
    lines.append(f"**{result}**")

    if not summary:
        return "\n".join(lines)

    game_info = summary.get('gameInfo', {})
    venue = game_info.get('venue', {}).get('fullName', '')
    attendance = game_info.get('attendance', 0)
    if venue:
        venue_line = f"  📍 场地: {venue}"
        if attendance:
            venue_line += f" | 👥 观众: {attendance:,}"
        lines.append(venue_line)

    boxscore = summary.get('boxscore', {})
    teams_stats = boxscore.get('teams', [])
    if len(teams_stats) >= 2:
        lines.append("  📊 **球队数据对比**:")
        stat_keys = ['possessionPct', 'totalShots', 'shotsOnTarget', 'wonCorners', 'foulsCommitted', 'yellowCards', 'redCards', 'offSides', 'saves', 'accuratePasses', 'passPct', 'penaltyKickGoals']
        stat_labels = {'possessionPct': '控球率%', 'totalShots': '射门', 'shotsOnTarget': '射正', 'wonCorners': '角球', 'foulsCommitted': '犯规', 'yellowCards': '黄牌', 'redCards': '红牌', 'offSides': '越位', 'saves': '扑救', 'accuratePasses': '传球成功', 'passPct': '传球成功率%', 'penaltyKickGoals': '点球'}
        for key in stat_keys:
            vals = []
            for t in teams_stats:
                stats = {s.get('name', ''): s.get('displayValue', '-') for s in t.get('statistics', [])}
                team = t.get('team', {}).get('abbreviation', t.get('team', {}).get('displayName', '?'))
                v = stats.get(key, '-')
                vals.append(f"{team}: {v}")
            if any(v.split(': ')[1] not in ('-', '0', '0.0', '0%') for v in vals):
                lines.append(f"    {stat_labels.get(key, key)} - {' | '.join(vals)}")

    key_events = summary.get('keyEvents', [])
    if key_events:
        lines.append("  ⏱️ **比赛进程**:")
        for ke in key_events:
            event_type = ke.get('type', {}).get('text', '')
            if not event_type:
                continue
            clock = ke.get('clock', {}).get('displayValue', '')
            short_text = ke.get('shortText', '')
            if not short_text:
                continue
            emoji_map = {'Goal': '⚽', 'Yellow Card': '🟨', 'Yellow': '🟨', 'Red Card': '🟥', 'Red': '🟥', 'Substitution': '🔃', 'Penalty': '🥅'}
            emoji = emoji_map.get(event_type, '')
            if emoji:
                lines.append(f"    {emoji} {clock}' - {short_text}")

    if standings_by_league and league in standings_by_league:
        comps = event.get('competitions', [{}])
        if comps:
            competitors = comps[0].get('competitors', [])
            entries = standings_by_league[league]
            team_ranks = []
            for comp in competitors:
                team_name = comp.get('team', {}).get('displayName', '')
                rank = _find_team_rank(entries, team_name)
                if rank:
                    team_ranks.append(f"{team_name} (赛前排名第{rank})")
            if team_ranks:
                lines.append(f"  赛前排名: {' vs '.join(team_ranks)}")

    return "\n".join(lines)


def _find_team_rank(standings_entries, team_name):
    if not team_name:
        return None
    team_lower = team_name.lower()
    for entry in standings_entries:
        entry_team = entry.get('team', '').lower()
        if team_lower == entry_team or team_lower in entry_team or entry_team in team_lower:
            for s in entry.get('stats', []):
                if s.get('name') == 'rank':
                    return s.get('displayValue')
    return None
