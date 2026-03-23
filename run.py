from app import create_app, db
import os

app = create_app()

# 데이터베이스 테이블 생성 추가
with app.app_context():
    db.create_all()

# APScheduler 설정 (매일 아침 8시 한국시간 = UTC 23시 전날)
def start_scheduler():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from app.scheduler import check_all_keywords_and_notify

        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=lambda: check_all_keywords_and_notify(app),
            trigger='cron',
            hour=23,  # UTC 23시 = KST 08시
            minute=0,
            id='daily_ranking_check',
            replace_existing=True
        )
        scheduler.start()
        print("✅ 스케줄러 시작됨 - 매일 KST 08:00 순위 체크")
    except ImportError:
        print("⚠️ APScheduler 미설치 - 자동 순위 체크 비활성화")
    except Exception as e:
        print(f"⚠️ 스케줄러 시작 실패: {e}")

start_scheduler()

if __name__ == '__main__':
    app.run(debug=False, port=5000)
