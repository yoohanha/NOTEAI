# NOTEAI 사이드바 메뉴 기획 문서 v1.0

**작성일**: 2026-08-26  
**프로젝트명**: NOTEAI 사이드바 메뉴  
**역할**: Planner (기획자)  
**상태**: Phase 1 기획 완료 ✅

---

## 📋 Executive Summary

NOTEAI의 **모던한 사이드바 네비게이션 메뉴**를 Heroicons(SVG) + Tailwind CSS를 활용하여 구현합니다. 다크 모드를 완벽히 지원하며, 반응형 디자인으로 모든 디바이스에서 일관된 사용자 경험을 제공합니다.

**핵심 목표:**
- ✅ 깔끔하고 모던한 사이드바 UI 구현
- ✅ Heroicons SVG 아이콘 통합
- ✅ Tailwind CSS 다크 모드 완벽 지원
- ✅ 반응형 디자인 (데스크톱/태블릿/모바일)
- ✅ 호버 및 활성화 상태 인터랙션
- ✅ 접근성 고려 (WCAG 2.1)

---

## 1. 프로젝트 개요

### 1.1 기본 정보

| 항목 | 내용 |
|------|------|
| **프로젝트명** | NOTEAI 사이드바 메뉴 |
| **목적** | NOTEAI 웹사이트의 주 네비게이션 메뉴 |
| **위치** | 왼쪽 측면 (데스크톱) / 토글 가능 (모바일) |
| **기술 스택** | HTML5, Tailwind CSS 3.x, Heroicons 2.x, JavaScript |
| **타겟 사용자** | NOTEAI 사용자 (연구원, 학생, 교수) |
| **브라우저** | Chrome, Firefox, Safari, Edge (최신 2개 버전) |

### 1.2 디자인 철학

```
┌─────────────────────────────────────┐
│  🎯 Design Principles               │
├─────────────────────────────────────┤
│ 1. 단순성 (Simplicity)              │
│    → 최소한의 요소로 최대의 효과    │
│                                     │
│ 2. 명확성 (Clarity)                 │
│    → 아이콘과 텍스트로 직관적 표현 │
│                                     │
│ 3. 일관성 (Consistency)             │
│    → 라이트/다크 모드에서 동일한   │
│       시각 경험                     │
│                                     │
│ 4. 접근성 (Accessibility)           │
│    → 키보드 네비게이션, 스크린리더 │
│                                     │
│ 5. 반응성 (Responsiveness)          │
│    → 모든 화면 크기에 최적화       │
└─────────────────────────────────────┘
```

---

## 2. 메뉴 구조 및 정의

### 2.1 메인 메뉴 (3개 항목)

#### 📊 Menu 1: Dashboard (대시보드)

| 속성 | 값 |
|------|-----|
| **텍스트** | Dashboard |
| **Heroicon** | HomeIcon (outline, 24x24) |
| **설명** | 주요 통계, 최근 논문, 진행 중인 작업 개요 |
| **링크** | `/dashboard` |
| **활성화 색상** | Blue (#3B82F6) |
| **우선순위** | 1 (가장 자주 사용) |
| **보조 텍스트** | "메인 대시보드로 이동" |

**아이콘 특성:**
```xml
<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" 
     stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
  <path stroke-linecap="round" stroke-linejoin="round" 
        d="m2.25 12 8.954-8.954c.78-.785 2.075-.785 2.853 0l8.956 8.954m-17.5 0a.75.75 0 0 0-.072 1.498h.144a.75.75 0 0 0 .072-1.498M9.75 12l-4.5 4.5M12 9.75l4.5 4.5" />
</svg>
```

---

#### 📄 Menu 2: Upload Paper (논문 업로드)

| 속성 | 값 |
|------|-----|
| **텍스트** | Upload Paper |
| **Heroicon** | ArrowUpTrayIcon (outline, 24x24) |
| **설명** | 새로운 논문 PDF/DOC 파일 업로드 |
| **링크** | `/upload` |
| **활성화 색상** | Green (#10B981) |
| **우선순위** | 2 (자주 사용) |
| **보조 텍스트** | "새 논문 업로드하기" |

**아이콘 특성:**
```xml
<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" 
     stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
  <path stroke-linecap="round" stroke-linejoin="round" 
        d="M12 16.5V9.75m0 0l-3 3m3-3l3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775A5.25 5.25 0 1115 6.75" />
</svg>
```

---

#### 🧠 Menu 3: Knowledge Graph (지식 그래프)

| 속성 | 값 |
|------|-----|
| **텍스트** | Knowledge Graph |
| **Heroicon** | CubeTransparentIcon (outline, 24x24) |
| **설명** | 논문 간 관계 및 지식 시각화 네트워크 |
| **링크** | `/graph` |
| **활성화 색상** | Purple (#8B5CF6) |
| **우선순위** | 3 (가끔 사용) |
| **보조 텍스트** | "지식 네트워크 탐색하기" |

**아이콘 특성:**
```xml
<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" 
     stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
  <path stroke-linecap="round" stroke-linejoin="round" 
        d="M12 6.75a.75.75 0 110-1.5.75.75 0 010 1.5zM7 13.5a.75.75 0 110-1.5.75.75 0 010 1.5zM17 13.5a.75.75 0 110-1.5.75.75 0 010 1.5zM12 20.25a.75.75 0 110-1.5.75.75 0 010 1.5z" />
</svg>
```

---

### 2.2 부가 메뉴 (하단, 2개 항목)

#### ⚙️ Menu 4: Settings (설정)

| 속성 | 값 |
|------|-----|
| **텍스트** | Settings |
| **Heroicon** | CogIcon (outline, 24x24) |
| **링크** | `/settings` |
| **분리자** | 예 (경계선으로 분리) |
| **보조 텍스트** | "앱 설정 구성" |

**아이콘 특성:**
```xml
<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" 
     stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
  <path stroke-linecap="round" stroke-linejoin="round" 
        d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.592c.55 0 1.02.398 1.11.94a6.047 6.047 0 001.366 2.29c.513.612 1.238.72 1.912.72.67 0 1.41.108 1.912-.72a6.047 6.047 0 001.366-2.29c.09-.542.56-.94 1.11-.94h2.592c.55 0 1.02.398 1.11.94a6.065 6.065 0 01-.227 1.378l-.883 5.3c-.287 1.722-1.666 2.957-3.388 2.95a8.25 8.25 0 01-7.23 0c-1.722.007-3.1-1.228-3.388-2.95l-.5-3.002a6.065 6.065 0 01-.227-1.378zM12 15a1.5 1.5 0 100-3 1.5 1.5 0 000 3z" />
</svg>
```

---

#### 🚪 Menu 5: Logout (로그아웃)

| 속성 | 값 |
|------|-----|
| **텍스트** | Logout |
| **Heroicon** | ArrowRightOnRectangleIcon (outline, 24x24) |
| **링크** | `/logout` |
| **색상** | Red (#EF4444 on hover) |
| **보조 텍스트** | "계정에서 로그아웃" |

**아이콘 특성:**
```xml
<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" 
     stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
  <path stroke-linecap="round" stroke-linejoin="round" 
        d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
</svg>
```

---

### 2.3 메뉴 계층 구조

```
NOTEAI Sidebar
│
├─ 헤더 (로고 & 제목)
│
├─ 메인 메뉴
│  ├─ 🏠 Dashboard
│  ├─ 📤 Upload Paper
│  └─ 🧠 Knowledge Graph
│
├─ 구분선 (경계선)
│
└─ 부가 메뉴 (하단)
   ├─ ⚙️ Settings
   └─ 🚪 Logout
```

---

## 3. 색상 팔레트 정의

### 3.1 라이트 모드 (Light Mode)

**배경 및 텍스트:**

```
┌────────────────────────────────────────┐
│        Light Mode Palette              │
├────────────────────────────────────────┤
│ 배경색 (bg-white)         │ #FFFFFF    │
│ 테두리색 (border)         │ #E5E7EB    │
│ 섀도우 (shadow)           │ 0 1px 3px  │
└────────────────────────────────────────┘
```

**텍스트 및 아이콘:**

| 요소 | 색상 코드 | Tailwind 클래스 | 사용 |
|------|---------|-----------------|------|
| 주 텍스트 | #374151 | `text-gray-700` | 메뉴 텍스트 |
| 보조 텍스트 | #6B7280 | `text-gray-500` | 설명 텍스트 |
| 기본 아이콘 | #6B7280 | `text-gray-500` | 기본 아이콘 색 |

**호버 상태:**

| 요소 | 색상 코드 | Tailwind 클래스 |
|------|---------|-----------------|
| 호버 배경 | #F3F4F6 | `hover:bg-gray-100` |
| 호버 텍스트 | #1F2937 | `hover:text-gray-900` |
| 호버 아이콘 | #374151 | `group-hover:text-gray-700` |

**활성화 상태:**

| 메뉴 | 배경 | 텍스트 | 경계선 |
|------|------|--------|--------|
| Dashboard | #EFF6FF (blue-50) | #1E40AF (blue-800) | #3B82F6 (blue-500) |
| Upload | #ECFDF5 (green-50) | #065F46 (green-800) | #10B981 (green-500) |
| Graph | #F5F3FF (purple-50) | #5B21B6 (purple-800) | #8B5CF6 (purple-500) |

---

### 3.2 다크 모드 (Dark Mode)

**배경 및 텍스트:**

```
┌────────────────────────────────────────┐
│        Dark Mode Palette               │
├────────────────────────────────────────┤
│ 배경색 (dark:bg-gray-900) │ #111827    │
│ 테두리색 (dark:border)    │ #1F2937    │
│ 섀도우 (shadow)           │ 0 1px 2px  │
└────────────────────────────────────────┘
```

**텍스트 및 아이콘:**

| 요소 | 색상 코드 | Tailwind 클래스 | 사용 |
|------|---------|-----------------|------|
| 주 텍스트 | #D1D5DB | `dark:text-gray-300` | 메뉴 텍스트 |
| 보조 텍스트 | #9CA3AF | `dark:text-gray-400` | 설명 텍스트 |
| 기본 아이콘 | #9CA3AF | `dark:text-gray-400` | 기본 아이콘 색 |

**호버 상태:**

| 요소 | 색상 코드 | Tailwind 클래스 |
|------|---------|-----------------|
| 호버 배경 | #374151 | `dark:hover:bg-gray-800` |
| 호버 텍스트 | #F3F4F6 | `dark:hover:text-gray-100` |
| 호버 아이콘 | #D1D5DB | `dark:group-hover:text-gray-300` |

**활성화 상태:**

| 메뉴 | 배경 | 텍스트 | 경계선 |
|------|------|--------|--------|
| Dashboard | #1E3A8A (blue-900) | #93C5FD (blue-300) | #3B82F6 (blue-500) |
| Upload | #064E3B (green-900) | #86EFAC (green-300) | #10B981 (green-500) |
| Graph | #3F0F63 (purple-900) | #D8B4FE (purple-300) | #8B5CF6 (purple-500) |

---

### 3.3 색상 적용 예시

**라이트 모드:**
```html
<aside class="w-64 bg-white border-r border-gray-200 shadow-sm">
  <a href="#" class="text-gray-700 hover:bg-gray-100">
    <svg class="text-gray-500 group-hover:text-gray-700"></svg>
    Dashboard
  </a>
</aside>
```

**다크 모드:**
```html
<aside class="w-64 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800">
  <a href="#" class="text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800">
    <svg class="text-gray-500 dark:text-gray-400 group-hover:text-gray-700 dark:group-hover:text-gray-300"></svg>
    Dashboard
  </a>
</aside>
```

---

## 4. 사이드바 레이아웃 설계

### 4.1 사이드바 컨테이너 스펙

**물리적 사양:**

| 속성 | 데스크톱 | 태블릿 | 모바일 |
|------|---------|--------|--------|
| 너비 (width) | 256px (w-64) | 224px (w-56) | 100% (토글) |
| 높이 (height) | 100vh (full screen) | 100vh | 100vh |
| 위치 (position) | 고정 (fixed) | 고정 | 고정 (z-40) |
| 방향 (direction) | 왼쪽 (left-0) | 왼쪽 | 왼쪽 |
| 수평 스크롤 | 아니오 | 아니오 | 아니오 |

**간격 (Spacing):**

| 요소 | 값 | Tailwind |
|------|-----|---------|
| 내부 패딩 (padding) | 1.5rem | `px-6 py-6` |
| 요소 간 간격 | 0.5rem | `space-y-2` |
| 메뉴 항목 패딩 | 0.75rem | `px-3 py-3` |

---

### 4.2 헤더 섹션 (로고)

**높이:** 80px (px-6 py-6)  
**내용:**
- 로고 텍스트: "NOTEAI"
- 부제: "Research Platform" (선택사항, 작은 텍스트)

**스타일:**
```css
header {
  padding: 1.5rem; /* py-6 px-6 */
  border-bottom: 1px solid #E5E7EB; /* border-gray-200 */
}

h1 {
  font-size: 1.5rem; /* text-2xl */
  font-weight: 700; /* font-bold */
  color: #111827; /* text-gray-900 */
}
```

---

### 4.3 메뉴 섹션 (메인)

**높이:** 자동 (콘텐츠에 따라)  
**패딩:** `px-3 py-6`  
**메뉴 항목 간격:** `space-y-2`

**메뉴 항목 스펙:**

```
┌──────────────────────────────────┐
│ [Icon] [Text]                   │ ← 높이: 3rem (h-12)
├──────────────────────────────────┤
│ padding: 0.75rem (px-3 py-3)    │
├──────────────────────────────────┤
│ display: flex                     │
│ align-items: center              │
│ gap: 0.75rem (space-x-3)        │
└──────────────────────────────────┘
```

**아이콘 사양:**
- 크기: 24x24px (w-6 h-6)
- 색상: `currentColor` (상속)
- stroke-width: 1.5

**텍스트 사양:**
- 폰트 크기: 14px (text-sm)
- 폰트 무게: 500 (font-medium)
- 색상: `text-gray-700` (light) / `dark:text-gray-300` (dark)

---

### 4.4 구분선 (경계선)

**위치:** 메인 메뉴와 부가 메뉴 사이  
**높이:** 1px  
**색상:** `border-gray-200` (light) / `dark:border-gray-800` (dark)  
**마진:** `my-2`

---

### 4.5 부가 메뉴 섹션 (하단)

**위치:** `absolute bottom-0 left-0 right-0`  
**높이:** 자동  
**패딩:** `px-3 py-6`  
**상단 경계선:** 1px `border-gray-200` (light) / `dark:border-gray-800` (dark)

---

### 4.6 시각적 레이아웃

```
┌─────────────────────────────┐
│  w-64 (256px)               │
├─────────────────────────────┤
│ NOTEAI                  ← 헤더  │ h: 80px
├─────────────────────────────┤
│                             │
│ 🏠 Dashboard            ← 메인  │ h: 48px × 3
│ 📤 Upload Paper             │
│ 🧠 Knowledge Graph          │
│                             │
├─────────────────────────────┤ ← 구분선 (border-y)
│                             │
│ ⚙️ Settings             ← 부가  │ h: 48px × 2
│ 🚪 Logout                   │
│                             │
└─────────────────────────────┘
```

---

## 5. 인터랙션 디자인

### 5.1 호버 상태 (Hover)

**시각적 변화:**

**라이트 모드:**
```
배경: White (#FFFFFF) → Light Gray (#F3F4F6)
텍스트: Gray-700 (#374151) → Gray-900 (#1F2937)
아이콘: Gray-500 (#6B7280) → Gray-700 (#374151)
```

**다크 모드:**
```
배경: Gray-900 (#111827) → Gray-800 (#1F2937)
텍스트: Gray-300 (#D1D5DB) → Gray-100 (#F3F4F6)
아이콘: Gray-400 (#9CA3AF) → Gray-300 (#D1D5DB)
```

**트랜지션:**
- 속성: `transition-colors`
- 시간: `duration-200`
- 타이밍: `ease-in-out` (기본)

**CSS 클래스:**
```html
<a class="text-gray-700 dark:text-gray-300 
         hover:bg-gray-100 dark:hover:bg-gray-800
         transition-colors duration-200 group">
  <svg class="text-gray-500 dark:text-gray-400 
              group-hover:text-gray-700 dark:group-hover:text-gray-300"></svg>
  Dashboard
</a>
```

---

### 5.2 활성화 상태 (Active/Selected)

**시각적 변화:**

**Dashboard (Blue):**
```
라이트 모드:
  배경: #EFF6FF (blue-50)
  텍스트: #1E40AF (blue-800)
  아이콘: #2563EB (blue-600)
  왼쪽 경계선: 4px #3B82F6 (blue-500)

다크 모드:
  배경: #1E3A8A (blue-900)
  텍스트: #93C5FD (blue-300)
  아이콘: #60A5FA (blue-400)
  왼쪽 경계선: 4px #3B82F6 (blue-500)
```

**Upload Paper (Green):**
```
라이트 모드:
  배경: #ECFDF5 (green-50)
  텍스트: #065F46 (green-800)
  아이콘: #059669 (green-600)
  왼쪽 경계선: 4px #10B981 (green-500)

다크 모드:
  배경: #064E3B (green-900)
  텍스트: #86EFAC (green-300)
  아이콘: #4ADE80 (green-400)
  왼쪽 경계선: 4px #10B981 (green-500)
```

**Knowledge Graph (Purple):**
```
라이트 모드:
  배경: #F5F3FF (purple-50)
  텍스트: #5B21B6 (purple-800)
  아이콘: #7C3AED (purple-600)
  왼쪽 경계선: 4px #8B5CF6 (purple-500)

다크 모드:
  배경: #3F0F63 (purple-900)
  텍스트: #D8B4FE (purple-300)
  아이콘: #C084FC (purple-400)
  왼쪽 경계선: 4px #8B5CF6 (purple-500)
```

**CSS 클래스:**
```html
<!-- Active Dashboard -->
<a class="bg-blue-50 dark:bg-blue-900 
         text-blue-800 dark:text-blue-300
         border-l-4 border-blue-500
         font-semibold">
  <svg class="text-blue-600 dark:text-blue-400"></svg>
  Dashboard
</a>
```

---

### 5.3 클릭 피드백

**시각적 효과:**
- 스케일: 95% (`active:scale-95`)
- 투명도: 90% (`active:opacity-90`)
- 지속 시간: 100ms

**CSS:**
```css
.menu-item:active {
  transform: scale(0.95);
  opacity: 0.9;
  transition: all 100ms ease-out;
}
```

---

### 5.4 포커스 상태 (Accessibility)

**키보드 네비게이션:**
```html
<a href="#" class="focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900">
  Dashboard
</a>
```

**스크린 리더:**
```html
<a href="#" aria-label="대시보드 페이지로 이동">
  <svg aria-hidden="true"></svg>
  Dashboard
</a>
```

---

## 6. Heroicons 통합 전략

### 6.1 아이콘 선택 기준

| 기준 | 설명 |
|------|------|
| **크기** | 24x24px (웹 UI에 최적) |
| **스타일** | outline (일관성 있는 스트로크) |
| **색상** | currentColor (Tailwind로 제어) |
| **SVG 포맷** | 인라인 (HTTP 요청 최소화) |

### 6.2 SVG 구조

**기본 SVG 템플릿:**
```xml
<svg xmlns="http://www.w3.org/2000/svg" 
     fill="none" 
     viewBox="0 0 24 24" 
     stroke-width="1.5" 
     stroke="currentColor" 
     class="w-6 h-6">
  <path stroke-linecap="round" 
        stroke-linejoin="round" 
        d="[path-data]" />
</svg>
```

### 6.3 Heroicons 출처

- **공식 사이트**: https://heroicons.com/
- **라이선스**: MIT (자유로운 상업 사용 가능)
- **버전**: 2.x
- **CDN** (선택사항): `https://cdn.jsdelivr.net/npm/heroicons@2.0.18/outline/`

---

## 7. Tailwind CSS 구현

### 7.1 주요 클래스 목록

**컨테이너:**
```tailwind
w-64              /* 너비 256px */
bg-white          /* 배경색 (라이트) */
dark:bg-gray-900  /* 배경색 (다크) */
h-screen          /* 높이 100vh */
border-r          /* 오른쪽 경계선 */
border-gray-200   /* 경계선 색상 (라이트) */
dark:border-gray-800  /* 경계선 색상 (다크) */
shadow-sm         /* 그림자 (미묘) */
fixed             /* 고정 위치 */
left-0            /* 왼쪽 정렬 */
top-0             /* 상단 정렬 */
z-40              /* z-index 40 */
```

**메뉴 항목:**
```tailwind
flex              /* Flexbox */
items-center      /* 수직 정렬 (가운데) */
space-x-3         /* 자식 간 가로 간격 (0.75rem) */
px-3 py-3         /* 패딩 */
rounded-lg        /* 모서리 반올림 (0.5rem) */
text-sm           /* 폰트 크기 (0.875rem) */
font-medium       /* 폰트 무게 (500) */
text-gray-700     /* 텍스트 색상 (라이트) */
dark:text-gray-300  /* 텍스트 색상 (다크) */
hover:bg-gray-100   /* 호버 배경 (라이트) */
dark:hover:bg-gray-800  /* 호버 배경 (다크) */
transition-colors /* 전환 속성 */
duration-200      /* 전환 시간 */
```

**활성화:**
```tailwind
bg-blue-50        /* 활성화 배경 (라이트) */
dark:bg-blue-900  /* 활성화 배경 (다크) */
text-blue-800     /* 활성화 텍스트 (라이트) */
dark:text-blue-300  /* 활성화 텍스트 (다크) */
border-l-4        /* 왼쪽 경계선 */
border-blue-500   /* 경계선 색상 */
font-semibold     /* 폰트 무게 (600) */
```

**아이콘:**
```tailwind
w-6 h-6           /* 크기 (24x24) */
text-gray-500     /* 색상 (라이트) */
dark:text-gray-400  /* 색상 (다크) */
group-hover:text-gray-700  /* 호버 색상 */
```

---

### 7.2 Tailwind 설정 (tailwind.config.js)

```javascript
module.exports = {
  content: [
    "./index.html",
    "./sidebar.html",
    "./**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: 'class', // HTML 클래스 기반 다크 모드
  theme: {
    extend: {
      spacing: {
        // 기본값으로 충분함
      },
      colors: {
        // Tailwind 기본 색상 사용
      },
    },
  },
  plugins: [],
}
```

---

## 8. 반응형 디자인

### 8.1 Breakpoint 전략

| 화면 크기 | Tailwind | 사이드바 | 동작 |
|---------|---------|--------|------|
| **모바일** | < 640px (xs) | 토글 가능 | 오버레이, 슬라이드인/아웃 |
| **작은 태블릿** | ≥ 640px (sm) | 토글 가능 | 오버레이 |
| **태블릿** | ≥ 768px (md) | w-56 고정 | 항상 표시 |
| **데스크톱** | ≥ 1024px (lg) | w-64 고정 | 항상 표시 |
| **큰 데스크톱** | ≥ 1280px (xl) | w-64 고정 | 항상 표시 |

### 8.2 반응형 구현

**HTML 구조:**
```html
<!-- 모바일 토글 버튼 -->
<button id="sidebar-toggle" class="md:hidden fixed top-4 left-4 z-50">
  <svg class="w-6 h-6"><!-- Menu Icon --></svg>
</button>

<!-- 모바일 오버레이 -->
<div id="sidebar-overlay" class="hidden md:hidden fixed inset-0 bg-black bg-opacity-50 z-30"></div>

<!-- 반응형 사이드바 -->
<aside id="sidebar" 
       class="w-64 fixed md:static h-screen left-0 top-0 z-40 
              transform -translate-x-full md:translate-x-0 
              transition-transform duration-300 
              bg-white dark:bg-gray-900">
  <!-- 사이드바 내용 -->
</aside>
```

### 8.3 메인 콘텐츠 영역

**데스크톱:**
```html
<main class="ml-64"><!-- 왼쪽 마진 (사이드바 너비) --></main>
```

**모바일:**
```html
<main class="ml-0 md:ml-56 lg:ml-64"><!-- 반응형 마진 --></main>
```

---

## 9. 다크 모드 구현

### 9.1 HTML 클래스 방식 (권장)

**활성화:**
```html
<html class="dark">
  <!-- 다크 모드 활성 -->
</html>
```

**비활성화:**
```html
<html class="">
  <!-- 라이트 모드 (기본) -->
</html>
```

### 9.2 JavaScript 토글

```javascript
// 다크 모드 토글
function toggleDarkMode() {
    document.documentElement.classList.toggle('dark');
    // localStorage에 저장
    localStorage.setItem('theme', 
        document.documentElement.classList.contains('dark') ? 'dark' : 'light'
    );
}

// 페이지 로드 시 사용자 설정 복원
function initTheme() {
    const saved = localStorage.getItem('theme');
    const system = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    const theme = saved || system;
    
    if (theme === 'dark') {
        document.documentElement.classList.add('dark');
    }
}

// 시스템 테마 변경 감지
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (e.matches) {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }
});

initTheme();
```

### 9.3 CSS 클래스 사용

**라이트 모드 기본값:**
```css
.sidebar {
  background-color: #FFFFFF;
  border-color: #E5E7EB;
}

.menu-item {
  color: #374151;
  background-color: transparent;
}

.menu-item:hover {
  background-color: #F3F4F6;
}
```

**다크 모드 (dark: 접두사):**
```css
.dark .sidebar {
  background-color: #111827;
  border-color: #1F2937;
}

.dark .menu-item {
  color: #D1D5DB;
}

.dark .menu-item:hover {
  background-color: #1F2937;
}
```

**Tailwind 클래스:**
```html
<aside class="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800">
  <a class="text-gray-700 dark:text-gray-300 
           hover:bg-gray-100 dark:hover:bg-gray-800">
    Dashboard
  </a>
</aside>
```

---

## 10. HTML 구조 설계

### 10.1 전체 문서 구조

```html
<!DOCTYPE html>
<html lang="ko" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="NOTEAI Sidebar Menu">
    <title>NOTEAI - Sidebar Navigation</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-white dark:bg-gray-950">

    <!-- 사이드바 -->
    <aside class="w-64 fixed left-0 top-0 h-screen bg-white dark:bg-gray-900 
                  border-r border-gray-200 dark:border-gray-800 shadow-sm">
        
        <!-- 헤더 (로고) -->
        <header class="px-6 py-6 border-b border-gray-200 dark:border-gray-800">
            <h1 class="text-2xl font-bold text-gray-900 dark:text-white">NOTEAI</h1>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Research Platform</p>
        </header>

        <!-- 메인 메뉴 -->
        <nav class="px-3 py-6 space-y-2">
            <!-- 메뉴 항목들 -->
        </nav>

        <!-- 부가 메뉴 (하단) -->
        <nav class="absolute bottom-0 left-0 right-0 px-3 py-6 space-y-2 
                    border-t border-gray-200 dark:border-gray-800">
            <!-- 부가 메뉴 항목들 -->
        </nav>

    </aside>

    <!-- 메인 콘텐츠 -->
    <main class="ml-64 p-8">
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">Welcome to NOTEAI</h2>
    </main>

    <!-- 스크립트 -->
    <script>
        // 다크 모드 토글, 활성 메뉴 처리, 모바일 반응형 등
    </script>

</body>
</html>
```

### 10.2 메뉴 항목 구조

```html
<!-- 메인 메뉴 항목 -->
<a href="/dashboard" 
   class="flex items-center space-x-3 px-3 py-3 rounded-lg 
          text-gray-700 dark:text-gray-300 
          hover:bg-gray-100 dark:hover:bg-gray-800 
          transition-colors duration-200 group">
    <svg class="w-6 h-6 text-gray-500 dark:text-gray-400 
                group-hover:text-gray-700 dark:group-hover:text-gray-300" 
         xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" 
         stroke-width="1.5" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" d="..." />
    </svg>
    <span class="text-sm font-medium">Dashboard</span>
</a>

<!-- 활성 메뉴 항목 -->
<a href="/dashboard" 
   class="flex items-center space-x-3 px-3 py-3 rounded-lg rounded-l-none
          bg-blue-50 dark:bg-blue-900 
          text-blue-800 dark:text-blue-300 
          border-l-4 border-blue-500
          font-semibold group">
    <svg class="w-6 h-6 text-blue-600 dark:text-blue-400" ...>
        <path ... />
    </svg>
    <span class="text-sm">Dashboard</span>
</a>
```

---

## 11. 구현 체크리스트

### ✅ Phase 1: 기획 (완료)

- [x] 프로젝트 개요 정의
- [x] 메뉴 구조 및 항목 정의 (5개)
- [x] 색상 팔레트 정의 (라이트/다크)
- [x] 레이아웃 설계 (데스크톱/태블릿/모바일)
- [x] Heroicons 선택 (5개)
- [x] HTML 구조 설계
- [x] Tailwind CSS 클래스 정의
- [x] 다크 모드 구현 전략
- [x] 인터랙션 디자인
- [x] 반응형 디자인 계획
- [x] SIDEBAR_PLAN.md 작성

### 📝 Phase 2: 설계 (예정)

- [ ] 목업/와이어프레임 작성
- [ ] 색상 테스트 (라이트/다크)
- [ ] 아이콘 SVG 최적화
- [ ] 인터랙션 미리보기

### 💻 Phase 3: 구현 (예정)

- [ ] HTML 작성 (Heroicons 통합)
- [ ] Tailwind CSS 적용
- [ ] 다크 모드 JavaScript 구현
- [ ] 활성 메뉴 하이라이트 구현
- [ ] 모바일 토글 메뉴 구현
- [ ] 반응형 테스트 (모바일/태블릿/데스크톱)

### 🧪 Phase 4: 테스트 & 배포 (예정)

- [ ] 크로스 브라우저 테스트 (Chrome, Firefox, Safari, Edge)
- [ ] 다크 모드 토글 테스트
- [ ] 호버/활성화/클릭 효과 테스트
- [ ] 키보드 네비게이션 테스트 (Tab, Enter)
- [ ] 스크린 리더 테스트 (VoiceOver, NVDA)
- [ ] 성능 테스트 (페이지 로드 시간, LCP, CLS)
- [ ] 문서화 및 주석 추가
- [ ] 최종 배포

---

## 12. 파일 구조

```
NOTEAI/
├── SIDEBAR_PLAN.md         # 이 파일 (기획 문서)
├── sidebar.html            # 메인 사이드바 (생성 예정)
├── sidebar-responsive.html # 반응형 버전 (생성 예정)
├── assets/
│   ├── css/
│   │   ├── sidebar.css       # 커스텀 스타일
│   │   └── dark-mode.css     # 다크 모드 추가 스타일
│   └── js/
│       ├── sidebar.js        # 인터랙션
│       ├── dark-mode.js      # 다크 모드 토글
│       └── responsive.js     # 반응형 처리
└── docs/
    ├── DEPLOYMENT.md         # 배포 가이드
    ├── ACCESSIBILITY.md      # 접근성 가이드
    └── TESTING.md           # 테스트 가이드
```

---

## 13. 개발 가이드

### 13.1 필수 도구

- 텍스트 에디터 (VS Code, Sublime Text 등)
- 모던 브라우저 (Chrome, Firefox, Safari, Edge)
- Git (버전 관리)

### 13.2 라이브러리

- **Tailwind CSS 3.x** (CDN 또는 npm)
- **Heroicons 2.x** (SVG 인라인 또는 CDN)
- **Vanilla JavaScript** (추가 라이브러리 없음)

### 13.3 성능 목표

- 페이지 로드 시간: < 1초
- Largest Contentful Paint (LCP): < 2.5초
- Cumulative Layout Shift (CLS): < 0.1
- 번들 크기: < 50KB (HTML + CSS + JS)

---

## 14. 참고자료

### 14.1 공식 문서

- **Tailwind CSS**: https://tailwindcss.com/docs
- **Tailwind Dark Mode**: https://tailwindcss.com/docs/dark-mode
- **Heroicons**: https://heroicons.com/
- **MDN Web Docs**: https://developer.mozilla.org/

### 14.2 접근성 표준

- **WCAG 2.1**: https://www.w3.org/WAI/WCAG21/quickref/
- **WAI-ARIA**: https://www.w3.org/WAI/ARIA/apg/

### 14.3 색상 도구

- **Tailwind Color Generator**: https://www.tailwindshades.com/
- **Color Contrast Checker**: https://webaim.org/resources/contrastchecker/
- **Color Picker**: https://coolors.co/

---

## 15. FAQ & 주의사항

### 15.1 자주 묻는 질문

**Q: Heroicons를 어디서 다운로드하나요?**  
A: https://heroicons.com/ 에서 직접 SVG 코드를 복사하거나, npm으로 설치할 수 있습니다.

**Q: 다크 모드 토글은 어떻게 구현하나요?**  
A: JavaScript로 `document.documentElement.classList.toggle('dark')`를 사용하고, localStorage에 저장합니다.

**Q: 모바일에서 사이드바가 자동으로 숨겨지나요?**  
A: 현재 기획에서는 토글 버튼으로 표시/숨김을 제어합니다. Phase 3에서 구현합니다.

**Q: SEO 최적화가 필요한가요?**  
A: 기본적인 메타 태그와 의미론적 HTML을 사용하면 충분합니다.

### 15.2 주의사항

- ⚠️ SVG 색상은 `stroke="currentColor"`를 사용하여 Tailwind 클래스로 제어
- ⚠️ 다크 모드 테스트는 별도의 브라우저 환경에서 수행
- ⚠️ 모바일 반응형은 CSS 미디어 쿼리로 구현 (not JavaScript)
- ⚠️ 접근성: 모든 링크에 `aria-label` 추가 (필수)

---

## 결론

NOTEAI 사이드바 메뉴는 **깔끔하고 모던한 디자인**과 **완벽한 다크 모드 지원**을 통해 사용자에게 최고의 경험을 제공합니다. Heroicons SVG와 Tailwind CSS의 조합으로 유지보수가 용이하고 확장 가능한 구조를 갖추고 있습니다.

**다음 단계:**
1. **Phase 2**: 디자인 검증 및 색상 테스트
2. **Phase 3**: HTML/CSS 구현 (Frontend Designer)
3. **Phase 4**: 테스트 및 배포

---

**작성자**: Planner Agent 📋  
**마지막 수정**: 2026-08-26  
**상태**: ✅ Phase 1 완료 → Phase 2 준비 중  
**버전**: v1.0
