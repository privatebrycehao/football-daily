import os
import requests
import time
from datetime import datetime, date, timedelta
import pytz

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
                    
                    # 检查已完成的比赛
                    if status == 'STATUS_FINAL':
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
        
        # 简化队名（取最后一个单词或前15个字符）
        home_short = home_name.split()[-1] if ' ' in home_name else home_name[:15]
        away_short = away_name.split()[-1] if ' ' in away_name else away_name[:15]
        
        # 格式化结果
        result = f"⚽ **{league}**: {away_short} {away_score} - {home_score} {home_short}"
        
        return result
        
    except Exception as e:
        return f"⚽ {match.get('league', 'Unknown')}: 解析比赛数据失败 - {e}"

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
