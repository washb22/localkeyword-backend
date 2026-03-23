# app/notification/telegram.py

import os
import requests

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')


def send_telegram_message(text, chat_id=None, bot_token=None):
    """텔레그램 메시지 발송"""
    token = bot_token or TELEGRAM_BOT_TOKEN
    cid = chat_id or TELEGRAM_CHAT_ID

    if not token or not cid:
        print("텔레그램 설정 누락 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': cid,
        'text': text,
        'parse_mode': 'HTML'
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print("텔레그램 발송 성공")
            return True
        else:
            print(f"텔레그램 발송 실패: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        print(f"텔레그램 발송 오류: {e}")
        return False


def format_ranking_report(results):
    """순위 체크 결과를 텔레그램 리포트 형식으로 변환"""
    now_str = __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')

    lines = [f"<b>📊 키워드 순위 리포트</b>", f"<i>{now_str}</i>", ""]

    # 우선순위별 그룹핑
    groups = {'상': [], '중': [], '하': []}
    for r in results:
        p = r.get('priority', '중')
        groups.get(p, groups['중']).append(r)

    for priority, items in groups.items():
        if not items:
            continue

        lines.append(f"<b>【우선순위: {priority}】</b>")

        for r in items:
            keyword = r['keyword_text']
            status = r['status']
            rank = r['ranking']
            section = r.get('section', '')
            prev_rank = r.get('prev_ranking')

            # 상태 이모지
            if status == '노출X':
                emoji = '❌'
                detail = '미노출'
            elif status == '확인 실패':
                emoji = '⚠️'
                detail = '확인 실패'
            else:
                if rank and rank <= 3:
                    emoji = '🔥'
                elif rank and rank <= 7:
                    emoji = '✅'
                else:
                    emoji = '📍'
                detail = f'{section} {rank}위'

            # 변동 표시
            change = ''
            if prev_rank and rank and prev_rank != rank and rank < 999 and prev_rank < 999:
                diff = prev_rank - rank
                if diff > 0:
                    change = f' (▲{diff})'
                else:
                    change = f' (▼{abs(diff)})'

            lines.append(f"{emoji} <b>{keyword}</b> — {detail}{change}")

        lines.append("")

    # 요약
    total = len(results)
    exposed = sum(1 for r in results if r['status'] not in ('노출X', '확인 실패', '확인 대기'))
    lines.append(f"<b>총 {total}개 키워드 | 노출 {exposed}개 | 미노출 {total - exposed}개</b>")

    return "\n".join(lines)
