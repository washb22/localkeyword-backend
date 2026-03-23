# cron_job.py
# Render Cron Job에서 실행하는 독립 스크립트
# 매일 아침 순위 체크 + 텔레그램 알림

from app import create_app, db
from app.scheduler import check_all_keywords_and_notify

app = create_app()
check_all_keywords_and_notify(app)
print("Cron job 완료")
