"""Luật chơi / game economy – nằm hoàn toàn ở server để chống gian lận."""

TZ_OFFSET_HOURS = 7  # giờ Việt Nam

BREEDS = {
    "golden": "Golden Retriever",
    "akita": "Akita",
    "great_dane": "Great Dane",
    "schnauzer": "Schnauzer",
    "saint_bernard": "Saint Bernard",
    "husky": "Siberian Husky",
}

# kind: food/toy/soap/bed (tiêu hao) hoặc acc (phụ kiện vĩnh viễn)
ITEMS = {
    "bone":    {"name": "Khúc xương",   "kind": "food", "price": 15,  "eff": {"hunger": 22, "happy": 3}},
    "steak":   {"name": "Bít tết",      "kind": "food", "price": 35,  "eff": {"hunger": 50, "happy": 8}},
    "treat":   {"name": "Bánh thưởng",  "kind": "food", "price": 10,  "eff": {"hunger": 8, "happy": 12}},
    "ball":    {"name": "Bóng tennis",  "kind": "toy",  "price": 20,  "eff": {"happy": 28, "energy": -8}},
    "frisbee": {"name": "Đĩa bay",      "kind": "toy",  "price": 30,  "eff": {"happy": 40, "energy": -12}},
    "soap":    {"name": "Xà phòng",     "kind": "soap", "price": 15,  "eff": {"clean": 45, "happy": -2}},
    "bed":     {"name": "Giường ngủ",   "kind": "bed",  "price": 25,  "eff": {"energy": 45}},
    "bandana": {"name": "Khăn đỏ",      "kind": "acc",  "price": 80},
    "glasses": {"name": "Kính râm",     "kind": "acc",  "price": 120},
    "bow":     {"name": "Nơ hồng",      "kind": "acc",  "price": 100},
    "crown":   {"name": "Vương miện",   "kind": "acc",  "price": 250},
}

ACTION_FOR_KIND = {"food": "feed", "toy": "play", "soap": "bathe", "bed": "rest"}

STARTER_ITEMS = {"bone": 2, "ball": 1, "soap": 1, "bed": 1}
STARTER_COINS = 30

# stage theo điểm tiến hoá
STAGES = [(0, "Cún con"), (40, "Thiếu niên"), (150, "Trưởng thành"), (400, "Huyền thoại")]

HABIT_REWARD_COINS = 10
HABIT_REWARD_XP = 15
STREAK_BONUS_PER_DAY = 2     # coin mỗi ngày streak
STREAK_BONUS_CAP = 10
WEEKLY_MULTIPLIER = 2
DAILY_REWARD_CAP = 15        # số lần nhận thưởng tối đa / ngày
COMPLETE_COOLDOWN = 2.0      # giây
MAX_ACTIVE_HABITS = 12

DECAY_PER_HOUR = {"hunger": 3.0, "happy": 2.0, "energy": 1.5, "clean": 1.5}

# Nhiệm vụ: kind=daily|weekly; src: habits | action:<x> | allhabits | streak
QUESTS = [
    {"id": "d_habit3", "period": "daily",  "title": "Hoàn thành 3 thói quen",       "src": "habits",       "target": 3, "coins": 25,  "xp": 20},
    {"id": "d_all",    "period": "daily",  "title": "Làm hết thói quen hằng ngày",  "src": "allhabits",    "target": 0, "coins": 40,  "xp": 30},
    {"id": "d_feed",   "period": "daily",  "title": "Cho thú ăn 1 lần",             "src": "action:feed",  "target": 1, "coins": 10,  "xp": 5},
    {"id": "d_play",   "period": "daily",  "title": "Chơi với thú 1 lần",           "src": "action:play",  "target": 1, "coins": 10,  "xp": 5},
    {"id": "w_habit15", "period": "weekly", "title": "Hoàn thành 15 thói quen",     "src": "habits",       "target": 15, "coins": 100, "xp": 80},
    {"id": "w_streak5", "period": "weekly", "title": "Giữ streak 5 ngày",           "src": "streak",       "target": 5, "coins": 80,  "xp": 60},
    {"id": "w_bathe3",  "period": "weekly", "title": "Tắm cho thú 3 lần",           "src": "action:bathe", "target": 3, "coins": 60,  "xp": 40},
]


def clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))


def mood_of(p):
    avg = (p["hunger"] + p["happy"] + p["energy"] + p["clean"]) / 4
    low = min(p["hunger"], p["happy"], p["energy"], p["clean"])
    if low < 8 or avg < 25:
        return "sick"
    if avg < 45:
        return "sad"
    if avg < 72:
        return "normal"
    return "happy"


def evo_score(total_done, streak, avg_care):
    return int(total_done * 2 + streak * 5 + avg_care / 5)


def stage_of(score):
    idx = 0
    for i, (th, _n) in enumerate(STAGES):
        if score >= th:
            idx = i
    return idx, STAGES[idx][1]


def level_of(xp):
    lvl = 1
    need = 50
    while xp >= need:
        xp -= need
        lvl += 1
        need = int(need * 1.25)
    return lvl, xp, need
