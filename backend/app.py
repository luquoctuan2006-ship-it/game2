"""PawHabit backend – FastAPI + SQLAlchemy (SQLite mặc định, Postgres qua DATABASE_URL)."""
import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import (Boolean, Column, Float, ForeignKey, Integer, String,
                        UniqueConstraint, create_engine, func)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from . import rules as R
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pawhabit.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS")
WEB_DIR = Path(os.getenv("WEB_DIR", Path(__file__).resolve().parent.parent / "game" / "build" / "web"))

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()


# ----------------------------------------------------------------- models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(24), unique=True, index=True, nullable=False)
    pw_hash = Column(String(200), nullable=False)
    role = Column(String(10), default="user")
    banned = Column(Boolean, default=False)
    created = Column(Float, default=time.time)


class Pet(Base):
    __tablename__ = "pets"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    name = Column(String(16), nullable=False)
    breed = Column(String(20), nullable=False)
    coins = Column(Integer, default=0)
    xp = Column(Integer, default=0)
    hunger = Column(Float, default=80)
    happy = Column(Float, default=80)
    energy = Column(Float, default=80)
    clean = Column(Float, default=80)
    updated = Column(Float, default=time.time)
    streak = Column(Integer, default=0)
    best_streak = Column(Integer, default=0)
    last_active = Column(String(10), nullable=True)
    total_done = Column(Integer, default=0)
    accessory = Column(String(16), default="")
    last_complete_ts = Column(Float, default=0)


class Habit(Base):
    __tablename__ = "habits"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title = Column(String(40), nullable=False)
    kind = Column(String(8), default="daily")  # daily | weekly
    reminder_hour = Column(Integer, nullable=True)
    active = Column(Boolean, default=True)
    created = Column(Float, default=time.time)


class HabitLog(Base):
    __tablename__ = "habit_logs"
    id = Column(Integer, primary_key=True)
    habit_id = Column(Integer, ForeignKey("habits.id", ondelete="CASCADE"), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    day = Column(String(10), index=True)
    week = Column(String(8), index=True)
    ts = Column(Float, default=time.time)
    rewarded = Column(Boolean, default=True)


class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    item_id = Column(String(16))
    qty = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint("user_id", "item_id"),)


class Action(Base):
    __tablename__ = "actions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind = Column(String(10))
    day = Column(String(10))
    week = Column(String(8))


class QuestClaim(Base):
    __tablename__ = "quest_claims"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    quest_id = Column(String(16))
    period = Column(String(10))
    __table_args__ = (UniqueConstraint("user_id", "quest_id", "period"),)


# ----------------------------------------------------------------- helpers
def now_local():
    return dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=R.TZ_OFFSET_HOURS)


def today_str():
    return now_local().date().isoformat()


def week_str(d=None):
    d = d or now_local().date()
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def hash_pw(pw, salt=None):
    salt = salt or secrets.token_hex(8)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${h}"


def check_pw(pw, stored):
    salt, _ = stored.split("$", 1)
    return hmac.compare_digest(hash_pw(pw, salt), stored)


def make_token(uid, ttl=7 * 86400):
    body = base64.urlsafe_b64encode(json.dumps({"u": uid, "e": int(time.time() + ttl)}).encode()).decode()
    sig = hmac.new(SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def read_token(tok):
    try:
        body, sig = tok.split(".")
        good = hmac.new(SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, good):
            return None
        data = json.loads(base64.urlsafe_b64decode(body.encode()))
        return data["u"] if data["e"] > time.time() else None
    except Exception:
        return None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    uid = read_token(authorization.replace("Bearer ", "")) if authorization else None
    user = db.get(User, uid) if uid else None
    if not user:
        raise HTTPException(401, "Phiên đăng nhập hết hạn, hãy đăng nhập lại")
    if user.banned:
        raise HTTPException(403, "Tài khoản đã bị khoá")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Chỉ admin mới được phép")
    return user


_fails = {}


def rate_limit(key):
    now = time.time()
    lst = [t for t in _fails.get(key, []) if now - t < 300]
    _fails[key] = lst
    if len(lst) >= 6:
        raise HTTPException(429, "Sai quá nhiều lần, thử lại sau 5 phút")


# ----------------------------------------------------------------- pet logic
def refresh_pet(db, pet):
    """Áp dụng suy giảm chỉ số theo thời gian + reset streak nếu bỏ lỡ."""
    now = time.time()
    hours = min((now - (pet.updated or now)) / 3600.0, 48)
    if hours > 0:
        for k, rate in R.DECAY_PER_HOUR.items():
            v = getattr(pet, k) - rate * hours
            if k == "happy" and pet.hunger < 20:
                v -= 1.0 * hours
            setattr(pet, k, R.clamp(v))
        pet.updated = now
    today = now_local().date()
    if pet.last_active and pet.streak:
        gap = (today - dt.date.fromisoformat(pet.last_active)).days
        if gap > 1:
            pet.streak = 0
    db.flush()


def pet_dict(pet):
    p = {k: round(getattr(pet, k), 1) for k in ("hunger", "happy", "energy", "clean")}
    care = sum(p.values()) / 4
    score = R.evo_score(pet.total_done, pet.streak, care)
    stage, stage_name = R.stage_of(score)
    lvl, cur, need = R.level_of(pet.xp)
    return {
        "name": pet.name, "breed": pet.breed, "breed_name": R.BREEDS.get(pet.breed, pet.breed),
        **p, "coins": pet.coins, "xp": pet.xp, "level": lvl, "xp_cur": cur, "xp_need": need,
        "streak": pet.streak, "best_streak": pet.best_streak, "total_done": pet.total_done,
        "accessory": pet.accessory or "", "mood": R.mood_of(p),
        "evo_score": score, "stage": stage, "stage_name": stage_name,
        "next_stage_at": next((t for t, _ in R.STAGES if t > score), None),
    }


def inv_dict(db, uid):
    return {i.item_id: i.qty for i in db.query(Inventory).filter_by(user_id=uid) if i.qty > 0}


def add_item(db, uid, item_id, n=1):
    row = db.query(Inventory).filter_by(user_id=uid, item_id=item_id).first()
    if row:
        row.qty += n
    else:
        db.add(Inventory(user_id=uid, item_id=item_id, qty=n))


def log_action(db, uid, kind):
    db.add(Action(user_id=uid, kind=kind, day=today_str(), week=week_str()))


def quest_progress(db, user, pet, habits):
    day, wk = today_str(), week_str()
    out = []
    daily_active = [h for h in habits if h.kind == "daily"]
    for q in R.QUESTS:
        period_key = day if q["period"] == "daily" else wk
        col = HabitLog.day if q["period"] == "daily" else HabitLog.week
        src, target = q["src"], q["target"]
        if src == "habits":
            prog = db.query(func.count(HabitLog.id)).filter(HabitLog.user_id == user.id, col == period_key).scalar()
        elif src == "allhabits":
            target = max(1, len(daily_active))
            ids = [h.id for h in daily_active]
            prog = db.query(func.count(func.distinct(HabitLog.habit_id))).filter(
                HabitLog.user_id == user.id, HabitLog.day == day, HabitLog.habit_id.in_(ids or [-1])).scalar()
        elif src == "streak":
            prog = pet.streak
        else:
            kind = src.split(":")[1]
            acol = Action.day if q["period"] == "daily" else Action.week
            prog = db.query(func.count(Action.id)).filter(Action.user_id == user.id, Action.kind == kind, acol == period_key).scalar()
        claimed = db.query(QuestClaim).filter_by(user_id=user.id, quest_id=q["id"], period=period_key).first() is not None
        out.append({"id": q["id"], "period": q["period"], "title": q["title"], "progress": min(prog, target),
                    "target": target, "coins": q["coins"], "xp": q["xp"], "claimed": claimed,
                    "ready": prog >= target and not claimed and not (src == "allhabits" and not daily_active)})
    return out


def build_state(db, user):
    pet = db.get(Pet, user.id)
    now = now_local()
    state = {"user": {"id": user.id, "username": user.username, "role": user.role},
             "server": {"day": today_str(), "hour": now.hour, "minute": now.minute},
             "pet": None, "habits": [], "inventory": {}, "quests": []}
    if not pet:
        return state
    refresh_pet(db, pet)
    habits = db.query(Habit).filter_by(user_id=user.id, active=True).order_by(Habit.id).all()
    day, wk = today_str(), week_str()
    done_ids = {l.habit_id for l in db.query(HabitLog).filter(HabitLog.user_id == user.id, HabitLog.day == day)}
    week_ids = {l.habit_id for l in db.query(HabitLog).filter(HabitLog.user_id == user.id, HabitLog.week == wk)}
    state["habits"] = [{"id": h.id, "title": h.title, "kind": h.kind, "reminder_hour": h.reminder_hour,
                        "done": (h.id in done_ids) if h.kind == "daily" else (h.id in week_ids)} for h in habits]
    state["pet"] = pet_dict(pet)
    state["inventory"] = inv_dict(db, user.id)
    state["quests"] = quest_progress(db, user, pet, habits)
    db.commit()
    return state


# ----------------------------------------------------------------- schemas
class Cred(BaseModel):
    username: str = Field(min_length=3, max_length=24, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=6, max_length=64)


class PetIn(BaseModel):
    name: str = Field(min_length=1, max_length=16)
    breed: str


class HabitIn(BaseModel):
    title: str = Field(min_length=1, max_length=40)
    kind: str = Field(default="daily", pattern="^(daily|weekly)$")
    reminder_hour: int | None = Field(default=None, ge=0, le=23)


class ItemIn(BaseModel):
    item_id: str


class RoleIn(BaseModel):
    role: str = Field(pattern="^(user|admin)$")


# ----------------------------------------------------------------- app
app = FastAPI(title="PawHabit API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.query(User).filter_by(username=ADMIN_USER).first():
            db.add(User(username=ADMIN_USER, pw_hash=hash_pw(ADMIN_PASS), role="admin"))
            db.commit()


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/auth/register")
def register(c: Cred, db: Session = Depends(get_db)):
    if db.query(User).filter(func.lower(User.username) == c.username.lower()).first():
        raise HTTPException(409, "Tên đăng nhập đã tồn tại")
    u = User(username=c.username, pw_hash=hash_pw(c.password))
    db.add(u)
    db.commit()
    return {"token": make_token(u.id), "username": u.username, "role": u.role}


@app.post("/api/auth/login")
def login(c: Cred, db: Session = Depends(get_db)):
    rate_limit(c.username.lower())
    u = db.query(User).filter(func.lower(User.username) == c.username.lower()).first()
    if not u or not check_pw(c.password, u.pw_hash):
        _fails.setdefault(c.username.lower(), []).append(time.time())
        raise HTTPException(401, "Sai tên đăng nhập hoặc mật khẩu")
    if u.banned:
        raise HTTPException(403, "Tài khoản đã bị khoá")
    return {"token": make_token(u.id), "username": u.username, "role": u.role}


@app.get("/api/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"state": build_state(db, user)}


@app.post("/api/pet")
def create_pet(p: PetIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    pet = db.get(Pet, user.id)
    name = p.name.strip()
    if not name:
        raise HTTPException(422, "Tên thú không được để trống")
    if pet:
        pet.name = name
    else:
        if p.breed not in R.BREEDS:
            raise HTTPException(422, "Giống chó không hợp lệ")
        db.add(Pet(user_id=user.id, name=name, breed=p.breed, coins=R.STARTER_COINS))
        for k, n in R.STARTER_ITEMS.items():
            add_item(db, user.id, k, n)
    db.commit()
    return {"state": build_state(db, user)}


@app.post("/api/habits")
def add_habit(h: HabitIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if db.query(func.count(Habit.id)).filter_by(user_id=user.id, active=True).scalar() >= R.MAX_ACTIVE_HABITS:
        raise HTTPException(400, f"Tối đa {R.MAX_ACTIVE_HABITS} thói quen")
    title = h.title.strip()
    if not title:
        raise HTTPException(422, "Tên thói quen trống")
    db.add(Habit(user_id=user.id, title=title, kind=h.kind, reminder_hour=h.reminder_hour))
    db.commit()
    return {"state": build_state(db, user)}


@app.delete("/api/habits/{hid}")
def del_habit(hid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    h = db.query(Habit).filter_by(id=hid, user_id=user.id, active=True).first()
    if not h:
        raise HTTPException(404, "Không tìm thấy thói quen")
    h.active = False  # giữ log để thống kê không bị mất, và không thể xoá-tạo lại để farm thưởng
    db.commit()
    return {"state": build_state(db, user)}


@app.post("/api/habits/{hid}/complete")
def complete(hid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    pet = db.get(Pet, user.id)
    h = db.query(Habit).filter_by(id=hid, user_id=user.id, active=True).first()
    if not pet or not h:
        raise HTTPException(404, "Không tìm thấy thói quen")
    now = time.time()
    if now - (pet.last_complete_ts or 0) < R.COMPLETE_COOLDOWN:
        raise HTTPException(429, "Thao tác quá nhanh, chờ một chút")
    refresh_pet(db, pet)
    day, wk = today_str(), week_str()
    q = db.query(HabitLog).filter(HabitLog.habit_id == h.id)
    q = q.filter(HabitLog.day == day) if h.kind == "daily" else q.filter(HabitLog.week == wk)
    if q.first():
        raise HTTPException(409, "Bạn đã hoàn thành thói quen này rồi")
    rewarded_today = db.query(func.count(HabitLog.id)).filter_by(user_id=user.id, day=day, rewarded=True).scalar()
    reward = rewarded_today < R.DAILY_REWARD_CAP
    db.add(HabitLog(habit_id=h.id, user_id=user.id, day=day, week=wk, ts=now, rewarded=reward))
    pet.last_complete_ts = now
    pet.total_done += 1
    # streak
    today = now_local().date()
    if pet.last_active != today.isoformat():
        if pet.last_active and (today - dt.date.fromisoformat(pet.last_active)).days == 1:
            pet.streak += 1
        else:
            pet.streak = 1
        pet.last_active = today.isoformat()
        pet.best_streak = max(pet.best_streak, pet.streak)
    coins = xp = 0
    if reward:
        mult = R.WEEKLY_MULTIPLIER if h.kind == "weekly" else 1
        coins = (R.HABIT_REWARD_COINS + min(pet.streak, R.STREAK_BONUS_CAP) * R.STREAK_BONUS_PER_DAY) * mult
        xp = R.HABIT_REWARD_XP * mult
        pet.coins += coins
        pet.xp += xp
        pet.happy = R.clamp(pet.happy + 5)
    db.commit()
    return {"state": build_state(db, user), "reward": {"coins": coins, "xp": xp, "capped": not reward}}


@app.get("/api/shop")
def shop():
    return {"items": [{"id": k, "name": v["name"], "kind": v["kind"], "price": v["price"], "eff": v.get("eff", {})}
                      for k, v in R.ITEMS.items()]}


@app.post("/api/shop/buy")
def buy(i: ItemIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    pet, item = db.get(Pet, user.id), R.ITEMS.get(i.item_id)
    if not pet or not item:
        raise HTTPException(404, "Vật phẩm không tồn tại")
    if item["kind"] == "acc" and inv_dict(db, user.id).get(i.item_id):
        raise HTTPException(409, "Bạn đã sở hữu phụ kiện này")
    if pet.coins < item["price"]:
        raise HTTPException(402, "Không đủ coin")
    pet.coins -= item["price"]
    add_item(db, user.id, i.item_id)
    db.commit()
    return {"state": build_state(db, user)}


@app.post("/api/inventory/use")
def use_item(i: ItemIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    pet, item = db.get(Pet, user.id), R.ITEMS.get(i.item_id)
    if not pet or not item or item["kind"] == "acc":
        raise HTTPException(404, "Không dùng được vật phẩm này")
    row = db.query(Inventory).filter_by(user_id=user.id, item_id=i.item_id).first()
    if not row or row.qty < 1:
        raise HTTPException(400, "Hết vật phẩm")
    refresh_pet(db, pet)
    row.qty -= 1
    for stat, delta in item["eff"].items():
        setattr(pet, stat, R.clamp(getattr(pet, stat) + delta))
    log_action(db, user.id, R.ACTION_FOR_KIND[item["kind"]])
    db.commit()
    return {"state": build_state(db, user), "used": i.item_id}


@app.post("/api/inventory/equip")
def equip(i: ItemIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    pet, item = db.get(Pet, user.id), R.ITEMS.get(i.item_id)
    if not pet or not item or item["kind"] != "acc" or not inv_dict(db, user.id).get(i.item_id):
        raise HTTPException(400, "Không thể trang bị")
    pet.accessory = "" if pet.accessory == i.item_id else i.item_id
    db.commit()
    return {"state": build_state(db, user)}


@app.post("/api/quests/{qid}/claim")
def claim(qid: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    pet = db.get(Pet, user.id)
    habits = db.query(Habit).filter_by(user_id=user.id, active=True).all()
    q = next((x for x in quest_progress(db, user, pet, habits) if x["id"] == qid), None) if pet else None
    if not q:
        raise HTTPException(404, "Không có nhiệm vụ này")
    if not q["ready"]:
        raise HTTPException(400, "Chưa đủ điều kiện nhận thưởng")
    period = today_str() if q["period"] == "daily" else week_str()
    db.add(QuestClaim(user_id=user.id, quest_id=qid, period=period))
    pet.coins += q["coins"]
    pet.xp += q["xp"]
    db.commit()
    return {"state": build_state(db, user), "reward": {"coins": q["coins"], "xp": q["xp"]}}


@app.get("/api/stats")
def stats(user: User = Depends(current_user), db: Session = Depends(get_db)):
    pet = db.get(Pet, user.id)
    today = now_local().date()
    days = [(today - dt.timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    counts = dict(db.query(HabitLog.day, func.count(HabitLog.id)).filter(
        HabitLog.user_id == user.id, HabitLog.day.in_(days)).group_by(HabitLog.day).all())
    per = []
    for h in db.query(Habit).filter_by(user_id=user.id, active=True):
        n = db.query(func.count(HabitLog.id)).filter(HabitLog.habit_id == h.id, HabitLog.day >= days[0]).scalar()
        per.append({"title": h.title, "kind": h.kind, "count7": n})
    return {"days": days, "counts": [counts.get(d, 0) for d in days], "per_habit": per,
            "total": pet.total_done if pet else 0, "best_streak": pet.best_streak if pet else 0}


@app.get("/api/leaderboard")
def leaderboard(by: str = "xp", db: Session = Depends(get_db), user: User = Depends(current_user)):
    col = Pet.streak if by == "streak" else Pet.xp
    rows = (db.query(Pet, User).join(User, User.id == Pet.user_id)
            .filter(User.banned == False).order_by(col.desc(), Pet.total_done.desc()).limit(20).all())  # noqa: E712
    out = []
    for rank, (p, u) in enumerate(rows, 1):
        d = pet_dict(p)
        out.append({"rank": rank, "username": u.username, "pet": p.name, "breed": p.breed, "xp": p.xp,
                    "level": d["level"], "streak": p.streak, "stage": d["stage"], "stage_name": d["stage_name"],
                    "accessory": p.accessory or "", "me": u.id == user.id})
    return {"by": by, "rows": out}


# ------------------------------------------------------------- admin
@app.get("/api/admin/users")
def admin_users(_: User = Depends(admin_user), db: Session = Depends(get_db)):
    rows = db.query(User, Pet).outerjoin(Pet, Pet.user_id == User.id).order_by(User.id).all()
    return {"users": [{"id": u.id, "username": u.username, "role": u.role, "banned": bool(u.banned),
                       "pet": p.name if p else "-", "xp": p.xp if p else 0} for u, p in rows]}


def _target(db, uid, admin):
    t = db.get(User, uid)
    if not t:
        raise HTTPException(404, "Không có user")
    if t.id == admin.id:
        raise HTTPException(400, "Không thể thao tác trên chính mình")
    return t


@app.post("/api/admin/users/{uid}/ban")
def admin_ban(uid: int, a: User = Depends(admin_user), db: Session = Depends(get_db)):
    t = _target(db, uid, a)
    t.banned = not t.banned
    db.commit()
    return admin_users(a, db)


@app.post("/api/admin/users/{uid}/role")
def admin_role(uid: int, r: RoleIn, a: User = Depends(admin_user), db: Session = Depends(get_db)):
    t = _target(db, uid, a)
    t.role = r.role
    db.commit()
    return admin_users(a, db)


@app.delete("/api/admin/users/{uid}")
def admin_delete(uid: int, a: User = Depends(admin_user), db: Session = Depends(get_db)):
    t = _target(db, uid, a)
    for M in (QuestClaim, Action, Inventory, HabitLog, Habit, Pet):
        db.query(M).filter_by(user_id=t.id).delete()
    db.delete(t)
    db.commit()
    return admin_users(a, db)


# ------------------------------------------------------------- static web build (cùng origin => không lỗi CORS)
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
