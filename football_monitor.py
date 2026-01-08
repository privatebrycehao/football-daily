import os
import requests
import time
from datetime import datetime, date, timedelta
import pytz
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ Google GenAI not available, will use simple analysis")

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
    try:
        # 美西时区（自动处理夏令时）
        pacific_tz = pytz.timezone('US/Pacific')
        utc_now = datetime.now(pytz.UTC)
        pacific_now = utc_now.astimezone(pacific_tz)
        
        print(f"🕐 UTC时间: {utc_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"🕐 美西时间: {pacific_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"🕐 时区偏移: {pacific_now.strftime('%z')}")
        
        return pacific_now.date()
    except ImportError:
        # 如果pytz不可用，使用简单的时区偏移
        print("⚠️ pytz不可用，使用简单时区计算")
        utc_now = datetime.utcnow()
        # 假设PST (UTC-8)，但实际应该检查夏令时
        pacific_now = utc_now - timedelta(hours=8)
        
        print(f"🕐 UTC时间: {utc_now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"🕐 美西时间(估算): {pacific_now.strftime('%Y-%m-%d %H:%M:%S')} PST")
        print("⚠️ 注意：未考虑夏令时，可能有1小时误差")
        
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
    
    for league_name, league_id in leagues.items():
        print(f"\n🏆 检查联赛: {league_name}")
        try:
            league_matches_found = 0
            
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
    
    return all_matches

def get_league_standings(league_id):
    """获取联赛积分榜信息"""
    try:
        standings_url = f"https://site.api.espn.com/apis/v2/sports/soccer/{league_id}/standings"
        
        response = requests.get(standings_url, headers=headers, timeout=15)
        if response.status_code == 200:
            standings_data = response.json()
            
            # 提取积分榜信息
            standings_info = {}
            children = standings_data.get('children', [])
            
            for child in children:
                standings = child.get('standings', {}).get('entries', [])
                for entry in standings:
                    team = entry.get('team', {})
                    team_name = team.get('displayName', '')
                    position = entry.get('position', 0)
                    points = entry.get('stats', [{}])[0].get('value', 0) if entry.get('stats') else 0
                    
                    standings_info[team_name] = {
                        'position': position,
                        'points': points
                    }
            
            return standings_info
    except Exception as e:
        print(f"❌ 获取积分榜失败: {e}")
    
    return {}

def get_match_details(event):
    """获取比赛详细信息，包括进球时间、球员等"""
    try:
        match_id = event.get('id')
        if not match_id:
            return {}
            
        print(f"🔍 获取比赛 {match_id} 的详细信息...")
        
        # 尝试获取比赛详细信息
        detail_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/summary"
        params = {'event': match_id}
        
        response = requests.get(detail_url, headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            detail_data = response.json()
            
            # 提取进球信息
            scoring_plays = []
            
            # 尝试多种方式获取进球信息
            # 方法1: keyEvents
            keyEvents = detail_data.get('keyEvents', [])
            print(f"   📊 找到 {len(keyEvents)} 个关键事件")
            
            for key_event in keyEvents:
                event_type = key_event.get('type', {}).get('text', '')
                if 'Goal' in event_type or 'goal' in event_type.lower():
                    clock = key_event.get('clock', {}).get('displayValue', '')
                    player = key_event.get('participant', {}).get('displayName', 'Unknown')
                    team = key_event.get('team', {}).get('displayName', 'Unknown')
                    scoring_plays.append({
                        'time': clock,
                        'player': player,
                        'team': team
                    })
                    print(f"   ⚽ 进球: {clock}' {player} ({team})")
            
            # 方法2: 如果keyEvents没有进球，尝试从competitions获取
            if not scoring_plays:
                competitions = detail_data.get('header', {}).get('competitions', [])
                for comp in competitions:
                    competitors = comp.get('competitors', [])
                    for competitor in competitors:
                        scoring = competitor.get('scoring', [])
                        for score in scoring:
                            if score.get('type') == 'goal':
                                clock = score.get('clock', '')
                                player = score.get('athlete', {}).get('displayName', 'Unknown')
                                team = competitor.get('team', {}).get('displayName', 'Unknown')
                                scoring_plays.append({
                                    'time': clock,
                                    'player': player,
                                    'team': team
                                })
                                print(f"   ⚽ 进球(方法2): {clock}' {player} ({team})")
            
            print(f"   ✅ 总共找到 {len(scoring_plays)} 个进球")
            
            return {
                'scoring_plays': scoring_plays,
                'detailed_stats': detail_data.get('boxscore', {}),
                'match_commentary': detail_data.get('commentary', [])
            }
        else:
            print(f"   ❌ API响应错误: {response.status_code}")
    except Exception as e:
        print(f"❌ 获取比赛详情失败: {e}")
    
    return {}

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
        
        # 获取比赛详细信息
        match_details = get_match_details(event)
        
        # 格式化结果 - 使用完整队名
        result = f"⚽ **{league}**: {away_name} {away_score} - {home_score} {home_name}"
        
        # 添加进球详情
        scoring_plays = match_details.get('scoring_plays', [])
        if scoring_plays:
            result += "\n   📊 进球详情:"
            for goal in scoring_plays:
                result += f"\n      {goal['time']}' {goal['player']} ({goal['team']})"
        
        return result
        
    except Exception as e:
        return f"⚽ {match.get('league', 'Unknown')}: 解析比赛数据失败 - {e}"

def analyze_matches_with_ai(matches):
    """使用Gemini AI分析足球比赛结果"""
    if not GEMINI_AVAILABLE:
        print("⚠️ Gemini不可用，使用简单分析")
        return analyze_matches_simple(matches)
    
    gemini_api_key = os.getenv('GEMINI_KEY')
    if not gemini_api_key:
        print("⚠️ 未设置GEMINI_KEY，使用简单分析")
        return analyze_matches_simple(matches)
    
    if not matches:
        return "没有比赛数据可供分析"
    
    try:
        # 准备详细的比赛数据给AI分析
        match_data = []
        league_standings_info = {}
        
        # 获取各联赛的积分榜信息
        leagues_in_matches = set(match['league'] for match in matches)
        league_id_map = {
            "English Premier League": "eng.1",
            "Spanish La Liga": "esp.1", 
            "German Bundesliga": "ger.1",
            "Italian Serie A": "ita.1",
            "UEFA Champions League": "uefa.champions",
            "UEFA Europa League": "uefa.europa"
        }
        
        for league_name in leagues_in_matches:
            if league_name in league_id_map:
                print(f"📊 获取 {league_name} 积分榜...")
                standings = get_league_standings(league_id_map[league_name])
                if standings:
                    league_standings_info[league_name] = standings
                    print(f"   ✅ 获取到 {len(standings)} 支球队的积分榜信息")
        
        for match in matches:
            # 基本比赛信息
            basic_result = format_match_result(match)
            match_data.append(basic_result)
            
            # 添加更多详细信息
            event = match['event']
            match_details = get_match_details(event)
            league = match['league']
            
            # 获取球队信息
            competitions = event.get('competitions', [{}])
            if competitions:
                competition = competitions[0]
                competitors = competition.get('competitors', [])
                
                if len(competitors) >= 2:
                    home_team = competitors[0]
                    away_team = competitors[1]
                    home_name = home_team.get('team', {}).get('displayName', '')
                    away_name = away_team.get('team', {}).get('displayName', '')
                    
                    # 添加球队在联赛中的排名信息（模拟数据，实际应从积分榜API获取）
                    if league not in league_standings_info:
                        league_standings_info[league] = []
                    
                    # 添加进球详情到AI分析数据
                    scoring_plays = match_details.get('scoring_plays', [])
                    if scoring_plays:
                        match_data.append(f"   🎯 {home_name} vs {away_name} 进球详情:")
                        for goal in scoring_plays:
                            match_data.append(f"      {goal['time']}' {goal['player']} ({goal['team']})")
                    else:
                        match_data.append(f"   ⚠️ {home_name} vs {away_name}: 暂未获取到进球详情")
                    
                    # 添加积分榜位置信息
                    if league in league_standings_info:
                        standings = league_standings_info[league]
                        home_pos = standings.get(home_name, {})
                        away_pos = standings.get(away_name, {})
                        
                        if home_pos or away_pos:
                            match_data.append(f"   📈 积分榜位置:")
                            if home_pos:
                                match_data.append(f"      {home_name}: 第{home_pos.get('position', '?')}位 ({home_pos.get('points', '?')}分)")
                            if away_pos:
                                match_data.append(f"      {away_name}: 第{away_pos.get('position', '?')}位 ({away_pos.get('points', '?')}分)")
                    
                    # 添加球队统计
                    home_stats = home_team.get('statistics', [])
                    if home_stats:
                        match_data.append(f"   📊 {home_name} 关键数据:")
                        for stat in home_stats[:3]:  # 只取前3个重要统计
                            stat_name = stat.get('name', '')
                            stat_value = stat.get('displayValue', '')
                            if stat_name and stat_value:
                                match_data.append(f"      {stat_name}: {stat_value}")
        
        # 添加完整的积分榜信息到AI分析
        if league_standings_info:
            match_data.append("\n🏆 **当前联赛积分榜概况**:")
            for league_name, standings in league_standings_info.items():
                match_data.append(f"\n📊 {league_name} 前10名:")
                # 按积分排序
                sorted_teams = sorted(standings.items(), key=lambda x: x[1].get('position', 999))
                for team_name, info in sorted_teams[:10]:
                    match_data.append(f"   {info.get('position', '?')}. {team_name} ({info.get('points', '?')}分)")
        
        matches_text = "\n".join(match_data)
        
        # 构建AI分析提示
        prompt = f"""请详细分析以下足球比赛结果，重点关注进球详情和积分榜影响：

{matches_text}

**重要提醒**：上述数据中包含了每场比赛的进球时间、进球球员和所属球队信息，请务必在分析中详细提及这些进球详情。

请提供以下内容：

1. **整体赛况总结**：
   - 今日比赛的整体特点和亮点
   - 意外结果和惊喜表现
   - 各联赛的竞争态势

2. **每场比赛详细分析**：
   为每场比赛提供：
   - **进球分析**：详细分析每个进球的时间、进球球员、进球方式和对比赛的影响
   - **关键球员表现**：重点评价进球球员和助攻球员的表现
   - 比赛过程分析（攻防表现、关键时刻、转折点）
   - 球队战术和阵容分析
   - 对两队后续比赛的影响

3. **联赛积分榜深度影响分析**：
   - **争冠形势**：分析各场比赛对争冠球队的影响
   - **欧战资格竞争**：评估欧冠、欧联杯资格争夺的变化
   - **保级大战**：分析保级球队的形势变化
   - **排名预测**：预测重要的排名变动趋势
   - **关键对决预告**：分析接下来的关键比赛

4. **进球球员和球队深度分析**：
   - 分析每位进球球员的状态和价值
   - 评估进球对球员个人和球队的意义
   - 分析进球时间对比赛走势的影响
   - 技术统计和攻防数据对比

5. **联赛格局展望**：
   - 基于今日结果预测联赛走势
   - 分析各队的优势和劣势
   - 预测后续关键比赛

请用专业且生动的中文撰写，确保每场比赛的进球详情都被详细分析，每位进球球员都被提及，积分榜影响分析要深入具体。总字数不限，越详细越好。"""

        # 使用API key调用Gemini
        client = genai.Client(api_key=gemini_api_key)
        
        # 尝试不同的模型名称（优先使用免费的）
        models_to_try = [
            "gemini-3-flash-preview",  # 免费额度
            "models/gemini-3-flash-preview",
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash",
            "gemini-pro",
            "models/gemini-1.5-flash-latest",
            "models/gemini-pro"
        ]
        
        response = None
        for model_name in models_to_try:
            try:
                print(f"🔄 尝试模型: {model_name}")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                print(f"✅ 模型 {model_name} 成功")
                break
            except Exception as model_error:
                print(f"❌ 模型 {model_name} 失败: {model_error}")
                continue
        
        if not response:
            raise Exception("所有模型都不可用")
        
        ai_analysis = response.text.strip()
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

def generate_football_summary(matches):
    """生成足球比赛摘要"""
    if not matches:
        return "今日没有足球比赛结果"
    
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
    
    # 按联赛显示结果
    for league, league_matches in leagues_matches.items():
        summary_lines.append(f"🏆 **{league}** ({len(league_matches)} 场)")
        
        for match in league_matches:
            result = format_match_result(match)
            summary_lines.append(f"   {result}")
        
        summary_lines.append("")  # 联赛间空行
    
    # 添加AI分析
    print("🤖 开始AI分析...")
    ai_analysis = analyze_matches_with_ai(matches)
    if ai_analysis and "遇到技术问题" not in ai_analysis:
        summary_lines.append("🤖 **AI分析**:")
        summary_lines.append("")
        summary_lines.append(ai_analysis)
        summary_lines.append("")
    elif ai_analysis:
        print(f"ℹ️ {ai_analysis}")
    
    return "\n".join(summary_lines)

def send_startup_notification():
    """发送足球监控启动通知"""
    webhook_url = os.getenv('DISCORD_WEBHOOK')
    if not webhook_url:
        print("警告: 未设置 DISCORD_WEBHOOK 环境变量")
        return
    
    webhook_type = detect_webhook_type(webhook_url)
    
    # 创建启动通知消息
    title = "⚽ 足球监控启动"
    content = f"欧洲足球比赛监控程序已启动\n开始检查今日足球比赛结果...\n\n⏰ 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC"
    
    if webhook_type == "lark":
        data = create_lark_message(title, content, "blue")
    else:
        data = create_discord_message(title, content, 3447003)
    
    try:
        print(f"📤 正在发送足球监控启动通知...")
        response = requests.post(webhook_url, json=data, timeout=10)
        
        expected_status = 200 if webhook_type == "lark" else 204
        
        if response.status_code == expected_status:
            print("✅ 成功发送启动通知")
        else:
            print(f"❌ 启动通知发送失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
    except Exception as e:
        print(f"❌ 发送启动通知时出错: {e}")

def send_football_summary(matches):
    """发送足球比赛摘要到webhook"""
    webhook_url = os.getenv('DISCORD_WEBHOOK')
    if not webhook_url:
        print("警告: 未设置 DISCORD_WEBHOOK 环境变量")
        return
    
    webhook_type = detect_webhook_type(webhook_url)
    print(f"🔍 检测到webhook类型: {webhook_type}")
    
    # 生成摘要
    summary = generate_football_summary(matches)
    
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
    
    # 显示运行环境信息
    github_event = os.getenv('GITHUB_EVENT_NAME', 'local')
    print(f"🔧 运行环境: {github_event}")
    
    is_manual_run = github_event in ['workflow_dispatch', 'local']
    
    if github_event == 'schedule':
        print("📅 这是自动调度运行 - 跳过启动通知")
    elif github_event == 'workflow_dispatch':
        print("🔧 这是手动触发运行 - 发送启动通知")
    else:
        print("💻 这是本地运行 - 发送启动通知")
    
    # 智能启动通知：只在手动运行时发送
    if is_manual_run:
        send_startup_notification()
    else:
        print("ℹ️ 自动调度运行，跳过启动通知")
    
    try:
        # 获取足球比赛数据
        matches = get_football_matches_from_espn()
        
        print(f"📊 总共找到 {len(matches)} 场已完成的比赛")
        
        # 发送摘要
        send_football_summary(matches)
        
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
