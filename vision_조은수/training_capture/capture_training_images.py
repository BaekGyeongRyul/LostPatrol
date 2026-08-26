"""
capture_training_images.py — 실물 Razbot 카메라로 재학습용 사진을 연속 촬영한다.

배경: 2026.08.26 실물 테스트에서 스테인리스 텀블러 미검출, 투명 페트병
umbrella 오분류 발견. 원인으로 의심되는 것 중 하나가 학습 데이터(폰카메라
사진)와 실제 로봇 카메라(CSI, 각도/색감 다름) 사진의 괴리라서, 조은수의
재학습을 돕기 위해 로봇 카메라로 직접 촬영한 사진을 모아준다.

사용법 (Pi 위, mock_controller와 같은 rpicam-still 촬영 설정 사용):
    python3 capture_training_images.py <라벨> [장수]
    예: python3 capture_training_images.py bottle 15

라벨별로 폴더를 만들고 그 안에 순번 붙여 저장한다 (bottle/bottle_01.jpg, ...).
매 장마다 3초 카운트다운을 주니, 그 사이에 물체를 살짝 돌리거나 각도/거리를
바꿔서 다양한 사진이 나오게 하면 된다.
"""

import subprocess
import sys
import time
from pathlib import Path

RPICAM_STILL = "rpicam-still"
OUT_ROOT = Path(__file__).parent / "captured"

# controller.py의 _grab_frame_rpicam()과 동일한 설정 — 실물 테스트로 확정된
# 값(뒤집힘 보정 rotation 180, 초록빛 보정 awb daylight)을 그대로 맞춘다.
CAMERA_ARGS = [
    "-o", "-", "-t", "1000", "-n",
    "--rotation", "180",
    "--awb", "daylight",
    "--width", "1296", "--height", "972",
]


def capture_one(out_path: Path) -> bool:
    try:
        result = subprocess.run(
            [RPICAM_STILL, *CAMERA_ARGS],
            capture_output=True, timeout=15, check=True,
        )
    except Exception as exc:
        print(f"  촬영 실패: {exc}")
        return False
    out_path.write_bytes(result.stdout)
    return True


def main():
    if len(sys.argv) < 2:
        print("사용법: python3 capture_training_images.py <라벨> [장수(기본 15)]")
        sys.exit(1)

    label = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 15

    out_dir = OUT_ROOT / label
    out_dir.mkdir(parents=True, exist_ok=True)

    # 이미 있는 파일과 안 겹치게 다음 번호부터 시작
    existing = sorted(out_dir.glob(f"{label}_*.jpg"))
    start_idx = len(existing) + 1

    print(f"'{label}' 라벨로 {count}장 촬영합니다 (저장 위치: {out_dir})")
    print("매 장마다 3초 드릴게요 — 물체를 조금씩 돌리거나 각도/거리를 바꿔주세요.\n")

    saved = 0
    for i in range(start_idx, start_idx + count):
        for remaining in (3, 2, 1):
            print(f"  [{saved + 1}/{count}] {remaining}초 후 촬영...", end="\r")
            time.sleep(1)
        out_path = out_dir / f"{label}_{i:02d}.jpg"
        if capture_one(out_path):
            saved += 1
            print(f"  [{saved}/{count}] 저장 완료: {out_path.name}          ")
        else:
            print(f"  [{saved}/{count}] 건너뜀 (촬영 실패)              ")

    print(f"\n완료 — 총 {saved}장 저장됨: {out_dir}")


if __name__ == "__main__":
    main()
