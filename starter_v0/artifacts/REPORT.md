# Day 04 Lab v2 Report — Research Agent

## Team

- Team: K3-DAY04-B5
- Members: Nguyễn Thế Công - Mai Quốc 
- Provider/model: Groq (`llama-3.1-8b-instant`); historical evidence used Gemini

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Research agent tìm tin web, tìm bài đăng theo chủ đề/tài khoản, đọc URL, tìm
paper/policy và tổng hợp kết quả. Agent hỏi lại khi thiếu URL/handle và xin xác
nhận trước hành động gửi Telegram.

**Link dùng thử:** `http://localhost:8501`

Chạy: `.venv/bin/streamlit run app.py`

## A2. Tool agent có

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| clarify | Hỏi bổ sung hoặc xin xác nhận | không |
| timeline | Lấy bài đăng của một tài khoản | không |
| social_search | Tìm bài đăng theo chủ đề | không |
| lookup | Tìm web/tin tức | không |
| fetch | Đọc một URL cụ thể | không |
| format | Định dạng items thành digest | không |
| citation_audit | Audit URL, metadata và nguồn trùng | **có** |
| policy | Tìm company policy nội bộ | không (optional built-in) |
| papers / paper_text | Tìm và đọc paper arXiv | không (optional built-in) |
| send | Gửi Telegram sau xác nhận | không (optional built-in) |
| discord_send | Gửi plain text lên Discord sau xác nhận | **có** |

## A3. Câu hỏi mẫu để thử

1. `Tweet mới nhất của Sam Altman là gì?`
2. `Tìm trên web tin AI hôm nay và tìm thêm tweet về AI.`
3. `Tóm tắt bài này giúp mình: https://example.com`
4. `Tóm tắt 5 tweet mới nhất giúp mình` (phải hỏi account).
5. `Audit metadata các nguồn sau: [...]`

## A4. Kịch bản demo đã rehearse

| Scenario | Tool trace cần thấy | Câu chuyện cải thiện | Fallback |
|---|---|---|---|
| Tin của Sam Altman | `timeline(screenname=sama)` | v1 tách “của account” và “về topic” | v0 base run |
| Thiếu URL | `clarify` | v2 bỏ hành vi đoán URL | v3 group run |
| Đổi topic qua 3 turn | `social_search(query=Anthropic, Top)` | v3 áp dụng correction mới nhất | v3 group run |
| Audit nguồn | `citation_audit` + issues | tool local mới, không cần API key | smoke command |

# PHẦN B — Chi tiết / Bằng chứng

> Baseline v0 không đủ điều kiện so metric vì 12 provider errors do free-tier
> quota. Run group v3 lúc 10:18 là evidence hợp lệ: 10/10 measured, 0 provider
> error. Không diễn giải metric của các run có provider errors như kết quả model.

## B1. Version evidence

| Version | Prompt/tool change | Hypothesis | Metric | Before | After | Run |
|---|---|---|---|---:|---:|---|
| v0 | Starter cố ý mơ hồ | Baseline lộ routing/boundary | case accuracy | — | invalid (quota) | `runs/v0_B_base_gemini_20260729T100044395933.json` |
| v1 | Routing + handle mapping | Phân biệt OF account / ABOUT topic | routing | invalid | chưa đo do quota | — |
| v2 | Missing-info + confirmation | Không đoán và không tự gửi | arguments | invalid | chưa đo do quota | — |
| v3 | Multi-turn + precise declarations + tool mới | Carry/correct constraints đúng | group accuracy | — | **0.80** | `runs/v3_B_group_gemini_20260729T101849450314.json` |

Valid v3 group metrics: routing `0.90`, arguments `0.80`, multi-turn `1.00`,
provider errors `0`. Sau run này, hai expectation chỉ chấm default arguments đã
được sửa và Gemini adapter được bổ sung `tool_choice=required`; quota ngày đã
hết trước khi tạo được final rerun hợp lệ.

## B2. Failure analysis

| Case | Failure type | Actual | What failed | Fix |
|---|---|---|---|---|
| R03 | wrong_tool | lookup thiếu expected args | starter không map news/day | thêm convention |
| R10 | missing_info | không gọi clarify | starter bảo model tự đoán | bắt buộc clarify |
| R12 | wrong_boundary | không xin xác nhận | starter tự gửi | confirmation boundary |
| G_S03 | wrong_arg_value | clarify nhưng bỏ default | eval chấm default không cần thiết | chấm routing, bỏ default khỏi expected subset |
| G_S05 | wrong_arg_value | citation_audit đúng, bỏ default | tương tự | bỏ default khỏi expected subset |

## B3. Team eval cases

Đủ đúng 10 case: 5 single-turn (`G_S01`–`G_S05`) và 5 multi-turn
(`G_M01`–`G_M05`). Các case đo handle/limit, timeframe, missing URL, send
boundary, tool mới, correction, cancellation, switch tool và out-of-scope.

## B4. Live/UI evidence

UI `app.py` tái sử dụng `run_model_tool_loop`, hiển thị request/response,
round/tool args/result/error, artifact version, lưu transcript và đọc run JSON.
Health check local trả `ok` tại `/_stcore/health`.

## B5. Tool capability evidence

| Category | Evidence | What worked | Guardrail |
|---|---|---|---|
| Must-have tool mới | `tools/citation_audit/` | Smoke: 2 items, 1 valid, phát hiện HTTP + missing metadata | Không fetch và không tuyên bố fact-check |
| Optional built-in | Không claim live | Implementation giữ nguyên | Không demo khi thiếu key |
| Bonus | Không claim | — | — |

## B6. Reflection

- Routing policy, safety boundary và multi-turn state thuộc system prompt.
- When/when-not-to-use, argument conventions và side effects thuộc tools YAML.
- Tool execution errors và provider quota cần review thủ công; routing PASS
  không chứng minh API research đã chạy thành công.
- Việc tiếp theo: bổ sung Tavily/Firecrawl/RapidAPI keys, reset/nâng Gemini quota,
  chạy paced base v1–v3 và ba live transcript trước khi nộp chính thức.
