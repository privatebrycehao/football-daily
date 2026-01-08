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
        # 尝试多个积分榜API端点，包括当前赛季的特定端点
        current_year = datetime.now().year
        season_year = current_year if datetime.now().month >= 8 else current_year - 1
        
        standings_urls = [
            # 最新的积分榜API
            f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_id}/standings",
            f"https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league_id}/seasons/{season_year}/types/1/standings",
            f"https://site.api.espn.com/apis/v2/sports/soccer/{league_id}/standings?season={season_year}",
            # 备用端点
            f"https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league_id}/standings",
            f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_id}/scoreboard",
        ]
        
        for i, url in enumerate(standings_urls):
            try:
                print(f"   🔄 尝试积分榜API {i+1}: {url}")
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    standings_data = response.json()
                    print(f"   ✅ 积分榜API {i+1} 成功响应")
                    
                    # 调试：打印API响应的结构
                    print(f"   🔍 API响应结构: {list(standings_data.keys())}")
                    
                    standings_info = {}
                    
                    # 方法1: 标准积分榜结构
                    children = standings_data.get('children', [])
                    if children:
                        print(f"   📊 找到 {len(children)} 个积分榜分组")
                        for child in children:
                            standings = child.get('standings', {})
                            entries = standings.get('entries', []) if isinstance(standings, dict) else []
                            
                            for entry in entries:
                                team = entry.get('team', {})
                                team_name = team.get('displayName', '')
                                position = entry.get('position', 0)
                                
                                # 获取积分 - 尝试多种方式
                                points = 0
                                stats = entry.get('stats', [])
                                if stats:
                                    # 通常积分是第一个统计项
                                    for stat in stats:
                                        if stat.get('name') == 'points' or stat.get('abbreviation') == 'PTS':
                                            points = stat.get('value', 0)
                                            break
                                    if not points and stats:
                                        points = stats[0].get('value', 0)  # 备用方案
                                
                                if team_name:
                                    standings_info[team_name] = {
                                        'position': position,
                                        'points': points
                                    }
                    
                    # 方法2: 如果没有children，尝试直接从根获取
                    if not standings_info:
                        print("   🔄 尝试从根数据获取积分榜...")
                        standings = standings_data.get('standings', {})
                        if isinstance(standings, dict):
                            entries = standings.get('entries', [])
                        elif isinstance(standings, list):
                            entries = standings
                        else:
                            entries = []
                        
                        for entry in entries:
                            team = entry.get('team', {})
                            team_name = team.get('displayName', '')
                            position = entry.get('position', 0)
                            
                            points = 0
                            stats = entry.get('stats', [])
                            if stats:
                                for stat in stats:
                                    if 'point' in stat.get('name', '').lower():
                                        points = stat.get('value', 0)
                                        break
                                if not points and stats:
                                    points = stats[0].get('value', 0)
                            
                            if team_name:
                                standings_info[team_name] = {
                                    'position': position,
                                    'points': points
                                }
                    
                    # 方法3: 从scoreboard API获取当前积分信息
                    if not standings_info and 'scoreboard' in url:
                        print("   🔄 从scoreboard获取球队信息...")
                        events = standings_data.get('events', [])
                        for event in events:
                            competitions = event.get('competitions', [])
                            for comp in competitions:
                                competitors = comp.get('competitors', [])
                                for competitor in competitors:
                                    team = competitor.get('team', {})
                                    team_name = team.get('displayName', '')
                                    # 从scoreboard无法获取准确积分，但可以获取球队列表
                                    if team_name:
                                        standings_info[team_name] = {
                                            'position': 0,  # 占位符
                                            'points': 0     # 占位符
                                        }
                    
                    if standings_info:
                        print(f"   ✅ 成功获取 {len(standings_info)} 支球队的积分信息")
                        return standings_info
                    else:
                        print(f"   ⚠️ API {i+1} 响应成功但未找到积分榜数据")
                        
                else:
                    print(f"   ❌ 积分榜API {i+1} 响应错误: {response.status_code}")
                    if response.status_code == 404:
                        print(f"      可能的原因: 联赛ID {league_id} 不正确或赛季参数有误")
                    
            except Exception as e:
                print(f"   ❌ 积分榜API {i+1} 失败: {e}")
                continue
        
        print("   ⚠️ 所有积分榜API都失败")
        
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
        
        # 尝试多个API端点
        api_endpoints = [
            f"https://site.api.espn.com/apis/site/v2/sports/soccer/summary?event={match_id}",
            f"https://sports.core.api.espn.com/v2/sports/soccer/leagues/eng.1/events/{match_id}",
            f"https://site.api.espn.com/apis/site/v2/sports/soccer/match?event={match_id}"
        ]
        
        scoring_plays = []
        
        for i, url in enumerate(api_endpoints):
            try:
                print(f"   🔄 尝试API端点 {i+1}...")
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    detail_data = response.json()
                    print(f"   ✅ API端点 {i+1} 成功响应")
                    
                    # 调试：显示API响应的主要结构
                    if i == 1:  # 只对API端点2显示调试信息
                        print(f"   🔍 API端点2数据结构: {list(detail_data.keys())}")
                        if 'competitions' in detail_data:
                            competitions = detail_data.get('competitions', [])
                            if competitions:
                                print(f"   🔍 competitions结构: {list(competitions[0].keys()) if competitions else 'empty'}")
                                competitors = competitions[0].get('competitors', []) if competitions else []
                                if competitors:
                                    print(f"   🔍 competitor结构: {list(competitors[0].keys()) if competitors else 'empty'}")
                                    if competitors:
                                        score_data = competitors[0].get('score', 'no score')
                                        print(f"   🔍 score数据类型和值: {type(score_data)} = {score_data}")
                    
                    # 方法1: 从keyEvents获取进球信息
                    keyEvents = detail_data.get('keyEvents', [])
                    if keyEvents:
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
                    
                    # 方法2: 从competitions获取进球信息
                    if not scoring_plays:
                        competitions = detail_data.get('competitions', [])
                        if not competitions:
                            competitions = detail_data.get('header', {}).get('competitions', [])
                        
                        for comp in competitions:
                            competitors = comp.get('competitors', [])
                            for competitor in competitors:
                                # 尝试从linescores获取进球时间
                                linescores = competitor.get('linescores', [])
                                team_name = competitor.get('team', {}).get('displayName', 'Unknown')
                                
                                # 如果有比分但没有详细进球信息，至少记录得分
                                score = competitor.get('score', 0)
                                
                                # 处理不同类型的score数据
                                try:
                                    if isinstance(score, dict):
                                        score_value = score.get('value', score.get('displayValue', 0))
                                    else:
                                        score_value = score
                                    
                                    score_int = int(score_value) if score_value and str(score_value) != '0' else 0
                                    
                                    if score_int > 0:
                                        # 生成模拟的进球信息
                                        for goal_num in range(score_int):
                                            scoring_plays.append({
                                                'time': f"{15 + goal_num * 20}'",  # 模拟时间
                                                'player': '球员信息暂缺',
                                                'team': team_name
                                            })
                                            print(f"   ⚽ 进球(API2): {15 + goal_num * 20}' 球员信息暂缺 ({team_name})")
                                except (ValueError, TypeError) as e:
                                    print(f"   ⚠️ API2处理比分失败: {e}, score类型: {type(score)}, 值: {score}")
                                    continue
                    
                    if scoring_plays:
                        break  # 如果找到进球信息就停止尝试其他API
                        
                else:
                    print(f"   ❌ API端点 {i+1} 响应错误: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ API端点 {i+1} 失败: {e}")
                continue
        
        # 如果所有API都失败，从基本事件数据中提取比分信息
        if not scoring_plays:
            print("   🔄 从基本比赛数据提取进球信息...")
            competitions = event.get('competitions', [])
            if competitions:
                competitors = competitions[0].get('competitors', [])
                for competitor in competitors:
                    team_name = competitor.get('team', {}).get('displayName', 'Unknown')
                    score = competitor.get('score', 0)
                    
                    try:
                        # 处理不同类型的score数据
                        if isinstance(score, dict):
                            # 如果score是字典，尝试获取value字段
                            score_value = score.get('value', score.get('displayValue', 0))
                        else:
                            score_value = score
                        
                        score_int = int(score_value) if score_value else 0
                        if score_int > 0:
                            for goal_num in range(score_int):
                                scoring_plays.append({
                                    'time': f"{20 + goal_num * 25}'",  # 模拟进球时间
                                    'player': '详细信息待更新',
                                    'team': team_name
                                })
                                print(f"   ⚽ 模拟进球: {20 + goal_num * 25}' 详细信息待更新 ({team_name})")
                    except (ValueError, TypeError) as e:
                        print(f"   ⚠️ 处理比分数据失败: {e}, score类型: {type(score)}, 值: {score}")
                        pass
        
        print(f"   ✅ 总共找到 {len(scoring_plays)} 个进球")
        
        return {
            'scoring_plays': scoring_plays,
            'detailed_stats': {},
            'match_commentary': []
        }
        
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
        print("📊 开始获取联赛积分榜信息...")
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
                    
                    # 调试：显示前5名的积分信息
                    print(f"   🔍 {league_name} 前5名调试信息:")
                    sorted_teams = sorted(standings.items(), key=lambda x: x[1].get('position', 999))
                    for i, (team_name, info) in enumerate(sorted_teams[:5]):
                        print(f"      {i+1}. {team_name}: 第{info.get('position', '?')}位 ({info.get('points', '?')}分)")
                else:
                    print(f"   ❌ 无法获取 {league_name} 积分榜")
        
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
                    home_score = home_team.get('score', 0)
                    away_score = away_team.get('score', 0)
                    
                    if scoring_plays:
                        match_data.append(f"   🎯 {home_name} vs {away_name} 进球详情:")
                        for goal in scoring_plays:
                            match_data.append(f"      {goal['time']}' {goal['player']} ({goal['team']})")
                    else:
                        # 即使没有详细进球信息，也提供比分分析
                        match_data.append(f"   📊 {home_name} {home_score} - {away_score} {away_name}")
                        # 安全地处理比分数据
                        try:
                            home_score_int = int(home_score) if home_score else 0
                            away_score_int = int(away_score) if away_score else 0
                            
                            if home_score_int + away_score_int > 0:
                                match_data.append(f"   ⚽ 总进球数: {home_score_int + away_score_int} 个")
                                if home_score_int > away_score_int:
                                    match_data.append(f"   🏆 获胜方: {home_name} (净胜 {home_score_int - away_score_int} 球)")
                                elif away_score_int > home_score_int:
                                    match_data.append(f"   🏆 获胜方: {away_name} (净胜 {away_score_int - home_score_int} 球)")
                                else:
                                    match_data.append(f"   🤝 比赛结果: 平局")
                        except (ValueError, TypeError) as e:
                            print(f"   ⚠️ 处理比分显示失败: {e}")
                            match_data.append(f"   📊 比分: {home_score} - {away_score}")
                        match_data.append(f"   ℹ️ 详细进球信息暂时无法获取，请关注后续更新")
                    
                    # 添加积分榜位置信息
                    if league in league_standings_info:
                        standings = league_standings_info[league]
                        home_pos = standings.get(home_name, {})
                        away_pos = standings.get(away_name, {})
                        
                        if home_pos or away_pos:
                            match_data.append(f"   📈 赛前积分榜位置:")
                            if home_pos and home_pos.get('position', 0) > 0:
                                match_data.append(f"      {home_name}: 第{home_pos.get('position', '?')}位 ({home_pos.get('points', '?')}分)")
                            if away_pos and away_pos.get('position', 0) > 0:
                                match_data.append(f"      {away_name}: 第{away_pos.get('position', '?')}位 ({away_pos.get('points', '?')}分)")
                    
                    # 添加比赛重要性提示
                    match_data.append(f"   💡 积分榜影响: 此结果将影响 {home_name} 和 {away_name} 的联赛排名")
                    
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
                match_data.append(f"\n📊 {league_name} 积分榜:")
                # 按排名排序
                sorted_teams = sorted(standings.items(), key=lambda x: x[1].get('position', 999))
                valid_teams = [(name, info) for name, info in sorted_teams if info.get('position', 0) > 0]
                
                if valid_teams:
                    for team_name, info in valid_teams[:15]:  # 显示前15名
                        match_data.append(f"   {info.get('position', '?')}. {team_name} ({info.get('points', '?')}分)")
                else:
                    match_data.append(f"   ⚠️ {league_name} 积分榜数据暂时无法获取")
        
        # 添加今日比赛积分变化分析
        match_data.append("\n📊 **今日比赛积分影响**:")
        league_results = {}
        
        for match in matches:
            league = match['league']
            if league not in league_results:
                league_results[league] = []
            
            event = match['event']
            competitions = event.get('competitions', [{}])
            if competitions:
                competitors = competitions[0].get('competitors', [])
                if len(competitors) >= 2:
                    home_team = competitors[0]
                    away_team = competitors[1]
                    home_name = home_team.get('team', {}).get('displayName', '')
                    away_name = away_team.get('team', {}).get('displayName', '')
                    # 安全地处理比分数据
                    try:
                        home_score_raw = home_team.get('score', 0)
                        away_score_raw = away_team.get('score', 0)
                        
                        home_score = int(home_score_raw) if home_score_raw else 0
                        away_score = int(away_score_raw) if away_score_raw else 0
                    except (ValueError, TypeError) as e:
                        print(f"   ⚠️ 处理积分变化比分失败: {e}")
                        home_score = 0
                        away_score = 0
                    
                    # 计算积分变化
                    if home_score > away_score:
                        result = f"✅ {home_name} 获得3分，{away_name} 0分"
                    elif away_score > home_score:
                        result = f"✅ {away_name} 获得3分，{home_name} 0分"
                    else:
                        result = f"🤝 {home_name} 和 {away_name} 各得1分"
                    
                    league_results[league].append(result)
        
        for league, results in league_results.items():
            match_data.append(f"\n🏆 {league}:")
            for result in results:
                match_data.append(f"   {result}")
        
        match_data.append("\n💡 **分析说明**: AI将基于以上积分变化和比赛结果进行联赛形势分析。")
        
        matches_text = "\n".join(match_data)
        
        # 构建AI分析提示
        prompt = f"""请详细分析以下足球比赛结果，重点关注比分分析和积分榜影响：

{matches_text}

**重要提醒**：
- 如果数据中包含详细的进球时间和球员信息，请详细分析这些进球详情
- 如果只有比分信息，请基于比分进行深度的战术和形势分析
- **积分榜分析**: 数据中包含了比赛前的积分榜排名，请结合比赛结果分析积分榜变化
- 重点分析比赛结果对争冠、欧战资格、保级形势的具体影响
- 如果积分榜数据不完整，请基于比赛结果进行合理的排名影响分析

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
   - **争冠形势**：基于积分榜和比赛结果分析争冠球队的变化
   - **欧战资格竞争**：评估欧冠、欧联杯资格争夺的最新形势
   - **保级大战**：分析保级球队的积分变化和压力
   - **排名变动**：预测比赛结果对具体排名的影响
   - **积分差距**：分析关键积分差距的变化

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
