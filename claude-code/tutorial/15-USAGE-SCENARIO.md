# 15. 完整使用情境：從零開發「任務管理 API」

本文件示範使用 Claude Code + 本配置包，從需求到上線的完整開發流程。
**每個步驟都列出實際輸入的指令、預期輸出、以及該步驟完成的成果。**

---

## 情境設定

> 開發一個「任務管理系統」後端 API（FastAPI + PostgreSQL + Docker），
> 包含 CRUD、使用者驗證、自動測試、容器化部署。

預計產出：
- FastAPI 後端（含 auth、CRUD endpoints）
- PostgreSQL + SQLAlchemy ORM
- pytest 完整測試
- Docker Compose 一鍵啟動
- CI-ready 的品質管線

---

## Phase 1：規劃

### Step 1.1 — 啟動 Claude Code 並確認配置

```bash
$ claude
```

進入互動後：
```
> /status
```

**預期輸出：**
```
Model: sonnet
Configuration: ~/.claude/settings.json (loaded)
Agents: 7 available (planner, code-reviewer, tdd-guide, ...)
Commands: 8 custom
Skills: 7 loaded
MCP: 5 servers (github: connected, context7: connected, ...)
Hooks: 3 PostToolUse, 1 PreToolUse
```

### Step 1.2 — 建立實作計畫

```
> /plan "Build a task management REST API with FastAPI. Features: user registration/login (JWT), CRUD tasks (title, description, status, due_date), task assignment, filtering by status/assignee. Use PostgreSQL with SQLAlchemy async, include full test coverage, Docker deployment."
```

**預期輸出（由 planner agent 使用 opus 產出）：**
```
# Implementation Plan: Task Management API

## Requirements Analysis
- User auth: register, login, JWT tokens
- Task CRUD: create, read, update, delete
- Task fields: title, description, status (todo/in_progress/done), due_date, assignee
- Filtering: by status, by assignee
- Stack: FastAPI + PostgreSQL + SQLAlchemy (async) + Docker

## Risk Assessment
- ⚠️ Async SQLAlchemy session management needs careful handling
- ⚠️ JWT refresh token logic can be complex
- ✅ Standard CRUD pattern — low risk

## Implementation Phases

### Phase 1: Project Structure (15 min)
- [ ] Create project skeleton (pyproject.toml, app/, tests/)
- [ ] Configure Docker Compose (API + PostgreSQL)
- [ ] Set up Alembic for migrations

### Phase 2: Authentication (30 min)
- [ ] User model + schema
- [ ] Register endpoint
- [ ] Login endpoint (JWT generation)
- [ ] Auth dependency (get_current_user)

### Phase 3: Task CRUD (30 min)
- [ ] Task model + schemas
- [ ] CRUD endpoints with auth
- [ ] Filtering logic

### Phase 4: Testing (30 min)
- [ ] Test fixtures (DB, client, auth)
- [ ] Auth tests
- [ ] Task CRUD tests

### Phase 5: Containerization (15 min)
- [ ] Multi-stage Dockerfile
- [ ] Docker Compose with health checks
- [ ] Environment configuration

Confirm to proceed? (y/n)
```

**輸入：**
```
> y
```

---

## Phase 2：專案骨架

### Step 2.1 — 建立專案結構

```
> Create the project structure for the task management API. Use the api-design and docker-patterns skills.
```

**Claude 執行的動作：**
1. 建立目錄結構
2. 建立 `pyproject.toml`
3. 建立 `app/main.py`, `app/config.py`
4. 建立 `docker-compose.yml`
5. 建立 `Dockerfile`

**預期輸出（Claude 的最終回報）：**
```
Created project structure:
  task-api/
  ├── app/
  │   ├── __init__.py
  │   ├── main.py
  │   ├── config.py
  │   ├── database.py
  │   ├── dependencies.py
  │   ├── models/
  │   ├── schemas/
  │   ├── routers/
  │   └── services/
  ├── tests/
  │   ├── conftest.py
  │   └── __init__.py
  ├── alembic/
  │   └── versions/
  ├── pyproject.toml
  ├── Dockerfile
  ├── docker-compose.yml
  └── .env.example
```

### Step 2.2 — 確認能正常啟動

```
> docker compose up -d && curl http://localhost:8000/health
```

**預期輸出：**
```json
{"status": "healthy", "version": "0.1.0"}
```

---

## Phase 3：TDD 開發認證模組

### Step 3.1 — 用 TDD 開發 User Registration

```
> Use the tdd-workflow skill to implement user registration. Start with the test.
```

**Claude 執行流程（TDD 紅-綠-重構）：**

**RED — 寫測試：**
```python
# tests/test_auth.py
import pytest
from httpx import AsyncClient

class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        resp = await client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "SecurePass123!"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert "id" in data
        assert "password" not in data

    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {"email": "dup@example.com", "password": "SecurePass123!"}
        await client.post("/api/auth/register", json=payload)
        resp = await client.post("/api/auth/register", json=payload)
        assert resp.status_code == 409
```

**執行測試確認 FAIL：**
```bash
$ pytest tests/test_auth.py -x -v
FAILED tests/test_auth.py::TestRegister::test_register_success - 404 Not Found
```

**GREEN — 最小實作：**
```python
# app/routers/auth.py
@router.post("/register", status_code=201, response_model=UserResponse)
async def register(payload: UserCreate, db=Depends(get_db)):
    existing = await UserService(db).get_by_email(payload.email)
    if existing:
        raise HTTPException(409, "Email already registered")
    user = await UserService(db).create(payload)
    return user
```

**執行測試確認 PASS：**
```bash
$ pytest tests/test_auth.py -x -v
PASSED tests/test_auth.py::TestRegister::test_register_success
PASSED tests/test_auth.py::TestRegister::test_register_duplicate_email
2 passed in 0.45s
```

**REFACTOR — 重構（如有需要）：**
此次無需重構，程式碼已夠簡潔。

### Step 3.2 — TDD 開發 Login

```
> Continue TDD: implement login endpoint that returns JWT access token.
```

**同樣流程：寫測試 → FAIL → 實作 → PASS**

**最終測試結果：**
```bash
$ pytest tests/test_auth.py -v
PASSED tests/test_auth.py::TestRegister::test_register_success
PASSED tests/test_auth.py::TestRegister::test_register_duplicate_email
PASSED tests/test_auth.py::TestRegister::test_register_weak_password
PASSED tests/test_auth.py::TestLogin::test_login_success
PASSED tests/test_auth.py::TestLogin::test_login_wrong_password
PASSED tests/test_auth.py::TestLogin::test_login_nonexistent_user
6 passed in 0.82s
```

---

## Phase 4：TDD 開發 Task CRUD

### Step 4.1 — Task 完整 CRUD

```
> Use tdd-workflow to implement Task CRUD. Follow the api-design skill patterns.
  Endpoints: GET /api/tasks, POST /api/tasks, GET /api/tasks/{id}, PATCH /api/tasks/{id}, DELETE /api/tasks/{id}
  All endpoints require authentication.
```

**Claude 對每個 endpoint 執行 RED→GREEN→REFACTOR 循環。**

**最終測試結果：**
```bash
$ pytest tests/ -v --tb=short
tests/test_auth.py::TestRegister::test_register_success PASSED
tests/test_auth.py::TestRegister::test_register_duplicate_email PASSED
tests/test_auth.py::TestRegister::test_register_weak_password PASSED
tests/test_auth.py::TestLogin::test_login_success PASSED
tests/test_auth.py::TestLogin::test_login_wrong_password PASSED
tests/test_auth.py::TestLogin::test_login_nonexistent_user PASSED
tests/test_tasks.py::TestCreateTask::test_create_task PASSED
tests/test_tasks.py::TestCreateTask::test_create_task_unauthenticated PASSED
tests/test_tasks.py::TestListTasks::test_list_own_tasks PASSED
tests/test_tasks.py::TestListTasks::test_filter_by_status PASSED
tests/test_tasks.py::TestListTasks::test_filter_by_assignee PASSED
tests/test_tasks.py::TestGetTask::test_get_own_task PASSED
tests/test_tasks.py::TestGetTask::test_get_other_user_task_forbidden PASSED
tests/test_tasks.py::TestUpdateTask::test_update_task PASSED
tests/test_tasks.py::TestUpdateTask::test_partial_update PASSED
tests/test_tasks.py::TestDeleteTask::test_delete_task PASSED
tests/test_tasks.py::TestDeleteTask::test_delete_other_user_task PASSED
17 passed in 2.31s
```

---

## Phase 5：品質管線

### Step 5.1 — 跑品質管線

```
> /quality-gate
```

**預期輸出：**
```
Quality Gate Results
════════════════════

1. Format (ruff format)
   ✅ All 12 files formatted correctly

2. Lint (ruff check)
   ✅ No issues found

3. Type Check (mypy)
   ✅ Success: no issues found in 12 source files

4. Tests (pytest)
   ✅ 17 passed in 2.31s

5. Security (bandit)
   ✅ No issues identified

6. Coverage
   ✅ 94% (above 80% threshold)

════════════════════
Overall: ✅ PASS — Ready to commit
```

### Step 5.2 — 安全審查

```
> Run security-review skill on the entire project.
```

**預期輸出：**
```
Security Review Results
═══════════════════════

[OWASP A01] Broken Access Control
  ✅ All endpoints check ownership (get_current_user + owner_id check)

[OWASP A02] Cryptographic Failures
  ✅ Passwords hashed with bcrypt (passlib)
  ✅ JWT signed with HS256 + secret from env var

[OWASP A03] Injection
  ✅ All queries use SQLAlchemy ORM (parameterized)
  ✅ No raw SQL found

[OWASP A07] Authentication Failures
  ✅ Rate limiting on /login (5/min via slowapi)
  ⚠️  MEDIUM: Consider adding refresh token rotation

[OWASP A09] Security Logging
  ⚠️  LOW: Add logging for failed login attempts

Overall: 2 low/medium suggestions, 0 critical issues
```

---

## Phase 6：Code Review

### Step 6.1 — 全面審查

```
> /code-review
```

**預期輸出：**
```
Code Review Summary
═══════════════════

Files reviewed: 12
Confidence: HIGH (patterns consistent, tests comprehensive)

Issues Found:
─────────────
🟡 [Quality] app/services/task.py:45
   Consider extracting filter logic to a separate method for readability.

🟡 [Pattern] app/routers/tasks.py:23
   The `limit` parameter max should match your pagination UI (currently 100).

✅ [Security] No security issues found
✅ [Performance] No N+1 queries detected
✅ [Best Practices] Consistent error handling, proper status codes

Verdict: APPROVE with minor suggestions (2 non-blocking)
```

---

## Phase 7：容器化部署

### Step 7.1 — 確認 Docker 部署

```
> Use docker-patterns skill to finalize the Dockerfile and docker-compose.yml. Ensure production-ready with health checks.
```

**Claude 完成：**
- Multi-stage Dockerfile (builder + runtime)
- Non-root user
- Health check endpoint
- docker-compose with depends_on + healthcheck

### Step 7.2 — 驗證容器化

```
> docker compose up --build -d && docker compose ps
```

**預期輸出：**
```
NAME           SERVICE    STATUS                  PORTS
task-api       api        Up (healthy)            0.0.0.0:8000->8000/tcp
task-db        db         Up (healthy)            5432/tcp
```

```
> curl http://localhost:8000/docs
```
→ 開啟 Swagger UI，所有 endpoint 可見

---

## Phase 8：提交與收尾

### Step 8.1 — 更新文件

```
> /update-docs
```

**Claude 自動：**
- 更新 README.md（安裝指令、API 端點列表、環境變數）
- 確認 .env.example 完整

### Step 8.2 — 提交

```
> git add -A && git commit -m "feat: complete task management API with auth, CRUD, tests, Docker"
```

**Hook 自動觸發：** PostToolUse 格式化確認（已在開發過程中持續格式化）

### Step 8.3 — 查看花費

```
> /cost
```

**預期輸出：**
```
Session cost: $0.47
  Input tokens:  ~45,000
  Output tokens: ~12,000
  Model: sonnet (primary), opus (planner only)
```

---

## 最終成果

| 產出物 | 狀態 |
|--------|------|
| FastAPI 後端（8 endpoints） | ✅ 完成 |
| User 認證（JWT） | ✅ 完成 |
| Task CRUD + 篩選 | ✅ 完成 |
| 17 個自動測試 | ✅ 全部通過 |
| 94% 測試覆蓋率 | ✅ 超過 80% 門檻 |
| Type check (mypy) | ✅ 0 errors |
| Lint (ruff) | ✅ 0 warnings |
| Security (bandit) | ✅ 0 critical |
| Docker 容器化 | ✅ 一鍵部署 |
| API 文件 (Swagger) | ✅ 自動生成 |
| README | ✅ 已更新 |

### 使用到的指令/功能統計

| 類型 | 使用項目 |
|------|---------|
| 內建指令 | `/status`, `/cost`, `/compact` |
| 自訂指令 | `/plan`, `/quality-gate`, `/code-review`, `/update-docs` |
| Skills | `tdd-workflow`, `api-design`, `docker-patterns`, `security-review` |
| Agents | `planner` (opus), `code-reviewer` (sonnet) |
| Hooks | PostToolUse (auto-format .py on every edit) |
| MCP | 未使用（本次為本地開發） |

---

## 重點提示

1. **先規劃再動手** — `/plan` 花 2 分鐘可省 30 分鐘走錯路
2. **TDD 不可跳過紅燈步驟** — 測試必須先 FAIL，證明它在測新東西
3. **品質管線一鍵跑完** — `/quality-gate` 取代手動 6 個步驟
4. **Hook 替你做瑣事** — 格式化從不需要手動執行
5. **model 分級使用** — sonnet 做日常開發，opus 只在規劃/深度除錯時用
6. **session 管理** — 長 session 在邏輯斷點用 `/compact`，切換任務用 `/clear`
