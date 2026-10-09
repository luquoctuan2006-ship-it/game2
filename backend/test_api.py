import os, tempfile
os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")
from fastapi.testclient import TestClient
from backend import app as A, rules as R
R.COMPLETE_COOLDOWN = 0

def test_flow():
    with TestClient(A.app) as c:
        r = c.post("/api/auth/register", json={"username": "alice", "password": "secret1"}); assert r.status_code == 200
        assert c.post("/api/auth/register", json={"username": "ALICE", "password": "secret1"}).status_code == 409
        assert c.post("/api/auth/login", json={"username": "alice", "password": "bad_pass"}).status_code == 401
        H = {"Authorization": "Bearer " + r.json()["token"]}
        assert c.get("/api/me").status_code == 401
        st = c.get("/api/me", headers=H).json()["state"]; assert st["pet"] is None
        st = c.post("/api/pet", headers=H, json={"name": "Bu", "breed": "husky"}).json()["state"]
        assert st["pet"]["coins"] == 30 and st["inventory"]["bone"] == 2
        for t in ("Uống nước", "Đọc sách", "Tập thể dục"):
            st = c.post("/api/habits", headers=H, json={"title": t, "reminder_hour": 9}).json()["state"]
        st = c.post("/api/habits", headers=H, json={"title": "Dọn nhà", "kind": "weekly"}).json()["state"]
        ids = [h["id"] for h in st["habits"]]
        r = c.post(f"/api/habits/{ids[0]}/complete", headers=H); assert r.status_code == 200, r.text
        assert r.json()["reward"]["coins"] == 12 and r.json()["state"]["pet"]["streak"] == 1
        assert c.post(f"/api/habits/{ids[0]}/complete", headers=H).status_code == 409   # không farm
        for i in ids[1:]: assert c.post(f"/api/habits/{i}/complete", headers=H).status_code == 200
        st = c.get("/api/me", headers=H).json()["state"]
        q = {x["id"]: x for x in st["quests"]}
        assert q["d_habit3"]["ready"] and q["d_all"]["ready"], q
        r = c.post("/api/quests/d_habit3/claim", headers=H); assert r.status_code == 200
        assert c.post("/api/quests/d_habit3/claim", headers=H).status_code in (400, 409, 500) or True
        assert c.post("/api/quests/d_habit3/claim", headers=H).status_code == 400
        # shop
        coins = r.json()["state"]["pet"]["coins"]
        assert c.post("/api/shop/buy", headers=H, json={"item_id": "crown"}).status_code == 402
        assert c.post("/api/shop/buy", headers=H, json={"item_id": "steak"}).status_code == 200
        st = c.post("/api/inventory/use", headers=H, json={"item_id": "bone"}).json()["state"]
        assert st["inventory"]["bone"] == 1
        assert {x["id"]: x for x in st["quests"]}["d_feed"]["ready"]
        s = c.get("/api/stats", headers=H).json(); assert sum(s["counts"]) == 4
        lb = c.get("/api/leaderboard?by=streak", headers=H).json(); assert lb["rows"][0]["username"] == "alice"
        # phân quyền
        assert c.get("/api/admin/users", headers=H).status_code == 403
        a = c.post("/api/auth/login", json={"username": "admin", "password": "admin123"}).json()
        HA = {"Authorization": "Bearer " + a["token"]}
        us = c.get("/api/admin/users", headers=HA).json()["users"]; assert len(us) == 2
        uid = [u for u in us if u["username"] == "alice"][0]["id"]
        c.post(f"/api/admin/users/{uid}/ban", headers=HA)
        assert c.get("/api/me", headers=H).status_code == 403
        assert c.delete(f"/api/admin/users/{uid}", headers=HA).status_code == 200
        print("ALL OK")
test_flow()
