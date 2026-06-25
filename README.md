# 바이럴 운영 대시보드 MVP

공개 Google Sheets의 원본 DB 시트만 읽어서 Python에서 KPI와 성과를 다시 계산하는 Streamlit 대시보드입니다.

## 핵심 원칙

- 엑셀 수식은 사용하지 않습니다.
- Google Sheets는 원본 입력 DB로만 사용합니다.
- 계산과 집계는 모두 Python에서 처리합니다.
- 로딩 함수는 `data_loader.py`에 분리되어 있습니다.

## 포함 파일

- `app.py`: Streamlit UI, 필터, KPI, 차트, 표
- `data_loader.py`: 공개 Google Sheets CSV 로딩, 표준화, 매칭, 집계용 전처리
- `requirements.txt`: 실행 의존성

## 데이터 처리 방식

1. 공개 Google Sheets의 각 플랫폼 DB 탭을 CSV로 읽습니다.
2. 플랫폼별 유상작업 데이터를 표준 스키마로 통합합니다.
3. `(DB)바이럴 효율` 시트를 NT 성과 원본으로 읽습니다.
4. `(DB)바이럴 효율`은 누적 입력형 데이터를 전제로 처리합니다.
5. 같은 `nt_source + nt_detail + nt_keyword` 키가 여러 번 들어오면 최신 수집일 데이터만 사용합니다.
6. 같은 최신 수집일 내 중복이 있으면 숫자 지표는 가장 큰 값을 최종값으로 사용합니다.
7. 이후 같은 키 기준으로 PC/모바일 성과를 합산합니다.
8. 유상작업 DB의 플랫폼 정보로 `nt_source`를 추론하고 성과 DB와 매칭합니다.
9. 매칭 실패 건은 별도 리스트로 표시합니다.

## KPI 기준

- `매칭 기준 KPI`: 유상작업 DB와 실제 매칭된 성과만 합산
- `원본 효율 DB 전체 합계`: `(DB)바이럴 효율` 시트 전체 합계
- 두 값은 기준이 다르므로 서로 다를 수 있습니다.

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

또는 Windows에서 [run_dashboard.bat](D:\1.마케팅\바이럴 대시보드\run_dashboard.bat)을 더블클릭하면 대시보드가 바로 실행됩니다. Streamlit이 없을 때만 한 번 설치합니다.

같은 네트워크의 다른 사람도 보게 하려면 [share_dashboard.bat](D:\1.마케팅\바이럴 대시보드\share_dashboard.bat)을 실행하세요. 실행 후 표시되는 IPv4 주소로 `http://내IP:8501` 형태로 접속하면 됩니다.

## 현재 데이터 소스

- Spreadsheet ID: `1NeeQNSiG9D9u5U290vyW_LKIn9Siyd9EinwZaUXzIiM`
- 공개 CSV URL은 `build_csv_url(spreadsheet_id, gid)`로 생성합니다.
- 기본 캐시 갱신 주기는 5분입니다.

## 다른 사람에게 공유하기

### 1. 가장 빠른 방법: 같은 네트워크에서 공유

1. [share_dashboard.bat](D:\1.마케팅\바이럴 대시보드\share_dashboard.bat) 실행
2. 실행 창에 보이는 IPv4 주소 확인
3. 다른 PC에서 `http://IPv4주소:8501` 접속

예: `http://192.168.0.15:8501`

### 2. 서버 배포

이 프로젝트에는 서버 배포용 파일도 포함되어 있습니다.

- [.streamlit/config.toml](D:\1.마케팅\바이럴 대시보드\.streamlit\config.toml)
- [Dockerfile](D:\1.마케팅\바이럴 대시보드\Dockerfile)
- [runtime.txt](D:\1.마케팅\바이럴 대시보드\runtime.txt)

배포 가능한 예:

- 사내 Linux 서버
- AWS EC2
- GCP VM / Cloud Run
- Azure VM
- Render / Railway 같은 컨테이너 배포 환경

## 현재 매칭 규칙

- 블로그: `naverblog`, 보조 후보로 `naver`
- 인스타그램: `instagram`
- 유튜브: `youtube`
- X: `x`
- 커뮤니티: 시트의 `플랫폼` 값을 `nt_source`로 사용
- 브랜드커넥트: `nshoplive`

## 추후 API 방식 전환

`data_loader.py`의 `load_google_public_sheets_data()`만 Google Sheets API 방식으로 바꾸면, `app.py`와 나머지 계산 로직은 그대로 재사용할 수 있습니다.
