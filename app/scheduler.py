# app/scheduler.py

from datetime import datetime, timezone
from app.models import db, Keyword, User
from app.keyword.scraper import run_check
from app.notification.telegram import send_telegram_message, format_ranking_report
from app.spreadsheet.sync import sync_to_spreadsheet
import time
import random


def check_all_keywords_and_notify(app):
    """전체 키워드 순위 체크 후 텔레그램 알림"""
    with app.app_context():
        users = User.query.all()

        for user in users:
            keywords = Keyword.query.filter_by(user_id=user.id).all()
            if not keywords:
                continue

            print(f"[스케줄러] {user.email} - {len(keywords)}개 키워드 체크 시작")

            results = []
            for kw in keywords:
                try:
                    status, rank, section = run_check(kw.keyword_text, kw.post_url, kw.post_title)

                    # 이전 값 저장
                    kw.prev_ranking = kw.ranking
                    kw.prev_section = kw.section
                    kw.prev_ranking_status = kw.ranking_status

                    # 새 값 업데이트
                    kw.ranking_status = status
                    kw.ranking = rank
                    kw.section = section
                    kw.last_checked_at = datetime.now(timezone.utc)

                    results.append({
                        'keyword_text': kw.keyword_text,
                        'status': status,
                        'ranking': rank,
                        'section': section,
                        'prev_ranking': kw.prev_ranking,
                        'priority': kw.priority
                    })

                    # 네이버 차단 방지 딜레이
                    time.sleep(random.uniform(3, 6))

                except Exception as e:
                    print(f"[스케줄러] '{kw.keyword_text}' 체크 실패: {e}")
                    results.append({
                        'keyword_text': kw.keyword_text,
                        'status': '확인 실패',
                        'ranking': 999,
                        'section': None,
                        'prev_ranking': kw.prev_ranking,
                        'priority': kw.priority
                    })

            db.session.commit()

            # 스프레드시트 동기화
            if results:
                kw_data = [{
                    'priority': kw.priority, 'keyword_text': kw.keyword_text,
                    'post_title': kw.post_title, 'post_url': kw.post_url,
                    'ranking_status': kw.ranking_status, 'ranking': kw.ranking,
                    'section': kw.section, 'prev_ranking': kw.prev_ranking,
                    'prev_section': kw.prev_section, 'prev_ranking_status': kw.prev_ranking_status
                } for kw in keywords]
                sync_to_spreadsheet(kw_data, user.email)

            # 텔레그램 발송
            if results:
                report = format_ranking_report(results)
                send_telegram_message(report)
                print(f"[스케줄러] {user.email} - 리포트 발송 완료")
