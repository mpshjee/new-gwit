# new-gwit

![blank](https://user-images.githubusercontent.com/58924412/147617149-62e9888f-14bc-4b34-bc95-bf288f3e60b3.png)

## 소개

* 기존 gwkit의 검색이 마음에 들지 않아, 가볍게 python으로 TUI를 만들었습니다.
* 범용적인 실행을 위해 python 2.7로 작성하였습니다.

## 키 바인딩

### 일반 모드

| 키 | 동작 |
|---|---|
| 화살표 위/아래 | 서버 목록 커서 이동 |
| PageUp / PageDown | 서버 목록 20칸씩 이동 |
| Enter | 커서 위 서버에 SSH(또는 rlogin) 접속 |
| `/` | 접속 사용자 변경 |
| `,` 또는 `\` | 접속 방식 전환 (rlogin ↔ SSH) |
| 영문 입력 | 키워드 필터 (스페이스로 AND 조건, 대소문자 무관, host·tag·description 검색) |
| Ctrl+R | 키워드 초기화 |
| Ctrl+N | 서버 추가 |
| Ctrl+E | 커서 위 서버 정보 수정 |
| Ctrl+D | 커서 위 서버 삭제 |
| Ctrl+L | 커서 위 서버에서 원격 명령 실행 (출력 팝업 표시) |
| `:` | 명령어 모드 진입 |
| Ctrl+C | 종료 |

### 명령어 모드 (`:` 입력 후)

| 명령 | 동작 |
|---|---|
| `:all` | 전체 서버 표시 (그룹 필터 해제) |
| `:group` | 그룹 선택 팝업 열기 |
| `:group <이름>` | 해당 그룹으로 바로 전환 |
| `:quit` 또는 `:q` | 종료 |

### 그룹 활성 상태에서

그룹을 선택하면 서버 목록이 그룹 멤버로 필터링되며, Ctrl+N / Ctrl+D 동작이 변경됩니다.

| 키 | 동작 |
|---|---|
| Ctrl+N | 현재 그룹에 서버 추가 (멀티 선택 팝업) |
| Ctrl+D | 현재 그룹에서 서버 제거 (멀티 선택 팝업) |

### 그룹 선택 팝업 안에서

| 키 | 동작 |
|---|---|
| 화살표 위/아래 | 그룹 목록 이동 |
| Enter | 그룹 선택 |
| Ctrl+N | 새 그룹 생성 |
| Ctrl+D | 그룹 삭제 |
| ESC / Ctrl+C | 팝업 닫기 |

## 기능 상세

### 서버 목록 관리

* `server_list.json` 파일에 서버 정보를 저장합니다. 직접 편집도 가능합니다.
  ```json
  [
      {
          "host": "example.com",
          "description": "Example server",
          "tags": ["web", "prod"]
      }
  ]
  ```
* 필터링된 키워드는 목록에서 빨간색으로 강조됩니다.

### 그룹

* 서버를 그룹으로 묶어 필터링 뷰를 만들 수 있습니다.
* `:group` 으로 팝업을 열고, Ctrl+N으로 그룹 생성 후 서버를 추가합니다.
* 그룹 정보는 별도 파일에 저장됩니다.

### 원격 명령 실행 팝업 (Ctrl+L)

* 서버에 SSH 전체 세션을 열지 않고, 단일 명령의 출력을 팝업 창 안에서 실시간으로 볼 수 있습니다.
* `tail -F /path/to/log` 처럼 스트리밍 출력도 지원합니다.
* 팝업 안 키:
  * `q` 또는 ESC: 종료 (원격 프로세스 자동 정리)
* 주의: SSH 키 기반 인증이 필요합니다. `top`, `vim` 등 TTY 기반 대화형 앱은 지원하지 않습니다.

### Tips 서버 목록 연동

* `python gwkit.py init` 으로 실행하면 Tips SSO 로그인 후 서버 목록을 자동 가져옵니다.
  * 호스트명 → Host, 서버그룹명 → Description, 태그 → Tags 로 매핑됩니다.
* 한글이 포함된 경우 인코딩 이슈가 발생할 수 있습니다. Tips에서 영문으로 변경 후 재실행하세요.

### kinit 자동 실행

* `~/.kinit_passwd` 파일이 있으면 시작 시 자동으로 `kinit` 을 실행합니다.

## 설치 및 실행

```bash
python gwkit.py         # 일반 실행
python gwkit.py init    # Tips 서버 목록 초기화
```

## 라이센스

* 그런거 없습니다. 마음대로 가져다가 수정해서 쓰세요.

copyright @handraker https://github.com/handraker/new-gwit

기능 추가 @viewrain, @지승훈
