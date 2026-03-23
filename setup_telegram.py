# setup_telegram.py
# 텔레그램 알림 설정 도우미
# 직원들이 이 스크립트만 실행하면 자동으로 세팅됨

import requests
import os
import time

BOT_TOKEN = "8310646914:AAEVtBvwZj4NwpN7D61B2x4CAVqBXye1RDc"
BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def main():
    print("=" * 50)
    print("  키워드 순위 알림 - 텔레그램 설정")
    print("=" * 50)
    print()
    print("1. 텔레그램에서 @wkrgudkeyword_bot 을 검색하세요")
    print("2. '시작' 버튼을 누르세요")
    print("3. 아무 메시지나 보내세요 (예: 안녕)")
    print()
    print("텔레그램 이름을 입력하세요 (예: 홍길동)")
    my_name = input("이름: ").strip()
    print()
    print("Chat ID 확인 중...")

    try:
        resp = requests.get(f"{BOT_URL}/getUpdates", timeout=10)
        data = resp.json()

        if not data.get('ok') or not data.get('result'):
            print("메시지를 찾을 수 없습니다. 봇에게 메시지를 보낸 후 다시 시도하세요.")
            return

        # 모든 메시지에서 이름이 일치하는 사람의 chat_id 찾기
        chat_id = None
        name = None
        for update in reversed(data['result']):
            msg = update.get('message', {})
            first_name = msg.get('from', {}).get('first_name', '')
            last_name = msg.get('from', {}).get('last_name', '')
            full_name = f"{last_name}{first_name}".strip()

            if my_name in full_name or full_name in my_name:
                chat_id = msg['chat']['id']
                name = full_name
                break

        if not chat_id:
            # 이름 매칭 실패시 모든 사용자 목록 표시
            print("이름이 일치하는 사용자를 찾을 수 없습니다.")
            print()
            seen = set()
            users = []
            for update in data['result']:
                msg = update.get('message', {})
                cid = msg.get('chat', {}).get('id')
                if cid and cid not in seen:
                    seen.add(cid)
                    fn = msg.get('from', {}).get('first_name', '')
                    ln = msg.get('from', {}).get('last_name', '')
                    users.append((cid, f"{ln}{fn}".strip()))

            if users:
                print("봇에 메시지를 보낸 사용자 목록:")
                for i, (cid, uname) in enumerate(users, 1):
                    print(f"  {i}. {uname} (ID: {cid})")
                print()
                choice = input("번호를 선택하세요: ").strip()
                try:
                    idx = int(choice) - 1
                    chat_id = users[idx][0]
                    name = users[idx][1]
                except (ValueError, IndexError):
                    print("잘못된 선택입니다.")
                    return
            else:
                print("봇에게 메시지를 보낸 후 다시 시도하세요.")
                return

        print(f"이름: {name}")
        print(f"Chat ID: {chat_id}")
        print()

        # .env 파일 생성/업데이트
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        env_lines = []

        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.startswith('TELEGRAM_BOT_TOKEN') and not line.startswith('TELEGRAM_CHAT_ID'):
                        env_lines.append(line)

        env_lines.append(f"TELEGRAM_BOT_TOKEN={BOT_TOKEN}\n")
        env_lines.append(f"TELEGRAM_CHAT_ID={chat_id}\n")

        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(env_lines)

        print(f".env 파일 저장 완료!")
        print()

        # 테스트 메시지 발송
        test_msg = f"{name}님, 키워드 순위 알림이 설정되었습니다!\n매일 아침 8시에 순위 리포트가 여기로 옵니다."
        test_resp = requests.post(f"{BOT_URL}/sendMessage", json={
            'chat_id': chat_id,
            'text': test_msg
        }, timeout=10)

        if test_resp.json().get('ok'):
            print("테스트 메시지 발송 성공! 텔레그램을 확인하세요.")
        else:
            print("테스트 메시지 발송 실패. 설정은 완료되었으니 수동 확인하세요.")

    except Exception as e:
        print(f"오류 발생: {e}")
        print("다시 시도해주세요.")

    print()
    print("=" * 50)
    print("  설정 완료! 컴퓨터가 켜져 있으면")
    print("  매일 아침 8시에 알림이 옵니다.")
    print("=" * 50)
    input("Enter를 누르면 종료됩니다... ")


if __name__ == '__main__':
    main()
