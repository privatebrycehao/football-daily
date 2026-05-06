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

def analyze_matches_with_ai(matches):
    """使用DeepSeek AI分析足球比赛结果"""
    api_key = os.getenv('DEEPSEEK_KEY')
    if not api_key:
        print("⚠️ 未设置DEEPSEEK_KEY，使用简单分析")
        return analyze_matches_simple(matches)
    
    if not matches:
        return "没有比赛数据可供分析"
    
    try:
        # 准备简化的比赛数据给AI分析
        match_data = []
        
        print("📊 准备比赛数据（简化版）...")
        
        for match in matches:
            # 基本比赛信息
            basic_result = format_match_result(match)
            match_data.append(basic_result)
            
            # 添加简单的比分分析
            event = match['event']
            competitions = event.get('competitions', [{}])
            if competitions:
                competitors = competitions[0].get('competitors', [])
                
                if len(competitors) >= 2:
                    home_team = competitors[0]
                    away_team = competitors[1]
                    home_name = home_team.get('team', {}).get('displayName', '')
                    away_name = away_team.get('team', {}).get('displayName', '')
                    home_score = home_team.get('score', 0)
                    away_score = away_team.get('score', 0)
                    
                    # 添加比分分析
                    try:
                        home_score_int = int(home_score) if home_score else 0
                        away_score_int = int(away_score) if away_score else 0
                        
                        if home_score_int + away_score_int > 0:
                            match_data.append(f"   📊 总进球数: {home_score_int + away_score_int} 个")
                            if home_score_int > away_score_int:
                                match_data.append(f"   🏆 获胜方: {home_name} (净胜 {home_score_int - away_score_int} 球)")
                            elif away_score_int > home_score_int:
                                match_data.append(f"   🏆 获胜方: {away_name} (净胜 {away_score_int - home_score_int} 球)")
                            else:
                                match_data.append(f"   🤝 比赛结果: 平局")
                    except (ValueError, TypeError):
                        match_data.append(f"   📊 比分: {home_score} - {away_score}")
        
        # 简化版不获取积分榜信息
        match_data.append("\n💡 **分析说明**: AI将基于比分和比赛结果进行分析。")
        
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
        prompt = f"""请分析以下足球比赛结果：

{matches_text}

请提供以下内容：

1. **整体赛况总结**：
   - 今日比赛的整体特点和亮点
   - 意外结果和惊喜表现
   - 各联赛的竞争态势

2. **比赛结果分析**：
   - 基于比分分析比赛的激烈程度
   - 识别大胜、平局、小胜等不同类型的比赛
   - 分析哪些结果可能是冷门

3. **联赛影响分析**：
   - 分析比赛结果对争冠形势的影响
   - 评估欧战资格竞争的变化
   - 分析保级形势的变化

4. **球队表现评价**：
   - 评价各队的表现和状态
   - 分析强队和弱队的表现是否符合预期

请用专业且生动的中文撰写，重点关注比分和结果分析。"""

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000,
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
