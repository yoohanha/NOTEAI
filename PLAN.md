# NOTEAI 대시보드 기획 문서

**프로젝트명**: NOTEAI 대시보드  
**버전**: 1.0  
**작성일**: 2026-08-26  
**작성자**: Planner (기획자)  
**상태**: 기획 완료 ✅

---

## 📋 Executive Summary

NOTEAI 대시보드는 팀 프로젝트의 진행 상황을 **시각적이고 직관적**으로 보여주는 모던 웹 대시보드입니다. 세 가지 핵심 역할(Planner 📋, Backend Developer 🔌, Frontend Designer 🎨)의 진행률, 통계, 활동 피드를 한 페이지에서 관리할 수 있습니다.

**핵심 목표:**
- 프로젝트 진행 상황 실시간 모니터링
- 역할별 진행률 시각화
- 팀 활동 추적 및 통계 제공
- 모던하고 반응형인 UX/UI 제공

---

## 1. 페이지 개요

### 1.1 페이지 정보
- **페이지명**: NOTEAI 대시보드
- **URL**: `/dashboard` 또는 `/index.html`
- **대상 사용자**: 프로젝트 팀원
- **디바이스**: 데스크톱, 태블릿, 모바일 (반응형)
- **기술 스택**:
  - HTML5
  - Tailwind CSS (CDN)
  - Vanilla JavaScript (ES6+)
  - 외부 라이브러리: 없음 (경량화)

### 1.2 페이지 목표 및 KPI
| 목표 | 측정 지표 |
|------|---------|
| 프로젝트 진행 상황 파악 | 진행률 시각화 정확성 |
| 팀 협업 촉진 | 활동 피드 업데이트 빈도 |
| 사용자 경험 향상 | 페이지 로드 시간 < 2초 |
| 모바일 대응 | 모든 기기에서 97% 이상 가독성 |

---

## 2. 주요 섹션 상세 설계

### 2.1 헤더 (네비게이션)
**목적**: 사용자 정보 표시 및 메뉴 네비게이션  
**위치**: 페이지 최상단 (고정 또는 스티키)  
**높이**: 64px  

**요소:**
- 🎯 로고 + 브랜드명 (좌측)
- 📱 네비게이션 메뉴:
  - 대시보드 (현재)
  - 파일 관리
  - 게시판
  - 설정
- 👤 사용자 프로필 (우측):
  - 사용자 아바타 (32x32px)
  - 사용자명 (표시/숨김 옵션)
  - 알림 벨 아이콘
  - 로그아웃 버튼

**스타일:**
- 배경: 흰색 (`bg-white`)
- 그림자: 미묘한 드롭 섀도우 (`shadow-sm`)
- 텍스트: 진회색 (`text-gray-900`)

---

### 2.2 웰컴 섹션
**목적**: 사용자 환영 및 프로젝트 소개  
**위치**: 헤더 아래  
**높이**: 자동 (콘텐츠에 따라)  

**요소:**
- 🚀 제목: "NOTEAI 대시보드에 오신 것을 환영합니다! 🚀"
- 📝 부제목: "현재 프로젝트의 진행 상황을 확인하세요"
- ⏰ 마지막 업데이트: "마지막 업데이트: 2시간 전"

**스타일:**
- 배경: 그라데이션 (`bg-gradient-to-r from-blue-500 to-purple-600`)
- 텍스트: 흰색 (`text-white`)
- 패딩: `py-12 px-8`
- 모서리 반경: `rounded-lg`

---

### 2.3 역할 카드 섹션
**목적**: 각 역할의 진행 상황 시각화  
**위치**: 웰컴 섹션 아래  
**카드 수**: 3개  
**레이아웃**: 반응형 그리드 (데스크톱: 3열, 태블릿: 2열, 모바일: 1열)  

#### 2.3.1 Planner 카드 📋

```
┌─────────────────────────────┐
│  📋 Planner (기획자)        │
├─────────────────────────────┤
│  설명: 프로젝트 기획 및     │
│       구조 설계             │
│                             │
│  진행률: ████████████ 100%  │
│                             │
│  [상세 보기] 버튼           │
└─────────────────────────────┘
```

- **이모티콘**: 📋 (Clipboard)
- **제목**: Planner (기획자)
- **설명**: 프로젝트 기획 및 구조 설계
- **진행률**: 100%
- **진행률 바 색상**: 파란색 (`bg-blue-500`)
- **버튼**: "상세 보기" (파란색)

#### 2.3.2 Backend Developer 카드 🔌

```
┌─────────────────────────────┐
│  🔌 Backend Developer       │
├─────────────────────────────┤
│  설명: FastAPI 백엔드 및   │
│       DB 구현              │
│                             │
│  진행률: ██████████░░ 70%   │
│                             │
│  [상세 보기] 버튼           │
└─────────────────────────────┘
```

- **이모티콘**: 🔌 (Plug)
- **제목**: Backend Developer (백엔드 개발자)
- **설명**: FastAPI 백엔드 및 DB 구현
- **진행률**: 70%
- **진행률 바 색상**: 보라색 (`bg-purple-500`)
- **버튼**: "상세 보기" (보라색)

#### 2.3.3 Frontend Designer 카드 🎨

```
┌─────────────────────────────┐
│  🎨 Frontend Designer       │
├─────────────────────────────┤
│  설명: Tailwind CSS UI      │
│       구현                  │
│                             │
│  진행률: █████░░░░░░ 50%    │
│                             │
│  [상세 보기] 버튼           │
└─────────────────────────────┘
```

- **이모티콘**: 🎨 (Artist Palette)
- **제목**: Frontend Designer (프론트엔드 설계자)
- **설명**: Tailwind CSS UI 구현
- **진행률**: 50%
- **진행률 바 색상**: 분홍색 (`bg-pink-500`)
- **버튼**: "상세 보기" (분홍색)

**카드 공통 스타일:**
- 배경: 흰색 (`bg-white`)
- 그림자: 중간 정도 (`shadow-md`)
- 호버 효과: 그림자 강조 + 상단 이동 (`hover:shadow-lg hover:-translate-y-1`)
- 전환 효과: 부드러운 300ms (`transition duration-300`)
- 패딩: `p-6`
- 모서리 반경: `rounded-lg`

---

### 2.4 통계 섹션
**목적**: 주요 프로젝트 지표 표시  
**위치**: 역할 카드 아래  
**카드 수**: 4개  
**레이아웃**: 반응형 그리드 (데스크톱: 4열, 태블릿: 2열, 모바일: 1열)  

#### 통계 카드 구조

```
┌──────────────────────────┐
│  📁 전체 파일 수         │
│  1,234 개                │
│  +15% 이전 달 대비       │
└──────────────────────────┘
```

**통계 항목:**

| 이모티콘 | 레이블 | 수치 | 변화율 |
|---------|--------|------|--------|
| 📁 | 전체 파일 수 | 1,234개 | +15% |
| 📝 | 작성한 노트 | 45개 | +8% |
| 👥 | 팀 멤버 | 8명 | 동일 |
| ⏱️ | 총 소요 시간 | 120시간 | +25% |

**카드 스타일:**
- 배경: 흰색 또는 연한 배경색
- 아이콘: 큰 사이즈 (48x48px)
- 텍스트: 제목은 `text-2xl`, 레이블은 `text-sm text-gray-600`
- 변화율: 증가(초록색), 감소(빨간색), 동일(회색)

---

### 2.5 활동 피드
**목적**: 팀 활동 실시간 추적  
**위치**: 통계 섹션 아래  
**항목 수**: 6-8개  
**레이아웃**: 수직 타임라인  

#### 활동 항목 구조

```
┌─────────────────────────────────────┐
│ ✅ 2시간 전                         │
│ Alice | Planner 단계 완료            │
│ "프로젝트 기획이 완료되었습니다."   │
└─────────────────────────────────────┘
```

**활동 데이터:**
1. ✅ 2시간 전 | Alice | Planner 단계 완료 | "프로젝트 기획이 완료되었습니다."
2. 📝 5시간 전 | Bob | 노트 작성 | "백엔드 API 설계 문서 작성"
3. 🔧 1일 전 | Carol | 버그 수정 | "로그인 오류 수정"
4. 🚀 2일 전 | David | 배포 완료 | "v1.0 프로덕션 배포"
5. 📊 3일 전 | Eve | 통계 업데이트 | "월간 리포트 생성"
6. 🎉 1주 전 | Frank | 프로젝트 시작 | "NOTEAI 프로젝트 시작!"

**활동 아이콘 매핑:**
- ✅ 완료 (초록색)
- 📝 작성 (파란색)
- 🔧 수정 (주황색)
- 🚀 배포 (보라색)
- 📊 통계 (회색)
- 🎉 이벤트 (노란색)

**피드 스타일:**
- 레이아웃: 좌측 아이콘 + 시간, 우측 내용
- 분리선: 카드 간 연한 경계선
- 호버 효과: 배경색 변화 (`hover:bg-gray-50`)

---

### 2.6 빠른 링크 섹션
**목적**: 자주 사용하는 기능 빠른 접근  
**위치**: 활동 피드 아래  
**버튼 수**: 4개  
**레이아웃**: 수평 버튼 그룹 (반응형 줄 바꿈)  

**빠른 링크 버튼:**
1. ✨ 새 노트 작성
2. 📤 파일 업로드
3. 👥 팀 초대
4. ⚙️ 설정

**버튼 스타일:**
- 배경: 파란색 (`bg-blue-500`)
- 텍스트: 흰색 (`text-white`)
- 호버: 진한 파란색 (`hover:bg-blue-600`)
- 패딩: `px-6 py-3`
- 모서리: `rounded-lg`
- 전환: 300ms (`transition duration-300`)

---

### 2.7 푸터
**목적**: 저작권 정보 및 링크 제공  
**위치**: 페이지 최하단  
**높이**: 100px  

**요소:**
- 저작권: "© 2026 NOTEAI. All rights reserved."
- 링크:
  - 문의하기
  - 개인정보처리방침
  - 이용약관
  - 블로그
- 소셜 미디어: GitHub, Twitter, LinkedIn 아이콘

**푸터 스타일:**
- 배경: 진회색 (`bg-gray-900`)
- 텍스트: 흰색 (`text-white`)
- 텍스트 크기: 작음 (`text-sm`)

---

## 3. 색상 팔레트 및 스타일 정의

### 3.1 Primary Color Scheme

**주요 색상:**

```css
/* Tailwind CSS Color Palette */

/* Blues (Planner / Primary) */
--blue-50:    #EFF6FF
--blue-100:   #DBEAFE
--blue-500:   #3B82F6  /* Primary Blue */
--blue-600:   #2563EB
--blue-700:   #1D4ED8

/* Purples (Backend) */
--purple-50:  #F5F3FF
--purple-100: #EDE9FE
--purple-500: #8B5CF6  /* Backend Purple */
--purple-600: #7C3AED

/* Pinks (Frontend) */
--pink-50:    #FDF2F8
--pink-100:   #FCE7F3
--pink-500:   #EC4899  /* Frontend Pink */
--pink-600:   #DB2777

/* Grays (Neutral) */
--gray-50:    #F9FAFB  /* Light Background */
--gray-100:   #F3F4F6
--gray-200:   #E5E7EB  /* Borders */
--gray-600:   #4B5563  /* Secondary Text */
--gray-900:   #111827  /* Primary Text */

/* Status Colors */
--green-500:  #10B981  /* Success */
--orange-500: #F59E0B  /* Warning */
--red-500:    #EF4444  /* Error */
```

### 3.2 색상 사용 가이드

| 요소 | 색상 | Tailwind 클래스 | 사용처 |
|------|------|-----------------|--------|
| Planner 카드 진행률 | 파란색 | `bg-blue-500` | Planner 섹션 |
| Backend 카드 진행률 | 보라색 | `bg-purple-500` | Backend 섹션 |
| Frontend 카드 진행률 | 분홍색 | `bg-pink-500` | Frontend 섹션 |
| 성공 상태 | 초록색 | `bg-green-500` | 체크마크, 완료 |
| 진행 중 | 주황색 | `bg-orange-500` | 프로그레스 바 |
| 오류/경고 | 빨간색 | `bg-red-500` | 오류 메시지 |
| 배경 | 연한 회색 | `bg-gray-50` | 페이지 배경 |
| 카드 배경 | 흰색 | `bg-white` | 카드 배경 |
| 텍스트 (주요) | 진회색 | `text-gray-900` | 제목, 주 텍스트 |
| 텍스트 (보조) | 회색 | `text-gray-600` | 부제목, 설명 |
| 경계선 | 연한 회색 | `border-gray-200` | 구분선 |

### 3.3 그라데이션 정의

**웰컴 섹션 배경:**
```css
background: linear-gradient(to right, #3B82F6, #8B5CF6);
/* Tailwind: bg-gradient-to-r from-blue-500 to-purple-600 */
```

**진행률 바 (고급):**
```css
background: linear-gradient(to right, #3B82F6 0%, #1D4ED8 100%);
/* Tailwind: bg-gradient-to-r from-blue-500 to-blue-700 */
```

---

## 4. Tailwind CSS 클래스 계획

### 4.1 레이아웃 클래스

```html
<!-- 컨테이너 -->
<div class="container mx-auto px-4">
  <!-- 콘텐츠 -->
</div>

<!-- 그리드 레이아웃 -->
<div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
  <!-- 아이템 -->
</div>

<!-- Flexbox -->
<div class="flex items-center justify-between">
  <!-- 항목 -->
</div>
```

### 4.2 카드 컴포넌트

```html
<div class="bg-white rounded-lg shadow-md hover:shadow-lg hover:-translate-y-1 transition duration-300 p-6">
  <h3 class="text-xl font-bold text-gray-900 mb-2">카드 제목</h3>
  <p class="text-sm text-gray-600">카드 설명</p>
</div>
```

### 4.3 진행률 바 컴포넌트

```html
<div class="flex items-center gap-4">
  <div class="flex-1">
    <div class="bg-gray-200 rounded-full h-3 overflow-hidden">
      <div class="bg-gradient-to-r from-blue-500 to-blue-700 h-full" 
           style="width: 75%"></div>
    </div>
  </div>
  <span class="text-lg font-bold text-gray-900">75%</span>
</div>
```

### 4.4 버튼 컴포넌트

```html
<!-- Primary Button -->
<button class="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600 transition duration-300 font-medium">
  작업 수행
</button>

<!-- Secondary Button -->
<button class="border-2 border-blue-500 text-blue-500 px-6 py-2 rounded-lg hover:bg-blue-50 transition duration-300 font-medium">
  보조 작업
</button>
```

### 4.5 텍스트 스타일

```html
<!-- 제목 -->
<h1 class="text-4xl font-bold text-gray-900">페이지 제목</h1>
<h2 class="text-2xl font-bold text-gray-900">섹션 제목</h2>
<h3 class="text-xl font-semibold text-gray-900">소제목</h3>

<!-- 본문 -->
<p class="text-base text-gray-700 leading-relaxed">일반 텍스트</p>
<p class="text-sm text-gray-600">보조 텍스트</p>

<!-- 하이라이트 -->
<span class="text-blue-500 font-semibold">강조 텍스트</span>
```

### 4.6 간격 규칙

```html
<!-- 마진 -->
<div class="mb-6 mt-4 mx-2">콘텐츠</div>

<!-- 패딩 -->
<div class="p-6 px-4 py-8">콘텐츠</div>

<!-- 갭 (그리드/플렉스) -->
<div class="flex gap-4">
  <div>항목 1</div>
  <div>항목 2</div>
</div>
```

---

## 5. HTML 구조 설계

### 5.1 전체 문서 구조

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NOTEAI 대시보드</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
  
  <!-- 헤더 -->
  <header class="bg-white shadow-sm sticky top-0 z-50">
    <!-- 네비게이션 내용 -->
  </header>

  <!-- 메인 콘텐츠 -->
  <main class="container mx-auto px-4 py-8">
    <!-- 웰컴 섹션 -->
    <!-- 역할 카드 섹션 -->
    <!-- 통계 섹션 -->
    <!-- 활동 피드 -->
    <!-- 빠른 링크 -->
  </main>

  <!-- 푸터 -->
  <footer class="bg-gray-900 text-white py-12 mt-16">
    <!-- 푸터 내용 -->
  </footer>

  <script src="script.js"></script>
</body>
</html>
```

### 5.2 섹션별 상세 구조

**헤더:**
```html
<header class="bg-white shadow-sm sticky top-0 z-50">
  <div class="container mx-auto px-4 py-4">
    <div class="flex items-center justify-between">
      <!-- 로고 -->
      <div class="flex items-center gap-2">
        <div class="text-2xl font-bold text-blue-600">📝 NOTEAI</div>
      </div>
      
      <!-- 네비게이션 -->
      <nav class="hidden md:flex gap-8">
        <a href="#" class="text-gray-700 hover:text-blue-600">대시보드</a>
        <a href="#" class="text-gray-700 hover:text-blue-600">파일 관리</a>
        <a href="#" class="text-gray-700 hover:text-blue-600">게시판</a>
        <a href="#" class="text-gray-700 hover:text-blue-600">설정</a>
      </nav>
      
      <!-- 사용자 프로필 -->
      <div class="flex items-center gap-4">
        <button class="relative text-gray-600 hover:text-gray-900">
          <span>🔔</span>
          <span class="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full"></span>
        </button>
        <img src="avatar.jpg" alt="사용자" class="w-10 h-10 rounded-full">
        <button class="text-gray-700 hover:text-red-600">로그아웃</button>
      </div>
    </div>
  </div>
</header>
```

**웰컴 섹션:**
```html
<section class="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-12 text-white mb-12">
  <h1 class="text-4xl font-bold mb-4">NOTEAI 대시보드에 오신 것을 환영합니다! 🚀</h1>
  <p class="text-lg text-blue-100 mb-2">현재 프로젝트의 진행 상황을 확인하세요</p>
  <p class="text-sm text-blue-100">마지막 업데이트: 2시간 전</p>
</section>
```

---

## 6. 반응형 설계

### 6.1 Breakpoint 전략

**Tailwind CSS Breakpoints:**

| Breakpoint | 화면 크기 | 사용처 | 클래스 접두사 |
|-----------|---------|--------|-------------|
| xs (기본) | < 640px | 모바일 | (없음) |
| sm | ≥ 640px | 작은 태블릿 | `sm:` |
| md | ≥ 768px | 태블릿 | `md:` |
| lg | ≥ 1024px | 데스크톱 | `lg:` |
| xl | ≥ 1280px | 넓은 데스크톱 | `xl:` |

### 6.2 반응형 그리드 예시

```html
<!-- 역할 카드 (1열 → 2열 → 3열) -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  <div class="bg-white rounded-lg p-6">카드 1</div>
  <div class="bg-white rounded-lg p-6">카드 2</div>
  <div class="bg-white rounded-lg p-6">카드 3</div>
</div>

<!-- 통계 카드 (1열 → 2열 → 4열) -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  <div class="bg-white rounded-lg p-6">통계 1</div>
  <!-- ... 추가 통계 ... -->
</div>
```

### 6.3 패딩 및 마진 반응형 조정

```html
<!-- 다양한 화면 크기에 따른 패딩 -->
<main class="px-4 md:px-6 lg:px-8 py-6 md:py-8 lg:py-12">
  콘텐츠
</main>
```

### 6.4 숨김/표시 반응형 제어

```html
<!-- 모바일에서 숨김, 데스크톱에서 표시 -->
<nav class="hidden md:flex gap-8">메뉴</nav>

<!-- 모바일에서 표시, 데스크톱에서 숨김 -->
<button class="md:hidden">메뉴 (모바일)</button>
```

---

## 7. 이모티콘 가이드

### 7.1 역할별 이모티콘

| 역할 | 이모티콘 | 유니코드 | 의미 |
|------|---------|---------|------|
| Planner | 📋 | U+1F4CB | 클립보드 (기획) |
| Backend | 🔌 | U+1F50C | 플러그 (연결/API) |
| Frontend | 🎨 | U+1F3A8 | 아티스트 팔레트 (디자인) |

### 7.2 섹션별 이모티콘

| 섹션 | 이모티콘 | 사용처 |
|------|---------|--------|
| 🏠 | 홈 | 헤더 (대시보드) |
| 📊 | 차트 | 통계 섹션 제목 |
| 📁 | 폴더 | 파일 수 통계 |
| 📝 | 문서 | 노트 수 통계 |
| 👥 | 사람들 | 팀 멤버 통계 |
| ⏱️ | 타이머 | 소요 시간 통계 |
| 📋 | 클립보드 | 활동 피드 |
| ✅ | 체크마크 | 완료 상태 |
| 🔧 | 렌치 | 수정/수정 활동 |
| 🚀 | 로켓 | 배포/시작 활동 |
| 🎉 | 파티 | 특별한 이벤트 |
| ⚙️ | 기어 | 설정 |
| 🔔 | 벨 | 알림 |
| 👤 | 사람 | 사용자 프로필 |

---

## 8. 컴포넌트 라이브러리

### 8.1 재사용 가능한 컴포넌트

**역할 카드 컴포넌트:**
```html
<div class="bg-white rounded-lg shadow-md hover:shadow-lg hover:-translate-y-1 transition duration-300 p-6">
  <div class="flex items-center gap-3 mb-4">
    <span class="text-3xl">📋</span>
    <h3 class="text-xl font-bold text-gray-900">Planner</h3>
  </div>
  <p class="text-sm text-gray-600 mb-6">프로젝트 기획 및 구조 설계</p>
  
  <div class="mb-4">
    <div class="flex items-center justify-between mb-2">
      <span class="text-sm font-medium text-gray-700">진행률</span>
      <span class="text-sm font-bold text-gray-900">100%</span>
    </div>
    <div class="bg-gray-200 rounded-full h-3 overflow-hidden">
      <div class="bg-blue-500 h-full" style="width: 100%"></div>
    </div>
  </div>
  
  <button class="w-full bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600 transition duration-300">
    상세 보기
  </button>
</div>
```

**통계 카드 컴포넌트:**
```html
<div class="bg-white rounded-lg shadow-md p-6">
  <div class="flex items-center justify-between mb-4">
    <span class="text-4xl">📁</span>
    <span class="text-xs font-bold text-green-600 bg-green-50 px-3 py-1 rounded-full">+15%</span>
  </div>
  <h3 class="text-3xl font-bold text-gray-900">1,234</h3>
  <p class="text-sm text-gray-600">전체 파일 수</p>
</div>
```

**활동 피드 아이템:**
```html
<div class="flex gap-4 pb-6 border-b border-gray-200 last:border-b-0">
  <span class="text-2xl">✅</span>
  <div class="flex-1">
    <p class="text-sm text-gray-600 mb-1">2시간 전</p>
    <p class="font-medium text-gray-900">Alice | Planner 단계 완료</p>
    <p class="text-sm text-gray-600 mt-1">프로젝트 기획이 완료되었습니다.</p>
  </div>
</div>
```

---

## 9. 상호작용 및 애니메이션

### 9.1 호버 효과

```html
<!-- 카드 호버 -->
<div class="hover:shadow-lg hover:-translate-y-1 transition duration-300">
  카드 콘텐츠
</div>

<!-- 버튼 호버 -->
<button class="hover:bg-blue-600 active:scale-95 transition duration-150">
  버튼
</button>

<!-- 링크 호버 -->
<a class="hover:text-blue-600 transition duration-200">링크</a>
```

### 9.2 전환 효과

- **기본 전환**: `transition duration-300`
- **빠른 전환**: `transition duration-150`
- **느린 전환**: `transition duration-500`

### 9.3 JavaScript 인터랙션 (선택사항)

- 활동 피드 실시간 업데이트
- 진행률 바 애니메이션
- 모달 팝업 (상세 보기)
- 다크 모드 토글

---

## 10. 성능 및 접근성

### 10.1 성능 최적화

- **CDN에서 Tailwind CSS 로드** (빠른 로딩)
- **이미지 최적화**: WebP 포맷 또는 압축
- **폰트**: 시스템 폰트 또는 `font-sans`
- **번들 크기**: < 100KB (gzip)

### 10.2 접근성 (WCAG 2.1)

- **색상 대비**: AA 등급 이상 (4.5:1)
- **아이콘 라벨**: `alt` 속성 및 `aria-label` 제공
- **키보드 네비게이션**: Tab 키로 이동 가능
- **스크린 리더**: 적절한 의미론적 HTML 사용

---

## 11. 파일 구조

```
NOTEAI/
├── index.html          # 메인 대시보드 페이지
├── script.js           # 상호작용 JavaScript
├── style.css           # 커스텀 스타일 (선택사항)
├── PLAN.md             # 이 파일 (기획 문서)
├── assets/
│   ├── images/
│   │   └── avatar.jpg
│   └── icons/
└── README.md           # 개발 가이드
```

---

## 12. 개발 타임라인 및 체크리스트

### 12.1 Phase 1: 기획 (완료) ✅
- [x] 프로젝트 개요 정의
- [x] 페이지 구조 설계
- [x] 색상 팔레트 정의
- [x] 컴포넌트 설계
- [x] PLAN.md 작성

### 12.2 Phase 2: 디자인 (진행 예정)
- [ ] Figma/디자인 시안 작성
- [ ] 컴포넌트 디자인 상세 작성
- [ ] 프로토타입 검수

### 12.3 Phase 3: 프론트엔드 구현 (진행 예정)
- [ ] HTML 구조 작성
- [ ] Tailwind CSS 스타일링
- [ ] 반응형 테스트
- [ ] JavaScript 상호작용 추가

### 12.4 Phase 4: 테스트 및 배포 (진행 예정)
- [ ] 크로스 브라우저 테스트
- [ ] 모바일 반응형 테스트
- [ ] 접근성 검사
- [ ] 성능 최적화
- [ ] 배포

---

## 13. 참고 자료 및 도구

### 13.1 사용 기술
- **HTML5**: 의미론적 마크업
- **Tailwind CSS**: 유틸리티 기반 CSS 프레임워크
- **JavaScript ES6+**: 상호작용 구현
- **CDN**: Tailwind CSS CDN 사용

### 13.2 유용한 링크
- [Tailwind CSS 공식 문서](https://tailwindcss.com)
- [이모티콘 검색](https://emojipedia.org)
- [색상 선택기](https://coolors.co)
- [반응형 테스트](https://responsively.app)

---

## 14. 추가 고려사항

### 14.1 향후 개선 사항
- 다크 모드 지원
- 국제화 (다국어 지원)
- 데이터베이스 연동
- 실시간 알림
- 모바일 앱 버전

### 14.2 보안 고려사항
- XSS 방지
- CSRF 토큰
- 입력 검증
- 데이터 암호화

### 14.3 SEO 최적화
- 메타 태그 설정
- 구조화된 데이터 (Schema.org)
- 페이지 제목 및 설명

---

## 결론

NOTEAI 대시보드는 **모던하고 직관적인 디자인**을 통해 프로젝트 진행 상황을 효과적으로 관리할 수 있는 도구입니다. Tailwind CSS를 활용한 반응형 설계로 모든 디바이스에서 최적의 사용자 경험을 제공합니다.

다음 단계는 **Phase 3: 프론트엔드 구현**으로 진행하여 실제 HTML/CSS 코드를 작성합니다.

---

**문서 작성**: Planner (기획자) 📋  
**최종 업데이트**: 2026-08-26  
**상태**: 기획 완료, 구현 준비 중
