# Yahboom Raspbot 하드웨어 레퍼런스

Yahboom 공식 GitHub(`YahboomTechnology/Raspbot`)의 튜토리얼 PDF에서 확인한
실제 핀맵/라이브러리 API 정리. 로봇 도착 후 `mock_controller`의 `_move()`,
`_check_obstacle()`, 라인트레이싱 부분, 부저를 실물 코드로 교체할 때 참고.

## 핵심 결론: WebSocket 아님, 전부 로컬 파이썬 라이브러리/GPIO

이전에 "라즈베리파이가 WebSocket 서버(포트6000)로 명령을 받을 것"이라고
추측했었는데, 틀렸다. 실제로는:
- **모터**: 라즈베리파이 → I2C(SDA.1/SCL.1) → STM8 MCU → AT8236 드라이버 칩
  → 4개 TT 모터. 우리 코드는 그냥 `YB_Pcb_Car.py` 라이브러리를 import해서
  직접 함수 호출하면 됨. 앱의 WebSocket 서버는 "그들의 앱"이 붙는 용도일
  뿐, 우리 스크립트는 그걸 거칠 필요가 없다.
- **부저/초음파/라인트레이싱**: 전부 라즈베리파이 GPIO에 직결, `RPi.GPIO`로
  직접 제어.

라이브러리 파일 위치(실제 Pi 위): `/home/pi/Yahboom_project/Raspbot/2.Hardware Control course/2.Drive motor/YB_Pcb_Car.py`

## 모터 (YB_Pcb_Car.py)

```python
import YB_Pcb_Car
car = YB_Pcb_Car.YB_Pcb_Car()

car.Car_Run(150, 150)   # 전진, 속도 0~255 (좌/우 바퀴 각각)
car.Car_Back(150, 150)  # 후진
car.Car_Stop()          # 정지
# left/right(제자리 회전) 함수명은 QR코드 리모컨 이미지에서
# spin_left.png / spin_right.png 로 확인됨 — 실물 도착 후
# YB_Pcb_Car.py 안에서 정확한 함수명 확인 필요 (Car_Left/Car_Right 등으로
# 추정되나 미확정)

del car  # 다 쓰면 반드시 해제 (안 하면 다음 실행 때 점유 에러)
```

## 부저 (RPi.GPIO 직결, Supabase 명령과 무관)

- 핀: **BOARD 32번 (BCM 12번)**
- Passive buzzer, PWM으로 주파수를 바꿔서 소리/멜로디 생성

```python
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BOARD)
GPIO.setup(32, GPIO.OUT)
buzz = GPIO.PWM(32, 440)
buzz.start(50)
buzz.ChangeFrequency(880)  # 음 바꾸기
buzz.stop()
GPIO.cleanup()
```
→ **결론(Task #11 관련)**: Supabase `robot_commands`에 없는 값이라 웹에서
직접 명령을 못 보내지만, 어차피 GPIO 직결이라 **Pi가 특정 이벤트(예:
patrol_start 수신, 장애물 감지)에 자체적으로 울리면 됨** — 팀 스키마 변경
불필요.

## 초음파 (RPi.GPIO 직결)

- Echo: **BOARD 18번 (BCM 24)**, Trig: **BOARD 16번 (BCM 23)**
- 측정 범위 3~450cm

```python
import RPi.GPIO as GPIO
import time

EchoPin, TrigPin = 18, 16
GPIO.setmode(GPIO.BOARD)
GPIO.setup(EchoPin, GPIO.IN)
GPIO.setup(TrigPin, GPIO.OUT)

def Distance():
    GPIO.output(TrigPin, GPIO.LOW)
    time.sleep(0.000002)
    GPIO.output(TrigPin, GPIO.HIGH)
    time.sleep(0.000015)
    GPIO.output(TrigPin, GPIO.LOW)

    t3 = time.time()
    while not GPIO.input(EchoPin):
        if time.time() - t3 > 0.03:
            return -1
    t1 = time.time()
    while GPIO.input(EchoPin):
        if time.time() - t1 > 0.03:
            return -1
    t2 = time.time()
    return (t2 - t1) * 340 / 2 * 100  # cm
```
→ `mock_controller/controller.py`의 `_check_obstacle()`을 이 `Distance()`
호출 결과가 `OBSTACLE_STOP_DISTANCE_CM` 이하인지로 교체하면 됨.

## 라인트레이싱 4채널 (RPi.GPIO 직결)

- Left1: BOARD 13 (BCM27), Left2: BOARD 15 (BCM22)
- Right1: BOARD 11 (BCM17), Right2: BOARD 7 (BCM4)
- 값 0 = 검은선 감지, 1 = 흰색(바탕) 감지

```python
GPIO.setup(13, GPIO.IN)  # Left1
GPIO.setup(15, GPIO.IN)  # Left2
GPIO.setup(11, GPIO.IN)  # Right1
GPIO.setup(7, GPIO.IN)   # Right2
```
→ `_patrol_loop()` 안의 "라인트레이싱 센서 읽어서 조향 보정" 부분을 이걸로
채우면 됨.

## Wi-Fi: AP(자체 핫스팟) → STA(일반 WiFi) 전환

로봇 기본 핫스팟 IP는 `10.42.0.1` (여기로 먼저 SSH 접속).

헤드리스(SSH) 환경에서 STA 전환 순서:
```bash
sudo raspi-config
# Localisation Options → WLAN Country → KR (Korea) 선택 → OK → Finish

nmcli radio wifi          # 현재 상태 확인
nmcli radio wifi on       # 꺼져있으면 켜기
sudo nmcli dev wifi list  # 주변 WiFi 검색
sudo nmcli --ask dev wifi connect <SSID>   # 연결 (비밀번호 물어봄)
```
연결 성공하면 그 시점부터 그 WiFi의 IP로 SSH 접속 가능. 로봇 자체 핫스팟과
일반 WiFi 중 뭘 우선할지는 NetworkManager 연결 우선순위(priority) 설정으로
정할 수 있음 — 부팅 시 자동으로 특정 WiFi에 붙게 하려면 이 우선순위를
높여주면 됨.

## 출처

Yahboom 공식 GitHub 저장소(`YahboomTechnology/Raspbot`)의 튜토리얼 PDF:
`5.Hardware Control course/{1.Drive buzzer, 2.Drive motor, 4.Ultrasonic ranging, 7.Tracking}.pdf`,
`3.Preparation/3.Raspbot-PI5 Connection WiFi Method.docx`
