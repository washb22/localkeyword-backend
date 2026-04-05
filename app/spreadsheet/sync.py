# app/spreadsheet/sync.py
# 구글 스프레드시트 자동 동기화 모듈

import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# 우선순위 정렬 순서
PRIORITY_ORDER = {'상': 0, '중': 1, '하': 2}


def get_gspread_client():
    """서비스 계정으로 gspread 클라이언트 생성"""
    key_path = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY')
    if not key_path:
        print("[스프레드시트] GOOGLE_SERVICE_ACCOUNT_KEY 환경변수가 설정되지 않았습니다.")
        return None

    # JSON 문자열 또는 파일 경로 모두 지원
    try:
        if key_path.strip().startswith('{'):
            info = json.loads(key_path)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        else:
            creds = Credentials.from_service_account_file(key_path, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        print(f"[스프레드시트] 인증 실패: {e}")
        return None


def sync_to_spreadsheet(keywords_data, user_email=None):
    """키워드 순위 데이터를 구글 스프레드시트에 동기화"""
    spreadsheet_id = os.environ.get('GOOGLE_SPREADSHEET_ID')
    if not spreadsheet_id:
        print("[스프레드시트] GOOGLE_SPREADSHEET_ID 환경변수가 설정되지 않았습니다.")
        return False

    client = get_gspread_client()
    if not client:
        return False

    try:
        spreadsheet = client.open_by_key(spreadsheet_id)

        # 시트 이름: 사용자 이메일 또는 '키워드 순위'
        sheet_name = user_email or '키워드 순위'
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=500, cols=10)

        # 우선순위 순으로 정렬
        sorted_data = sorted(keywords_data, key=lambda x: PRIORITY_ORDER.get(x.get('priority', '중'), 1))

        # 헤더
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        headers = ['우선순위', '키워드', '글 제목', 'URL', '이전 상태', '이전 순위', '현재 상태', '현재 순위', '변동', f'마지막 확인: {now_str}']

        # 데이터 행 생성
        rows = [headers]
        for kw in sorted_data:
            status = kw.get('ranking_status', '확인 대기')
            rank = kw.get('ranking')
            section = kw.get('section', '')
            prev_status = kw.get('prev_ranking_status', '')
            prev_rank = kw.get('prev_ranking')
            prev_section = kw.get('prev_section', '')

            # 현재 상태 텍스트
            if status == '노출X':
                current_display = '미노출'
            elif rank and rank < 999:
                current_display = f'{section} {rank}위'
            else:
                current_display = status

            # 이전 상태 텍스트
            if prev_status == '노출X':
                prev_display = '미노출'
            elif prev_rank and prev_rank < 999:
                prev_display = f'{prev_section} {prev_rank}위'
            elif prev_status:
                prev_display = prev_status
            else:
                prev_display = '-'

            # 변동 계산
            change = ''
            if prev_rank and rank and prev_rank < 999 and rank < 999:
                diff = prev_rank - rank
                if diff > 0:
                    change = f'▲{diff}'
                elif diff < 0:
                    change = f'▼{abs(diff)}'
                else:
                    change = '-'

            rows.append([
                kw.get('priority', '중'),
                kw.get('keyword_text', ''),
                kw.get('post_title', '') or '',
                kw.get('post_url', ''),
                prev_display,
                prev_rank if prev_rank and prev_rank < 999 else '',
                current_display,
                rank if rank and rank < 999 else '',
                change,
                ''
            ])

        # 시트 전체 업데이트 (기존 내용 덮어쓰기)
        worksheet.clear()
        worksheet.update(range_name='A1', values=rows)

        # 헤더 서식 (볼드 + 배경색)
        worksheet.format('A1:J1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.95}
        })

        # 열 너비 자동 조정은 API 미지원이므로 패스

        print(f"[스프레드시트] '{sheet_name}' 시트에 {len(rows) - 1}개 키워드 동기화 완료")
        return True

    except Exception as e:
        print(f"[스프레드시트] 동기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
