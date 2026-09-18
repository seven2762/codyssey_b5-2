# Mini Git

커밋을 DAG(방향성 비순환 그래프)로 관리하는 메모리 기반 CLI 프로그램입니다. 브랜치, 커밋, 로그, 최단 경로, 조상 탐색, 역색인 검색, 직접 구현한 정렬을 지원합니다. 프로그램을 종료하면 데이터는 사라집니다.

## 실행 환경과 방법

- Python 3.10 이상
- 외부 라이브러리 없음

```bash
python main.py
```

프롬프트가 나타나면 명령을 입력합니다. 명령어 이름과 옵션 이름은 대소문자를 구분하지 않습니다. 공백을 포함한 인자는 따옴표로 감싸야 합니다.

```text
mini-git> INIT "Alice Kim"
mini-git> COMMIT "Initial commit"
mini-git> BRANCH feature
mini-git> SWITCH feature
mini-git> COMMIT "Add login feature"
mini-git> LOG
mini-git> SEARCH login
mini-git> SEARCH --author="Alice Kim"
mini-git> quit
```

## 프로젝트 구조

```text
main.py                 실행 진입점과 공개 API
cli.py                  명령 해석과 REPL 입출력
repository.py           커밋 그래프와 브랜치·검색 관리
file_diff.py            LCS 기반 파일 비교
sorting.py              안정 병합 정렬
models.py               Commit 데이터 모델
errors.py               사용자용 예외 정의
```

## 명령어

| 명령 | 설명 |
|---|---|
| `INIT <user_name>` | 저장소를 초기화하고 `main` 브랜치와 사용자를 설정합니다. 다시 실행하면 현재 메모리 저장소를 초기화합니다. |
| `BRANCH <branch_name>` | 현재 HEAD를 가리키는 새 브랜치를 만듭니다. |
| `SWITCH <branch_name>` | 지정한 브랜치로 HEAD를 옮깁니다. |
| `COMMIT <message>` | 현재 HEAD를 부모로 하는 커밋을 만듭니다. 첫 커밋은 부모가 없습니다. |
| `LOG` | 모든 부모가 자식보다 먼저 나오도록 커밋을 출력합니다. |
| `LOG --sort-by=date` | 작성 시각 오름차순으로 출력합니다. |
| `LOG --sort-by=author` | 작성자 이름 오름차순으로 출력합니다. |
| `PATH <commit1> <commit2>` | 부모 연결을 무방향으로 보고 최단 경로를 출력합니다. |
| `ANCESTORS <commit_hash>` | 지정 커밋의 모든 조상을 부모 우선 순서로 출력합니다. |
| `SEARCH <keyword>` | 메시지 키워드 역색인으로 검색합니다. 여러 단어는 모든 단어를 포함한 커밋을 찾습니다. |
| `SEARCH --author=<name>` | 작성자 역색인으로 검색합니다. |
| `exit`, `quit` | 프로그램을 종료합니다. |

보너스로 `MERGE <branch_name>`과 `DIFF <file1> <file2>`도 제공합니다. `MERGE`는 현재 HEAD와 대상 브랜치 HEAD를 부모로 갖는 2-parent 커밋을 만들며, `DIFF`는 LCS를 이용해 공통 줄(`  `), 삭제 줄(`- `), 추가 줄(`+ `)을 표시합니다.

## 실행 예시

아래 출력은 한 세션에서 명령을 순서대로 실제 실행한 결과입니다. 해시와 작성 시각은 실행할 때마다 달라집니다. 예시에서 만드는 커밋 그래프는 다음과 같습니다.

```text
Initial commit ── Add README ── Fix typo in README        (main)
                       \
                        Add login feature ── Add login tests   (feature)
```

### INIT, COMMIT, BRANCH, SWITCH

```text
mini-git> INIT "Alice Kim"
Initialized repository.
Current branch: main
Current user: Alice Kim
mini-git> COMMIT "Initial commit"
[main e80c88d3a5] Initial commit
mini-git> COMMIT "Add README"
[main d56710deb3] Add README
mini-git> BRANCH feature
Created branch: feature
mini-git> COMMIT "Fix typo in README"
[main cc8ac15210] Fix typo in README
mini-git> SWITCH feature
Switched to branch: feature
mini-git> COMMIT "Add login feature"
[feature 23cece7454] Add login feature
mini-git> COMMIT "Add login tests"
[feature b7eafa1c53] Add login tests
```

`BRANCH`는 현재 HEAD(`Add README`)를 가리키는 브랜치를 만들기 때문에, 이후 `main`과 `feature`의 커밋은 `Add README`에서 갈라집니다.

### LOG

기본 `LOG`는 위상 정렬 순서라서 부모가 항상 자식보다 먼저 나옵니다. 각 브랜치의 HEAD 커밋에는 `[브랜치명]`이 붙습니다.

```text
mini-git> LOG
commit e80c88d3a5 (Alice Kim, 2026-09-19 00:19:01)
Initial commit

commit d56710deb3 (Alice Kim, 2026-09-19 00:19:02)
Add README

commit 23cece7454 (Alice Kim, 2026-09-19 00:19:04)
Add login feature

commit cc8ac15210 (Alice Kim, 2026-09-19 00:19:03) [main]
Fix typo in README

commit b7eafa1c53 (Alice Kim, 2026-09-19 00:19:05) [feature]
Add login tests
```

`--sort-by=date`는 작성 시각 오름차순입니다. 기본 `LOG`와 달리 `Fix typo in README`(00:19:03)가 `Add login feature`(00:19:04)보다 먼저 나옵니다.

```text
mini-git> LOG --sort-by=date
commit e80c88d3a5 (Alice Kim, 2026-09-19 00:19:01)
Initial commit

commit d56710deb3 (Alice Kim, 2026-09-19 00:19:02)
Add README

commit cc8ac15210 (Alice Kim, 2026-09-19 00:19:03) [main]
Fix typo in README

commit 23cece7454 (Alice Kim, 2026-09-19 00:19:04)
Add login feature

commit b7eafa1c53 (Alice Kim, 2026-09-19 00:19:05) [feature]
Add login tests
```

`--sort-by=author`는 작성자 이름 오름차순이고, 작성자가 같으면 작성 시각 순입니다. 이 예시는 작성자가 한 명이라 날짜 정렬과 결과가 같습니다.

```text
mini-git> LOG --sort-by=author
commit e80c88d3a5 (Alice Kim, 2026-09-19 00:19:01)
Initial commit

commit d56710deb3 (Alice Kim, 2026-09-19 00:19:02)
Add README

commit cc8ac15210 (Alice Kim, 2026-09-19 00:19:03) [main]
Fix typo in README

commit 23cece7454 (Alice Kim, 2026-09-19 00:19:04)
Add login feature

commit b7eafa1c53 (Alice Kim, 2026-09-19 00:19:05) [feature]
Add login tests
```

### PATH

`Fix typo in README`(main)와 `Add login tests`(feature)는 서로 조상 관계가 아니지만, `PATH`는 연결을 무방향으로 보기 때문에 공통 부모 `Add README`를 거쳐 가는 경로를 찾습니다. 같은 커밋을 두 번 주면 그 커밋 하나만 출력합니다.

```text
mini-git> PATH cc8ac15210 b7eafa1c53
Path: cc8ac15210 -> d56710deb3 -> 23cece7454 -> b7eafa1c53
mini-git> PATH e80c88d3a5 e80c88d3a5
Path: e80c88d3a5
```

두 커밋이 이어져 있지 않으면 `No path`를 출력합니다.

### ANCESTORS

지정한 커밋 자신은 빼고, 부모 방향으로 닿는 모든 커밋을 부모 우선 순서로 출력합니다. 다른 브랜치의 `Fix typo in README`는 조상이 아니므로 나오지 않습니다.

```text
mini-git> ANCESTORS b7eafa1c53
commit e80c88d3a5 (Alice Kim, 2026-09-19 00:19:01)
Initial commit

commit d56710deb3 (Alice Kim, 2026-09-19 00:19:02)
Add README

commit 23cece7454 (Alice Kim, 2026-09-19 00:19:04)
Add login feature
mini-git> ANCESTORS e80c88d3a5
No ancestors.
```

### SEARCH

키워드는 대소문자를 구분하지 않습니다. 여러 단어를 따옴표로 묶으면 모든 단어를 포함한 커밋만 찾습니다.

```text
mini-git> SEARCH login
Found 2 commits:

- 23cece7454 (Alice Kim): Add login feature
- b7eafa1c53 (Alice Kim): Add login tests
mini-git> SEARCH "login tests"
Found 1 commit:

- b7eafa1c53 (Alice Kim): Add login tests
mini-git> SEARCH --author="Alice Kim"
Found 5 commits:

- e80c88d3a5 (Alice Kim): Initial commit
- d56710deb3 (Alice Kim): Add README
- cc8ac15210 (Alice Kim): Fix typo in README
- 23cece7454 (Alice Kim): Add login feature
- b7eafa1c53 (Alice Kim): Add login tests
mini-git> SEARCH nothing
Found 0 commits.
```

### MERGE (보너스)

현재 브랜치 HEAD와 대상 브랜치 HEAD를 부모로 갖는 병합 커밋을 만듭니다. 병합 커밋의 조상에는 두 브랜치의 커밋이 모두 포함됩니다.

```text
mini-git> SWITCH main
Switched to branch: main
mini-git> MERGE feature
[main 1650900ccc] Merge branch 'feature'
mini-git> ANCESTORS 1650900ccc
commit e80c88d3a5 (Alice Kim, 2026-09-19 00:19:01)
Initial commit

commit d56710deb3 (Alice Kim, 2026-09-19 00:19:02)
Add README

commit 23cece7454 (Alice Kim, 2026-09-19 00:19:04)
Add login feature

commit cc8ac15210 (Alice Kim, 2026-09-19 00:19:03)
Fix typo in README

commit b7eafa1c53 (Alice Kim, 2026-09-19 00:19:05) [feature]
Add login tests
mini-git> MERGE feature
Already up to date.
```

대상 브랜치의 HEAD가 이미 현재 HEAD의 조상이면(이미 병합했으면) 새 커밋을 만들지 않고 `Already up to date.`를 출력합니다.

### DIFF (보너스)

`old.txt`와 `new.txt`가 다음과 같을 때의 결과입니다.

```text
old.txt          new.txt
apple            apple
banana           blueberry
cherry           cherry
                 date
```

```text
mini-git> DIFF old.txt new.txt
  apple
- banana
+ blueberry
  cherry
+ date
```

### 에러

에러가 나도 REPL은 종료되지 않고 다음 명령을 기다립니다.

```text
mini-git> LOG
Repository not initialized
mini-git> COMMIT
Invalid args
mini-git> COMMIT "unclosed
Invalid args
mini-git> LOG --sort-by=size
Invalid args
mini-git> SWITCH dev
Unknown branch: dev
mini-git> BRANCH feature
Branch already exists: feature
mini-git> PATH abc123 e80c88d3a5
Unknown commit: abc123
mini-git> PUSH
Unknown command: PUSH
```

`Repository not initialized`는 `INIT` 전에 다른 명령을 실행했을 때 나옵니다. 인자 개수가 맞지 않거나, 따옴표가 닫히지 않았거나, 지원하지 않는 옵션 값을 주면 `Invalid args`가 나옵니다.

### 종료

```text
mini-git> quit
Goodbye.
```

`Ctrl+D`나 `Ctrl+C`로도 종료할 수 있습니다.

## 핵심 설계

### 커밋 그래프

각 `Commit`은 `hash`, `message`, `author`, `timestamp`, `parents`를 가집니다. 저장소는 `dict[hash, Commit]` 형태라 해시로 평균 O(1)에 커밋을 찾습니다. 새 커밋은 이미 존재하는 HEAD만 부모로 삼으므로 미래 커밋을 가리키는 간선이 생기지 않아 사이클이 만들어지지 않습니다. merge도 이미 존재하는 두 HEAD만 부모로 사용하므로 같은 성질을 유지합니다.

커밋 해시는 세션 UUID, 증가 카운터, 작성자, 작성 시각, 메시지, 부모 해시를 조합해 SHA-1으로 만들며, 생성된 10자리 해시가 이미 존재하면 카운터를 증가시켜 다시 생성합니다. 따라서 세션 안에서 중복된 해시는 저장되지 않습니다.

일반 Git과 같이 간선 방향을 `자식 -> 부모`로 보면 커밋 그래프는 방향성이 있고 순환이 없는 DAG입니다. 부모의 자식 목록도 별도로 유지하여 반대 방향 탐색이 필요한 경우 매번 전체 커밋을 훑지 않습니다.

### 부모 우선 LOG

기본 `LOG`는 Kahn 방식의 위상 정렬을 사용합니다. 각 커밋의 진입 차수를 부모 수로 두고, 부모가 모두 출력되어 진입 차수가 0이 된 커밋을 큐에 넣습니다. 따라서 부모가 항상 자식보다 먼저 출력됩니다. 시간복잡도는 커밋 수를 V, 부모 연결 수를 E라 할 때 O(V + E)이며, 같은 시점에 처리 가능한 노드의 결정적 순서를 위한 직접 구현 병합 정렬 비용이 더해질 수 있습니다.

`LOG --sort-by=...`는 학습용 비교 정렬 명령이므로 지정한 필드가 기본 위상 순서보다 우선합니다. 날짜 정렬은 일반적인 커밋 생성 과정에서는 부모가 자식보다 먼저지만, 작성자 정렬은 위상 순서를 보장하지 않습니다.

### 직접 구현한 안정 병합 정렬

날짜와 작성자 정렬에는 `merge_sort`를 사용하며 `sorted()`와 `list.sort()`를 사용하지 않습니다. 리스트를 절반씩 나눈 뒤 정렬된 두 부분을 합칩니다.

- 평균 시간복잡도: O(n log n)
- 최악 시간복잡도: O(n log n)
- 추가 공간복잡도: O(n)
- 안정 정렬: 예. 키가 같으면 왼쪽 원소를 먼저 선택합니다.

### PATH와 ANCESTORS

`PATH`는 부모와 자식 연결을 모두 이웃으로 간주하고 BFS를 수행합니다. 시작점과 도착점 양쪽의 거리를 구한 다음, 최단 거리 조건을 유지하는 이웃 중 해시가 가장 작은 것을 매 단계 고릅니다. 따라서 여러 최단 경로 중 `hash1->hash2->...` 문자열이 사전순으로 가장 작은 경로를 선택합니다. 시간복잡도는 O(V + E)입니다.

예를 들어 커밋 그래프가 다음과 같다고 하겠습니다.

```text
A ── B ── C   (main)
      \
       D ── E   (feature)
```

C와 E는 서로 조상 관계가 아니므로 부모 방향으로만 따라가면 만날 수 없습니다. `PATH`는 연결을 무방향으로 보기 때문에 C에서 부모 B로 올라간 뒤 자식 D, E로 내려가는 경로를 찾습니다.

전체 실행 결과는 [실행 예시의 PATH](#path)를 참고하세요.

`ANCESTORS`는 지정 커밋의 부모 방향으로 방문 집합을 유지하며 탐색하므로 merge로 같은 조상에 여러 번 닿아도 한 번만 처리합니다. 수집한 조상은 전체 위상 순서를 기준으로 출력하여 조상 집합 안에서도 부모가 자식보다 먼저 나옵니다.

### 역색인 검색

커밋을 만들 때 메시지를 공백으로 나누고 소문자로 바꾼 토큰을 `keyword -> commit hash 집합`에 기록합니다. 작성자도 `author -> commit hash 집합`에 기록합니다. 검색 시 모든 V개 커밋의 메시지를 검사하지 않고 해당 키의 posting 집합을 즉시 조회합니다.

- 단일 키워드 후보 조회: 평균 O(1) + 결과 수에 비례
- 여러 키워드: posting 집합의 교집합 비용 + 결과 수에 비례
- 전체 순회 검색: 매 요청마다 O(V), 메시지 비교 비용까지 필요

검색 결과의 일관된 출력 순서를 만들기 위한 병합 정렬 비용은 별도입니다. 토큰 기준은 공백 분리와 소문자화이므로 구두점은 토큰의 일부로 취급됩니다. 작성자 값은 입력한 대소문자를 그대로 구분합니다.
