import os
import requests
from datetime import datetime, timedelta
import pytz
from openai import OpenAI

# 设置请求头，避免被识别为爬虫
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Referer': 'https://www.espn.com/'
}

def get_pacific_time_date():
    """获取美西时间的当前日期"""
    pacific_tz = pytz.timezone('US/Pacific')
    utc_now = datetime.now(pytz.UTC)
    pacific_now = utc_now.astimezone(pacific_tz)
    
    print(f"🕐 UTC时间: {utc_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"🕐 美西时间: {pacific_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"🕐 时区偏移: {pacific_now.strftime('%z')}")
    
    return pacific_now.date()

def detect_webhook_type(webhook_url):
    """检测webhook类型"""
    if "discord" in webhook_url.lower():
        return "discord"
    elif "larksuite.com" in webhook_url.lower() or "feishu" in webhook_url.lower():
        return "lark"
    else:
        return "unknown"

def create_lark_message(title, content, color="green"):
    """创建飞书消息格式"""
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
    """创建Discord消息格式"""
    return {
        "content": f"⚽ **{title}**",
        "embeds": [{
            "title": title,
            "description": content,
            "color": color,
            "footer": {"text": "由 GitHub Actions 自动监控"}
        }]
    }

def get_football_matches_from_espn():
    """从ESPN获取足球比赛数据"""
    print("⚽ 尝试使用ESPN API获取足球比赛数据...")
    
    # 获取美西时间日期
    pacific_today = get_pacific_time_date()
    
    # 扩大检查范围：考虑到欧洲时区差异，检查今天、昨天、前天
    # 欧洲比赛通常在欧洲时间进行，可能跨越美西时间的多个日期
    check_dates = [
        pacific_today,
        pacific_today - timedelta(days=1),
        pacific_today - timedelta(days=2)
    ]
    
    print(f"📅 将检查以下美西时间日期: {[d.strftime('%Y-%m-%d') for d in check_dates]}")
    print(f"💡 注意：欧洲比赛时间可能跨越多个美西日期")
    
    # 定义要监控的联赛
    leagues = {
        "UEFA Champions League": "uefa.champions",
        "UEFA Europa League": "uefa.europa", 
        "English Premier League": "eng.1",
        "Spanish La Liga": "esp.1",
        "German Bundesliga": "ger.1",
        "Italian Serie A": "ita.1"
    }
    
    all_matches = []
    all_standings = {}
    
    for league_name, league_id in leagues.items():
        print(f"\n🏆 检查联赛: {league_name}")
        try:
            league_matches_found = 0
            standings_collected = False
            
            # 检查多个日期
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
                events = data.get('events', [])
                
                print(f"    📊 API返回 {len(events)} 个事件")
                
                # 详细分析所有比赛状态
                status_counts = {}
                completed_matches = []
                
                for event in events:
                    status = event.get('status', {}).get('type', {}).get('name', '')
                    status_counts[status] = status_counts.get(status, 0) + 1
                    
                    # 检查已完成的比赛（支持多种完成状态）
                    if status in ['STATUS_FINAL', 'STATUS_FULL_TIME']:
                        completed_matches.append({
                            'league': league_name,
                            'league_id': league_id,
                            'event': event,
                            'date': check_date
                        })
                
                print(f"    📈 比赛状态统计: {status_counts}")
                
                # 显示所有比赛
                if events:
                    for i, event in enumerate(events):
                        name = event.get('name', 'Unknown Match')
                        status = event.get('status', {}).get('type', {}).get('name', '')
                        print(f"      {i+1}. {name} - {status}")
                
                if completed_matches:
                    print(f"    ✅ 找到 {len(completed_matches)} 场已完成的比赛")
                    
                    # 获取积分榜（从第一场比赛的summary中提取）
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
                    print(f"    ⚪ 没有找到已完成的比赛")
            
            print(f"  🎯 {league_name} 总计找到: {league_matches_found} 场比赛")
        
        except Exception as e:
            print(f"  ❌ 获取 {league_name} 数据失败: {e}")
            import traceback
            print(f"  📝 详细错误: {traceback.format_exc()}")
            continue
    
    return all_matches, all_standings

def format_match_result(match):
    """格式化单场比赛结果"""
    try:
        event = match['event']
        league = match['league']
        
        # 获取比赛信息
        competitions = event.get('competitions', [{}])
        if not competitions:
            return f"⚽ {league}: 比赛信息不完整"
        
        competition = competitions[0]
        competitors = competition.get('competitors', [])
        
        if len(competitors) < 2:
            return f"⚽ {league}: 队伍信息不完整"
        
        # 通常home是第一个，away是第二个
        home_team = competitors[0]
        away_team = competitors[1]
        
        # 获取队名和比分
        home_name = home_team.get('team', {}).get('displayName', 'Unknown')
        away_name = away_team.get('team', {}).get('displayName', 'Unknown')
        home_score = home_team.get('score', 0)
        away_score = away_team.get('score', 0)
        
        # 格式化结果 - 使用完整队名和比分
        result = f"⚽ **{league}**: {away_name} {away_score} - {home_score} {home_name}"
        
        return result
        
    except Exception as e:
        return f"⚽ {match.get('league', 'Unknown')}: 解析比赛数据失败 - {e}"

def get_match_summary(event_id, league_id):
    """获取单场比赛的详细摘要"""
    try:
        summary_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_id}/summary?event={event_id}"
        response = requests.get(summary_url, timeout=30, headers=headers)
        if response.status_code != 200:
            print(f"    Summary API错误: {response.status_code}")
            return None
        return response.json()
    except Exception as e:
        print(f"    获取摘要失败: {e}")
        return None

def extract_standings_from_summary(summary):
    """从比赛摘要提取积分榜"""
    if not summary:
        return []
    standings_data = summary.get('standings', {})
    if isinstance(standings_data, dict):
        groups = standings_data.get('groups', [])
        if groups:
            return groups[0].get('standings', {}).get('entries', [])
    return []

def extract_key_events_from_summary(summary):
    """提取进球、红黄牌、换人等关键事件"""
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

def format_standings(entries, league_name, top_n=8):
    """格式化积分榜"""
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
    """构建单场比赛的显示文本（仅比分和场地信息）"""
    lines = []
    event = match['event']
    league = match['league']
    
    result = format_match_result(match)
    lines.append(result)
    
    if not summary:
        return "\n".join(lines)
    
    venue = summary.get('gameInfo', {}).get('venue', {}).get('fullName', '')
    attendance = summary.get('gameInfo', {}).get('attendance', 0)
    if venue:
        info_line = f"  📍 {venue}"
        if attendance:
            info_line += f" | 👥 {attendance:,}"
        lines.append(info_line)
    
    return "\n".join(lines)

def analyze_matches_with_ai(matches, standings_by_league=None, match_details=None):
    """使用DeepSeek AI分析足球比赛结果"""
    api_key = os.getenv('DEEPSEEK_KEY')
    if not api_key:
        print("⚠️ 未设置DEEPSEEK_KEY，使用简单分析")
        return analyze_matches_simple(matches)
    
    if not matches:
        return "没有比赛数据可供分析"
    
    try:
        print("📊 准备AI分析数据...")
        match_data = []
        
        # 积分榜数据
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
        
        # 比赛详情
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
    """基于规则的简单比赛分析"""
    if not matches:
        return "没有比赛数据可供分析"
    
    try:
        analysis_points = []
        total_matches = len(matches)
        
        # 统计各联赛比赛数量
        league_counts = {}
        high_scoring_games = []
        big_wins = []
        close_games = []
        
        for match in matches:
            league = match['league']
            league_counts[league] = league_counts.get(league, 0) + 1
            
            # 解析比分
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
                    
                    # 高比分比赛 (总进球>=5)
                    if total_goals >= 5:
                        high_scoring_games.append(f"{away_name} {away_score}-{home_score} {home_name}")
                    
                    # 大胜比赛 (净胜球>=3)
                    if score_diff >= 3:
                        big_wins.append(f"{away_name} {away_score}-{home_score} {home_name}")
                    
                    # 激烈比赛 (1球小胜)
                    if score_diff == 1:
                        close_games.append(f"{away_name} {away_score}-{home_score} {home_name}")
        
        # 生成分析
        analysis_points.append(f"📊 今日共有 {total_matches} 场精彩比赛结束")
        
        # 联赛分布
        active_leagues = [league for league, count in league_counts.items() if count > 0]
        if len(active_leagues) > 1:
            analysis_points.append(f"🏆 涉及 {len(active_leagues)} 个联赛，足球日程丰富")
        
        # 高比分比赛
        if high_scoring_games:
            analysis_points.append(f"⚽ 进球大战: {len(high_scoring_games)} 场比赛总进球数≥5个")
            if len(high_scoring_games) <= 2:
                for game in high_scoring_games:
                    analysis_points.append(f"   • {game}")
        
        # 大胜比赛
        if big_wins:
            analysis_points.append(f"🎯 碾压式胜利: {len(big_wins)} 场比赛净胜球≥3个")
            if len(big_wins) <= 2:
                for game in big_wins[:2]:
                    analysis_points.append(f"   • {game}")
        
        # 激烈比赛
        if close_games:
            analysis_points.append(f"🔥 激烈对决: {len(close_games)} 场比赛仅1球分胜负")
        
        # 总结
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

def generate_football_summary(matches, standings_by_league=None):
    """生成足球比赛摘要"""
    if not matches:
        return "今日没有足球比赛结果"
    
    if standings_by_league is None:
        standings_by_league = {}
    
    # 按联赛分组
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
    
    # 按联赛显示
    match_details_for_ai = []
    
    for league, league_matches in leagues_matches.items():
        # 积分榜
        if league in standings_by_league:
            summary_lines.append(format_standings(standings_by_league[league], league))
            summary_lines.append("")
        
        summary_lines.append(f"🏆 **{league}** ({len(league_matches)} 场)")
        
        for match in league_matches:
            event_id = match['event'].get('id')
            league_id = match.get('league_id', '')
            
            # 获取比赛详细摘要
            summary = None
            if event_id and league_id:
                summary = get_match_summary(event_id, league_id)
            
            detail_text = build_match_detail_text(match, summary)
            summary_lines.append(f"   {detail_text}")
            summary_lines.append("")
            
            # 收集AI分析数据
            match_detail_info = _build_match_ai_info(match, summary, standings_by_league)
            if match_detail_info:
                match_details_for_ai.append(match_detail_info)
        
        summary_lines.append("")
    
    # 添加AI分析
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

def _build_match_ai_info(match, summary, standings_by_league=None):
    """为AI分析构建单场比赛的详细数据"""
    lines = []
    event = match['event']
    league = match['league']
    result = format_match_result(match)
    lines.append(f"**{result}**")
    
    if not summary:
        return "\n".join(lines)
    
    # 场地和观众
    game_info = summary.get('gameInfo', {})
    venue = game_info.get('venue', {}).get('fullName', '')
    attendance = game_info.get('attendance', 0)
    if venue:
        venue_line = f"  📍 场地: {venue}"
        if attendance:
            venue_line += f" | 👥 观众: {attendance:,}"
        lines.append(venue_line)
    
    # 球队统计对比
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
    
    # 完整事件时间线
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
    
    # 球队排名参考（从积分榜中查找）
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
    """在积分榜中查找球队排名"""
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

def send_football_summary(matches, standings_by_league=None):
    """发送足球比赛摘要到webhook"""
    webhook_url = os.getenv('DISCORD_WEBHOOK')
    if not webhook_url:
        print("警告: 未设置 DISCORD_WEBHOOK 环境变量")
        return
    
    webhook_type = detect_webhook_type(webhook_url)
    print(f"🔍 检测到webhook类型: {webhook_type}")
    
    summary = generate_football_summary(matches, standings_by_league)
    
    # 创建消息
    title = "⚽ 欧洲足球比赛日报"
    content = f"{summary}\n\n⏰ 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC"
    
    if webhook_type == "lark":
        data = create_lark_message(title, content, "blue")
    else:
        data = create_discord_message(title, content, 3447003)
    
    try:
        print(f"📤 正在发送足球比赛摘要...")
        response = requests.post(webhook_url, json=data, timeout=10)
        
        expected_status = 200 if webhook_type == "lark" else 204
        
        if response.status_code == expected_status:
            print("✅ 成功发送足球比赛摘要")
        else:
            print(f"❌ 发送失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
    except Exception as e:
        print(f"❌ 发送webhook时出错: {e}")

def main():
    """主函数"""
    print("⚽ 欧洲足球比赛监控启动...")
    
    try:
        # 获取足球比赛数据
        matches, standings = get_football_matches_from_espn()
        
        print(f"📊 总共找到 {len(matches)} 场已完成的比赛")
        print(f"📊 获取到 {len(standings)} 个联赛的积分榜")
        
        send_football_summary(matches, standings)
        
        print("✅ 足球监控完成")
        
    except Exception as e:
        print(f"❌ 足球监控出错: {e}")
        
        # 发送错误通知
        webhook_url = os.getenv('DISCORD_WEBHOOK')
        if webhook_url:
            webhook_type = detect_webhook_type(webhook_url)
            
            error_content = f"足球比赛监控程序遇到错误\n\n错误详情: {str(e)}\n\n⏰ 错误时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            
            if webhook_type == "lark":
                data = create_lark_message("⚠️ 足球监控错误", error_content, "red")
            else:
                data = create_discord_message("足球监控错误", error_content, 15158332)
            
            try:
                requests.post(webhook_url, json=data, timeout=10)
                print("✅ 已发送错误通知")
            except:
                print("❌ 发送错误通知失败")

if __name__ == "__main__":
    main()
