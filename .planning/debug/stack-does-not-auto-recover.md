---
status: resolved
trigger: "Grafana và toàn bộ stack SimpAgent cùng ở trạng thái Exited (255); truy cập http://localhost:3001/api/health không phản hồi."
created: 2026-06-21
updated: 2026-06-21T17:11:00+07:00
---

## Symptoms

- Expected behavior: Stack local tiếp tục chạy sau các gián đoạn ngắn của Docker Desktop/engine hoặc ít nhất các service dài hạn tự lên lại thay vì yêu cầu `docker compose up` thủ công.
- Actual behavior: `backend`, `frontend`, `grafana`, `kong`, `loki`, `tempo`, `promtail`, `postgres`, và `sandbox` đều cùng dừng với `Exited (255)`.
- Error messages: `Invoke-RestMethod http://localhost:3001/api/health` trả về `Unable to connect to the remote server`.
- Timeline: Các container chính đều có `FinishedAt` gần như trùng nhau vào 2026-06-21 16:56:12+07:00.
- Reproduction: Sau khi stack bị gián đoạn ở mức project/engine, dịch vụ không tự phục hồi; phải chạy lại `docker compose up --build --wait`.

## Current Focus

- hypothesis: Root cause không phải crash riêng của Grafana mà là compose resiliency gap: các service dài hạn đang dùng `restartPolicy=no`, nên một lần Docker Desktop/engine hoặc compose project bị dừng sẽ để toàn bộ stack nằm yên cho đến khi người vận hành khởi động thủ công.
- test: Thêm `restart: unless-stopped` cho các service dài hạn, thêm regression test đọc `compose.yaml`, rồi xác minh `docker compose config` và targeted test pass.
- expecting: `compose.yaml` khai báo auto-restart cho các service dài hạn; outage tương tự không còn để stack nằm chết im sau một lần gián đoạn runtime.
- next_action: Patch restart policy on durable services and verify the compose/test contract.

## Evidence

- timestamp: 2026-06-21T17:07:00+07:00
  checked: `docker compose ps --all` and `docker inspect`
  found: Các service dài hạn của stack đều `Exited (255)` với `FinishedAt` gần như giống nhau, `OOMKilled=false`, `State.Error=""`, `RestartCount=0`, `RestartPolicy=no`.
  implication: Đây không giống một container crash độc lập; nó phù hợp hơn với việc project/engine bị dừng đồng loạt và không có cơ chế tự phục hồi.

- timestamp: 2026-06-21T17:07:00+07:00
  checked: `docker compose logs` for backend/grafana/postgres/loki/tempo
  found: Grafana startup thành công, backend trả `/health` 200, Postgres và observability stack hoạt động bình thường trước khi tất cả dừng.
  implication: Không có tín hiệu root-cause nội bộ rõ ràng ở Grafana hay backend trước khi outage xảy ra.

- timestamp: 2026-06-21T17:07:00+07:00
  checked: `docker compose up --build --wait`
  found: Stack khởi động lại sạch và tất cả service dài hạn vào trạng thái healthy.
  implication: Vấn đề hiện tại là khả năng tự phục hồi sau gián đoạn runtime, không phải một lỗi khởi động bền vững trong source hiện tại.

## Eliminated

- hypothesis: Grafana provisioning lỗi làm container Grafana crash và kéo cả stack xuống.
  evidence: Grafana logs cho thấy provisioning dashboards/datasources hoàn tất, HTTP server đã lắng nghe, và các service khác cũng dừng cùng lúc.
  timestamp: 2026-06-21T17:07:00+07:00

- hypothesis: Backend hoặc Postgres bị OOM rồi cascade làm dừng phần còn lại.
  evidence: `OOMKilled=false` và `State.Error=""` cho các container chính; stack khởi động lại sạch mà không cần thay đổi ứng dụng trước khi vá.
  timestamp: 2026-06-21T17:07:00+07:00

## Resolution
root_cause: "Outage quan sát được là stack-wide stop chứ không phải crash riêng của Grafana. Các service dài hạn trong `compose.yaml` đều dùng `restartPolicy=no`, nên khi Docker Desktop/engine hoặc compose project bị gián đoạn, toàn bộ stack nằm yên ở `Exited (255)` cho đến khi operator chạy lại `docker compose up`."
fix: "Thêm `restart: unless-stopped` cho các service dài hạn (`postgres`, `backend`, `backend-small-production`, `frontend`, `kong`, `loki`, `tempo`, `promtail`, `grafana`, `sandbox`) và thêm regression test đọc `compose.yaml` để giữ nguyên contract này, trong khi vẫn để các job một lần (`migrate`, `init-dev-secrets`, `seed-demo`, `init-kong-logs`) không có restart policy."
verification: "`docker compose config -q` pass. Targeted static gateway/observability tests pass khi mount đầy đủ repo root vào test container (`9 passed`). Sau `docker compose up --wait --force-recreate --no-build ...`, `docker inspect` xác nhận `restart=unless-stopped` cho `grafana`, `backend`, và `kong`; `http://localhost:3001/api/health` trả Grafana health JSON và `http://localhost:8000/health` trả `{\"status\":\"alive\"}`."
files_changed:
  - "E:\\Dữ liệu ổ D\\Tài liệu\\MMH\\Simpagent\\compose.yaml"
  - "E:\\Dữ liệu ổ D\\Tài liệu\\MMH\\Simpagent\\backend\\tests\\integration\\gateway\\test_production_profile.py"
  - "E:\\Dữ liệu ổ D\\Tài liệu\\MMH\\Simpagent\\.planning\\debug\\stack-does-not-auto-recover.md"
