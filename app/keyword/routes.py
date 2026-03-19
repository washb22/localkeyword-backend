# app/keyword/routes.py

from flask import Blueprint, request
from app.models import db, Keyword
from app.auth.routes import token_required
from .scraper import run_check
from datetime import datetime, timezone
from app.utils import json_response
import traceback
import io
import csv

keyword_bp = Blueprint('keyword', __name__)


@keyword_bp.route('/keywords', methods=['POST'])
@token_required
def create_keyword(current_user):
    data = request.get_json()
    if not data or not 'keyword_text' in data or not 'post_url' in data:
        return json_response({'message': 'Required fields are missing!'}, status=400)
    new_keyword = Keyword(
        user_id=current_user.id,
        keyword_text=data['keyword_text'],
        post_url=data['post_url'],
        post_title=data.get('post_title'),
        priority=data.get('priority', '중')
    )
    db.session.add(new_keyword)
    db.session.commit()
    return json_response({'message': 'New keyword created!'}, status=201)


@keyword_bp.route('/keywords/upload', methods=['POST'])
@token_required
def upload_keywords(current_user):
    """엑셀/CSV 파일로 키워드 일괄 등록"""
    if 'file' not in request.files:
        return json_response({'message': '파일이 없습니다.'}, status=400)

    file = request.files['file']
    if not file.filename:
        return json_response({'message': '파일이 선택되지 않았습니다.'}, status=400)

    try:
        content = file.read()

        # CSV 파싱 시도 (UTF-8 → EUC-KR 순서)
        text = None
        for encoding in ['utf-8-sig', 'utf-8', 'euc-kr', 'cp949']:
            try:
                text = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if text is None:
            return json_response({'message': '파일 인코딩을 인식할 수 없습니다.'}, status=400)

        # TSV(탭 구분) 또는 CSV(쉼표 구분) 자동 감지
        if '\t' in text.split('\n')[0]:
            reader = csv.reader(io.StringIO(text), delimiter='\t')
        else:
            reader = csv.reader(io.StringIO(text))

        rows = list(reader)
        created_count = 0
        skipped_count = 0

        for row in rows:
            if len(row) < 2:
                skipped_count += 1
                continue

            keyword_text = row[0].strip()
            post_url = row[1].strip()
            post_title = row[2].strip() if len(row) > 2 else None
            priority = row[3].strip() if len(row) > 3 else '중'

            # 헤더 행 스킵
            if keyword_text in ('키워드', 'keyword', ''):
                continue
            if not keyword_text or not post_url:
                skipped_count += 1
                continue
            # URL 형식 기본 검증
            if not post_url.startswith('http'):
                skipped_count += 1
                continue

            new_keyword = Keyword(
                user_id=current_user.id,
                keyword_text=keyword_text,
                post_url=post_url,
                post_title=post_title if post_title else None,
                priority=priority if priority in ('상', '중', '하') else '중'
            )
            db.session.add(new_keyword)
            created_count += 1

        db.session.commit()
        return json_response({
            'message': f'{created_count}개 키워드가 등록되었습니다. (건너뜀: {skipped_count}개)',
            'created': created_count,
            'skipped': skipped_count
        }, status=201)

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return json_response({'message': f'파일 처리 중 오류: {str(e)}'}, status=500)


@keyword_bp.route('/keywords', methods=['GET'])
@token_required
def get_keywords(current_user):
    keywords = Keyword.query.filter_by(user_id=current_user.id).order_by(Keyword.id.desc()).all()
    output = []
    for keyword in keywords:
        keyword_data = {
            'id': keyword.id,
            'keyword_text': keyword.keyword_text,
            'post_url': keyword.post_url,
            'post_title': keyword.post_title,
            'priority': keyword.priority,
            'ranking_status': keyword.ranking_status,
            'ranking': keyword.ranking,
            'section': keyword.section,
            'prev_ranking': keyword.prev_ranking,
            'prev_section': keyword.prev_section,
            'prev_ranking_status': keyword.prev_ranking_status,
            'last_checked_at': keyword.last_checked_at.isoformat() if keyword.last_checked_at else None
        }
        output.append(keyword_data)
    return json_response({'keywords': output})


@keyword_bp.route('/keywords/<int:keyword_id>/check', methods=['POST'])
@token_required
def check_keyword_ranking(current_user, keyword_id):
    keyword = Keyword.query.filter_by(id=keyword_id, user_id=current_user.id).first()
    if not keyword:
        return json_response({'message': 'Keyword not found or permission denied'}, status=404)

    try:
        print(f"키워드 '{keyword.keyword_text}' 순위 확인 시작...")

        status, rank, section = run_check(keyword.keyword_text, keyword.post_url, keyword.post_title)

        print(f"스크래핑 결과 - 상태: {status}, 순위: {rank}, 섹션: {section}")

        # 현재 값을 이전 값으로 저장
        keyword.prev_ranking = keyword.ranking
        keyword.prev_section = keyword.section
        keyword.prev_ranking_status = keyword.ranking_status

        # 새 값으로 업데이트
        keyword.ranking_status = status
        keyword.ranking = rank
        keyword.section = section
        keyword.last_checked_at = datetime.now(timezone.utc)

        db.session.commit()
        print("DB 업데이트 완료")

        if rank and rank > 0:
            response_message = f'순위 확인 완료. {section} 섹션에서 {rank}위에 노출되고 있습니다.'
        elif status == "노출X":
            response_message = f'순위 확인 완료. 현재 노출되지 않고 있습니다.'
        else:
            response_message = f'순위 확인 완료. 상태: {status}'

        return json_response({
            'message': response_message,
            'status': status,
            'ranking': rank,
            'section': section
        })

    except Exception as e:
        print(f"순위 확인 중 오류 발생: {str(e)}")
        traceback.print_exc()
        return json_response({'message': f'순위 확인 중 오류가 발생했습니다: {str(e)}'}, status=500)


@keyword_bp.route('/keywords/<int:keyword_id>', methods=['PUT'])
@token_required
def update_keyword(current_user, keyword_id):
    keyword = Keyword.query.filter_by(id=keyword_id, user_id=current_user.id).first()
    if not keyword:
        return json_response({'message': 'Keyword not found or permission denied'}, status=404)

    data = request.get_json()
    if not data:
        return json_response({'message': 'Request body is missing!'}, status=400)

    keyword.keyword_text = data.get('keyword_text', keyword.keyword_text)
    keyword.post_title = data.get('post_title', keyword.post_title)
    keyword.post_url = data.get('post_url', keyword.post_url)
    keyword.priority = data.get('priority', keyword.priority)

    db.session.commit()

    updated_keyword_data = {
        'id': keyword.id,
        'keyword_text': keyword.keyword_text,
        'post_url': keyword.post_url,
        'priority': keyword.priority,
    }
    return json_response({'message': 'Keyword updated successfully!', 'keyword': updated_keyword_data})


@keyword_bp.route('/keywords/<int:keyword_id>', methods=['DELETE'])
@token_required
def delete_keyword(current_user, keyword_id):
    keyword = Keyword.query.filter_by(id=keyword_id, user_id=current_user.id).first()
    if not keyword:
        return json_response({'message': 'Keyword not found or permission denied'}, status=404)

    db.session.delete(keyword)
    db.session.commit()

    return json_response({'message': f'Keyword with ID {keyword_id} has been deleted.'})
