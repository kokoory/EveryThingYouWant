# 파일 업로드 가이드

GitHub 저장소에 파일을 올리는 방법은 크게 3가지가 있습니다.

---

## 1. GitHub 웹사이트에서 직접 올리기 (가장 쉬운 방법)

1. GitHub에서 저장소 페이지로 이동합니다.
2. **Add file** > **Upload files** 버튼을 클릭합니다.
3. 파일을 드래그 앤 드롭하거나, **choose your files**를 클릭하여 파일을 선택합니다.
4. 커밋 메시지를 작성하고 **Commit changes**를 클릭합니다.

> 참고: 웹에서는 한 번에 최대 100개 파일, 개별 파일 크기 25MB까지 업로드 가능합니다.

---

## 2. Git 명령어로 올리기

터미널(명령 프롬프트)에서 Git을 사용하는 방법입니다.

### 처음 저장소를 받는 경우

```bash
git clone https://github.com/kokoory/EveryThingYouWant.git
cd EveryThingYouWant
```

### 파일 추가 및 업로드

```bash
# 1. 올리고 싶은 파일을 저장소 폴더에 넣습니다.

# 2. 변경 사항을 스테이징합니다.
git add 파일이름.txt          # 특정 파일만
git add .                     # 모든 변경 파일

# 3. 커밋합니다.
git commit -m "파일 추가: 파일이름.txt"

# 4. GitHub에 올립니다.
git push origin main
```

---

## 3. GitHub Desktop 앱 사용하기

Git 명령어가 어렵다면 [GitHub Desktop](https://desktop.github.com/)을 사용할 수 있습니다.

1. GitHub Desktop을 설치합니다.
2. 저장소를 클론합니다.
3. 파일 탐색기에서 저장소 폴더에 파일을 넣습니다.
4. GitHub Desktop에 변경 사항이 자동으로 표시됩니다.
5. 커밋 메시지를 입력하고 **Commit to main**을 클릭합니다.
6. **Push origin** 버튼을 클릭하여 업로드합니다.

---

## 주의 사항

| 항목 | 제한 |
|------|------|
| 개별 파일 크기 (웹) | 25MB |
| 개별 파일 크기 (Git 명령어) | 100MB |
| 대용량 파일 | [Git LFS](https://git-lfs.github.com/) 사용 필요 |
| 민감한 정보 | `.env`, 비밀번호, API 키 등은 절대 올리지 마세요 |

> 대용량 파일(100MB 초과)은 Git LFS를 사용해야 합니다.
