# Week 3 실습 검증본

작업을 배정한 다음 선정된 에이전트가 실제 도구로 수행하는 Contract Net.
Python 3 표준 라이브러리만 필요하다. 설계와 Mermaid는 [PLAN.md](PLAN.md).

## 1. 시스템 아키텍처

매니저와 평가기는 일반 코드다. 세 담당자 각각은 역할 프롬프트를 가진 LLM이다.
입찰에는 정답을 보내지 않으며, 선정된 담당자만 수행 루프를 시작한다.

## 2. 작업과 프로토콜

[tasks.json](tasks.json)은 계산·날짜 추출·숫자 정렬 각 2개다. `id, desc`는 공고용,
`gold, expected`는 평가 전용이다. 입찰은 `participate, confidence, reason`이다.
[contract_net.py](contract_net.py)의 parse_bid, choose, matches를 순서대로 읽는다.

## 3. 1주차 방식의 에이전트

[agent.py](agent.py)의 execute가 LLM → 도구 실행 → 관측을 반복한다.
최종 JSON 답변이면 종료하며 최대 호출은 6회다. 각 도구는 모델 없이 먼저 실행해 볼 수 있다.

```bash
cd submissions/21567/week-03
python3 -c 'from agent import calculate; print(calculate("17*23"))'
python3 -m unittest discover -p test_lab.py -v
```

## 4. Contract Net 연결

[contract_net.py](contract_net.py)의 run이 공고·입찰·선정·수행·평가를 연결한다.
[run.py](run.py)는 API 호출과 원본 로그, CSV 저장을 담당한다.
API 키는 환경 변수만 사용한다. OPENAI_BASE_URL은 해당 키의 제공자 주소,
AGENT_MODEL은 그 제공자가 지원하는 모델이어야 한다. 키를 코드나 로그에 넣지 않는다.

```bash
python3 run.py --smoke --limit 1 --model "$AGENT_MODEL"
```

작업 하나의 로그에서 announcement 3개 → bid 3개 → award 1개 → tool → answer → evaluation을 확인한다.
도구 사용 여부는 로그에서 확인하며, 단순 정답 출력만으로 도구 호출이 있었다고 간주하지 않는다.
실제 모델은 도구 사용 지시를 따르지 않을 수 있다.

## 5. 과제: 조건 비교

연결 검증이 성공한 후 동일 모델로 아래를 실행한다.

```bash
for condition in baseline homogeneous overconfident; do
  for attempt in 1 2 3; do
    python3 run.py --condition "$condition" --model "$AGENT_MODEL"
  done
done
```

results.csv는 원 과제의 배정 지표, execution.csv는 수행 지표다.
원본 실험 로그는 logs/, 연결 확인과 자동 테스트 기록은 smoke/에 분리한다.
REPORT.md에는 실제 결과가 생긴 뒤 표와 로그 근거를 추가한다.

## 현재 검증 상태

- 자동 테스트 12개 통과: 도구, 입찰 검증, 동점, 불참, 잘못된 응답, 실제 수행 루프의 관측 연결,
  최대 반복, 도구 오류 회복, 조건 통제, 배정·수행의 독립 평가, CSV 누적 보존, 인증 실패 기록.
- 테스트의 LLM 응답은 Scripted 대역이다. 실제 LLM의 행동 또는 조건별 성능을 입증하지 않는다.
- 실제 연결 시도: 현재 환경의 서버가 HTTP 401을 반환했다. smoke/에 실패 원본을 보존했다.
- 실제 9회 실험과 수행 검증은 미완료다. 결과를 만들어 채우지 않았다.
- 기존 구조 검사는 results.csv, logs/ 9개, REPORT.md가 아직 없어 실패한다.
  이는 제출 미완료를 정확히 나타낸다. 강의 원본과 검사기는 변경하지 않았다.

## 다음 확인

제공자 인증 설정이 복구되면 단일 작업 연결을 먼저 재실행한다. tool 관측과 정답을 확인한 후
세 조건 9회 실험을 실행한다. 결과·메시지 수를 원본 로그와 대조하고 보고서를 작성한 뒤
`python3 ../../../scripts/check_week03.py .`를 실행한다.
