# app/notification/routes.py

from flask import Blueprint, request
from app.auth.routes import token_required
from app.utils import json_response
from app.notification.telegram import send_telegram_message

notification_bp = Blueprint('notification', __name__)


@notification_bp.route('/telegram/test', methods=['POST'])
@token_required
def test_telegram(current_user):
    """텔레그램 알림 테스트"""
    msg = f"✅ 텔레그램 연동 성공!\n{current_user.email} 계정의 키워드 순위 알림이 여기로 옵니다."
    success = send_telegram_message(msg)

    if success:
        return json_response({'message': '텔레그램 테스트 메시지 발송 성공!'})
    else:
        return json_response({'message': '발송 실패. TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 환경변수를 확인하세요.'}, status=500)


@notification_bp.route('/telegram/report', methods=['POST'])
@token_required
def manual_report(current_user):
    """수동으로 전체 순위 체크 + 텔레그램 리포트 발송"""
    from app.scheduler import check_all_keywords_and_notify
    from flask import current_app

    try:
        check_all_keywords_and_notify(current_app._get_current_object())
        return json_response({'message': '전체 순위 체크 및 리포트 발송 완료!'})
    except Exception as e:
        return json_response({'message': f'리포트 발송 실패: {str(e)}'}, status=500)
