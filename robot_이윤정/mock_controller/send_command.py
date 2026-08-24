"""
send_command.py — 웹에서 버튼을 누른 것을 흉내내는 테스트 도구.

백경률의 웹 화면이 아직 없으니, 대신 터미널에서 이 스크립트로
명령을 넣어서 controller.py가 잘 반응하는지 확인한다.

나중에 웹이 완성되면, 웹 서버가 하는 일이 정확히 이 스크립트가
지금 하는 일(add_command 호출)과 같다 — 그래서 이 스크립트가
곧 "웹이 해야 할 일"의 명세서 역할도 한다.

사용법:
    python send_command.py forward
    python send_command.py capture
    python send_command.py stop
"""

import sys
import store

VALID_COMMANDS = {
    "forward", "backward", "left", "right", "stop",
    "capture", "buzz", "patrol_start", "patrol_stop",
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in VALID_COMMANDS:
        print(f"사용법: python send_command.py <명령>")
        print(f"가능한 명령: {', '.join(sorted(VALID_COMMANDS))}")
        sys.exit(1)

    store.init_store()
    command = sys.argv[1]
    record = store.add_command(command)
    print(f"명령 전송됨: id={record['id']} command={record['command']}")
    print("controller.py가 실행 중이면 곧 처리될 것입니다.")


if __name__ == "__main__":
    main()
