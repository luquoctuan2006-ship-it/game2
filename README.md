# PawHabit – Game nuôi thú ảo + Habit Tracker (pygame)

Cấu trúc: `game/` (client pygame, build web bằng pygbag), `backend/` (FastAPI + SQLAlchemy).

## Chạy thử trên máy
    pip install -r requirements-dev.txt
    python -m uvicorn backend.app:app --port 8000        # terminal 1
    cd game && python main.py                  # terminal 2 (cua so pygame)
Test backend: `python -m backend.test_api`
Admin mặc định: admin / admin123 (đổi bằng biến ADMIN_PASS).

## Build web + deploy
    python -m pygbag --build game              # ra game/build/web
    WEB_DIR=game/build/web uvicorn backend.app:app --port 8000
Deploy: đẩy repo lên GitHub, tạo Web Service kiểu Docker trên Render/Railway/Fly (có sẵn Dockerfile, render.yaml).
Đặt biến môi trường: SECRET_KEY, ADMIN_PASS, (tuỳ chọn) DATABASE_URL=Postgres.

## Lưu ý
- Phần gọi mạng trên web (fetch qua platform.window.eval) chưa được thử trong trình duyệt thật.
- Nhập tiếng Việt có dấu bằng bộ gõ trong trình duyệt có thể không hoạt động.
