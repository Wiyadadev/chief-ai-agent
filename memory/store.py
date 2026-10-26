from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import datetime
import urllib.request
import urllib.parse

load_dotenv()

# ============================================================
# MEMORY STORE — โฟลเดอร์ data/ ไฟล์ละ 1 เรื่อง (memory/ เป็นแพ็กเกจโค้ด ไม่ใช่ที่เก็บข้อมูลแล้ว)
# ============================================================
MEMORY_DIR = "data"

MEMORY_FILES = {
    "company":       "company.json",
    "owner":         "profile.json",
    "current_state": "current_state.json",
    "projects":      "projects.json",
    "conversations": "conversations.json",
    "clients":       "clients.json",
    "tasks":         "tasks.json",
    "decisions":     "decisions.json",
    "knowledge":     "knowledge.json",
    "workflows":     "workflows.json",
    "agents":        "agents.json",
    "settings":      "settings.json",
    "rocks":         "rocks.json",
    "scorecard":     "scorecard.json",
    "issues":        "issues.json",
    "calendar":      "calendar.json",
    "timeline":      "timeline.json",
    "preferences":   "preferences.json",
}

def _mpath(key):
    return os.path.join(MEMORY_DIR, MEMORY_FILES[key])

def mem_load(key, default):
    path = _mpath(key)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def mem_save(key, data):
    os.makedirs(MEMORY_DIR, exist_ok=True)
    with open(_mpath(key), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============================================================
# DEFAULT AGENTS (ใช้ตอน migrate ครั้งแรก หรือถ้า memory/agents.json หาย)
# ============================================================
DEFAULT_AGENTS = {
    "engineering": {"name": "Engineering", "role": "ดูแลเรื่องเทคนิค ระบบ โค้ด สถาปัตยกรรม และความเป็นไปได้ทางเทคนิคของไอเดีย"},
    "sales":       {"name": "Sales",       "role": "ดูแลเรื่องการขาย การปิดดีล ลูกค้า และกลยุทธ์สร้างรายได้"},
    "marketing":   {"name": "Marketing",   "role": "ดูแลเรื่องการตลาด แบรนด์ การโปรโมท และคอนเทนต์เพื่อเข้าถึงลูกค้า"},
    "finance":     {"name": "Finance",     "role": "ดูแลเรื่องการเงิน งบประมาณ ต้นทุน และความคุ้มค่าการลงทุน"},
    "project":     {"name": "Project",     "role": "ดูแลเรื่องบริหารโปรเจกต์ timeline milestone และการจัดลำดับความสำคัญของงาน"},
    "analytics":   {"name": "Analytics",   "role": "ดูแลเรื่องวิเคราะห์ข้อมูล ตัวเลข metrics และ insight เชิงลึก"},
    "security":    {"name": "Security",    "role": "ดูแลเรื่องความปลอดภัยของระบบ ข้อมูล และความเสี่ยงที่อาจเกิดขึ้น"},
    "research":    {"name": "Research",    "role": "ดูแลเรื่องค้นคว้าข้อมูล งานวิจัย และแนวโน้มตลาด/เทคโนโลยีใหม่ๆ"},
    "workflow":    {"name": "Workflow",    "role": "ดูแลเรื่องกระบวนการทำงาน automation และ SOP ให้ทีมทำงานลื่นไหล"},
}

# ============================================================
# MIGRATION — ย้ายของเก่า (memory.json, goals.json, tasks.json, session_history.json)
# เข้า data/ ให้อัตโนมัติ ทำครั้งเดียว (ถ้ามีโฟลเดอร์ data/ อยู่แล้วจะข้าม)
# ============================================================
def migrate_legacy_files():
    if os.path.isdir(MEMORY_DIR):
        return

    old_memory = {}
    if os.path.exists("memory.json"):
        with open("memory.json", "r", encoding="utf-8") as f:
            old_memory = json.load(f)

    old_goals = []
    if os.path.exists("goals.json"):
        with open("goals.json", "r", encoding="utf-8") as f:
            old_goals = json.load(f)

    old_tasks = []
    if os.path.exists("tasks.json"):
        with open("tasks.json", "r", encoding="utf-8") as f:
            old_tasks = json.load(f)

    old_history = []
    if os.path.exists("session_history.json"):
        with open("session_history.json", "r", encoding="utf-8") as f:
            old_history = json.load(f)

    mem_save("owner", {
        "name": old_memory.get("owner", "Owner"),
        "role": "CEO",
        "goal": old_memory.get("goal", "")
    })
    mem_save("company", {
        "name": old_memory.get("project", "My Company"),
        "mission": "",
        "industry": ""
    })
    mem_save("current_state", {
        "active_goals": old_goals,
        "focus": "",
        "last_updated": datetime.datetime.now().isoformat()
    })
    mem_save("projects", [])
    mem_save("conversations", old_history)
    mem_save("clients", [])
    mem_save("tasks", old_tasks)
    mem_save("decisions", [])
    mem_save("knowledge", [])
    mem_save("workflows", [])
    mem_save("agents", DEFAULT_AGENTS)
    mem_save("settings", {
        "model": "gpt-4.1-mini",
        "stale_days_threshold": 2,
        "history_context_window": 20
    })
    mem_save("rocks", [])
    mem_save("scorecard", [])
    mem_save("issues", [])
    mem_save("calendar", [])
    mem_save("timeline", [])
    mem_save("preferences", {})

    print("📦 ย้ายข้อมูลเก่าเข้าโฟลเดอร์ data/ เรียบร้อยแล้ว (ไฟล์เดิมยังอยู่ ลบเองได้ทีหลังถ้าเช็คแล้วโอเค)")

migrate_legacy_files()

def migrate_old_memory_folder():
    """เดิมโฟลเดอร์เก็บข้อมูลชื่อ memory/ แต่ตอนนี้ memory/ กลายเป็นแพ็กเกจโค้ด (มี store.py) แล้ว
    ข้อมูลจริงต้องย้ายไปอยู่ data/ แทน — ทำครั้งเดียว ถ้ายังไม่เคยย้าย"""
    old_dir = "memory"
    if os.path.isdir(MEMORY_DIR):
        return  # data/ มีอยู่แล้ว ย้ายไปแล้ว ไม่ต้องทำซ้ำ
    if not os.path.isdir(old_dir):
        return
    moved_any = False
    # เช็คทั้งชื่อไฟล์ปัจจุบันและชื่อเก่าก่อนเปลี่ยนชื่อ (owner.json/contacts.json)
    candidates = dict(MEMORY_FILES)
    legacy_names = {"owner": "owner.json", "clients": "contacts.json"}
    for key, filename in candidates.items():
        for fname in {filename, legacy_names.get(key, filename)}:
            old_path = os.path.join(old_dir, fname)
            if os.path.exists(old_path):
                with open(old_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                mem_save(key, data)
                moved_any = True
                break
    if moved_any:
        print("📦 ย้ายข้อมูลจากโฟลเดอร์ memory/ เดิม → data/ เรียบร้อยแล้ว (memory/ ตอนนี้เป็นโค้ดล้วนแล้ว)")

migrate_old_memory_folder()

def migrate_renamed_files():
    """เคยเปลี่ยนชื่อไฟล์ (owner.json -> profile.json, contacts.json -> clients.json) — ย้ายข้อมูลให้อัตโนมัติถ้ายังไม่เคยย้าย ไม่ให้ของเดิมหาย"""
    if not os.path.isdir(MEMORY_DIR):
        return
    renames = [("owner.json", "owner"), ("contacts.json", "clients")]
    for old_filename, new_key in renames:
        old_path = os.path.join(MEMORY_DIR, old_filename)
        new_path = _mpath(new_key)
        if os.path.exists(old_path) and not os.path.exists(new_path):
            with open(old_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            mem_save(new_key, data)
            print(f"📦 ย้าย {old_filename} → {MEMORY_FILES[new_key]} เรียบร้อยแล้ว")

migrate_renamed_files()

owner = mem_load("owner", {"name": "Owner", "role": "CEO", "goal": ""})
company = mem_load("company", {"name": "My Company", "mission": "", "industry": ""})
settings = mem_load("settings", {"model": "gpt-4.1-mini", "stale_days_threshold": 2, "history_context_window": 20})
DEPARTMENTS = mem_load("agents", DEFAULT_AGENTS)

MODEL = settings.get("model", "gpt-4.1-mini")
HISTORY_WINDOW = settings.get("history_context_window", 20)
STALE_DAYS = settings.get("stale_days_threshold", 2)

# ============================================================
# CONVERSATIONS (ประวัติการคุย — ถาวรข้ามวัน)
# ============================================================
def load_history():
    return mem_load("conversations", [])

def save_history(history):
    mem_save("conversations", history)

# ============================================================
# WEB SEARCH (DuckDuckGo — ฟรี ไม่ต้อง API key)
# ============================================================
def web_search(query: str, max_results: int = 5) -> str:
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as res:
            data = json.loads(res.read().decode())

        results = []

        if data.get("AbstractText"):
            results.append(f"📌 สรุป: {data['AbstractText']}")

        for item in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(item, dict) and item.get("Text"):
                results.append(f"• {item['Text']}")

        if not results:
            return "ไม่พบผลลัพธ์ที่ชัดเจน ลองค้นด้วยคำอื่น"

        return "\n".join(results)
    except Exception as e:
        return f"ค้นหาไม่สำเร็จ: {e}"

# ============================================================
# GOALS (เก็บใน current_state.json)
# ============================================================
def load_goals():
    state = mem_load("current_state", {"active_goals": [], "focus": "", "last_updated": ""})
    return state.get("active_goals", [])

def save_goal(goal_text):
    state = mem_load("current_state", {"active_goals": [], "focus": "", "last_updated": ""})
    state.setdefault("active_goals", []).append({
        "goal": goal_text,
        "created": datetime.datetime.now().isoformat(),
        "status": "active"
    })
    state["last_updated"] = datetime.datetime.now().isoformat()
    mem_save("current_state", state)
    return f"✅ บันทึกเป้าหมายแล้ว: {goal_text}"

def show_goals():
    goals = load_goals()
    if not goals:
        return "ยังไม่มีเป้าหมายที่บันทึกไว้"
    lines = ["🎯 เป้าหมายของคุณ:"]
    for i, g in enumerate(goals, 1):
        status = "✅" if g["status"] == "done" else "🔄"
        lines.append(f"{i}. {status} {g['goal']} (เพิ่มเมื่อ {g['created'][:10]})")
    return "\n".join(lines)

# ============================================================
# TASKS
# ============================================================
def load_tasks():
    return mem_load("tasks", [])

def save_tasks(tasks):
    mem_save("tasks", tasks)

def add_task(task_text):
    tasks = load_tasks()
    tasks.append({
        "task": task_text,
        "created": datetime.datetime.now().isoformat(),
        "last_touched": datetime.datetime.now().isoformat(),
        "status": "pending"  # pending | in_progress | done
    })
    save_tasks(tasks)
    log_event(f"📝 งานใหม่: {task_text}")
    return f"📝 บันทึกงานแล้ว: {task_text}"

def show_tasks():
    tasks = load_tasks()
    if not tasks:
        return "ยังไม่มีงานที่บันทึกไว้"
    icon = {"pending": "⬜", "in_progress": "🔄", "done": "✅"}
    lines = ["📋 งานทั้งหมด:"]
    for i, t in enumerate(tasks, 1):
        lines.append(f"{i}. {icon.get(t['status'], '⬜')} {t['task']} (เพิ่มเมื่อ {t['created'][:10]})")
    return "\n".join(lines)

def complete_task(index):
    tasks = load_tasks()
    if 0 <= index - 1 < len(tasks):
        tasks[index - 1]["status"] = "done"
        tasks[index - 1]["last_touched"] = datetime.datetime.now().isoformat()
        save_tasks(tasks)
        log_event(f"✅ ปิดงาน: {tasks[index - 1]['task']}")
        return f"✅ ทำเสร็จแล้ว: {tasks[index - 1]['task']}"
    return "❌ ไม่พบงานลำดับนี้ ลองพิมพ์ /tasks เพื่อดูเลขงาน"

def get_stale_tasks(days=None):
    """งานที่ยังไม่เสร็จและไม่ถูกแตะต้องมานานเกิน N วัน — ใช้เตือนแบบมือขวา ไม่ใช่ตัดสินใจแทน"""
    days = days if days is not None else STALE_DAYS
    tasks = load_tasks()
    stale = []
    now = datetime.datetime.now()
    for t in tasks:
        if t["status"] != "done":
            last = datetime.datetime.fromisoformat(t["last_touched"])
            if (now - last).days >= days:
                stale.append(t["task"])
    return stale

# ============================================================
# PROJECTS
# ============================================================
def load_projects():
    return mem_load("projects", [])

def add_project(name):
    projects = load_projects()
    projects.append({
        "name": name,
        "status": "active",
        "created": datetime.datetime.now().isoformat()
    })
    mem_save("projects", projects)
    log_event(f"📁 โปรเจกต์ใหม่: {name}")
    return f"📁 เพิ่มโปรเจกต์แล้ว: {name}"

def show_projects():
    projects = load_projects()
    if not projects:
        return "ยังไม่มีโปรเจกต์ที่บันทึกไว้"
    lines = ["📁 โปรเจกต์ทั้งหมด:"]
    for i, p in enumerate(projects, 1):
        lines.append(f"{i}. {p['name']} ({p['status']}) — เริ่มเมื่อ {p['created'][:10]}")
    return "\n".join(lines)

# ============================================================
# CLIENTS (ลูกค้า)
# ============================================================
def load_clients():
    return mem_load("clients", [])

def add_client(text):
    """รูปแบบ: ชื่อ | โน้ต (โน้ตใส่หรือไม่ใส่ก็ได้)"""
    parts = text.split("|", 1)
    name = parts[0].strip()
    note = parts[1].strip() if len(parts) > 1 else ""
    clients = load_clients()
    clients.append({
        "name": name,
        "note": note,
        "added": datetime.datetime.now().isoformat()
    })
    mem_save("clients", clients)
    log_event(f"👤 ลูกค้าใหม่: {name}")
    return f"👤 เพิ่มลูกค้าแล้ว: {name}"

def show_clients():
    clients = load_clients()
    if not clients:
        return "ยังไม่มีลูกค้าที่บันทึกไว้ ใช้ /client ชื่อ | โน้ต เพื่อเพิ่ม"
    lines = ["👤 ลูกค้าทั้งหมด:"]
    for i, c in enumerate(clients, 1):
        note = f" — {c['note']}" if c.get("note") else ""
        lines.append(f"{i}. {c['name']}{note}")
    return "\n".join(lines)

# ============================================================
# TIMELINE — log กลางของทุกเหตุการณ์สำคัญ (ให้ Morning Briefing อ่านจากที่เดียว)
# ============================================================
def log_event(text):
    timeline = mem_load("timeline", [])
    timeline.append({"text": text, "at": datetime.datetime.now().isoformat()})
    mem_save("timeline", timeline)

def show_timeline(limit=20):
    timeline = mem_load("timeline", [])
    if not timeline:
        return "ยังไม่มีเหตุการณ์บันทึกไว้"
    lines = ["🕰️ Timeline ล่าสุด:"]
    for e in timeline[-limit:]:
        stamp = e["at"][:16].replace("T", " ")
        lines.append(f"- [{stamp}] {e['text']}")
    return "\n".join(lines)

# ============================================================
# CALENDAR (ตารางนัด/เดดไลน์)
# ============================================================
def load_calendar():
    return mem_load("calendar", [])

def add_event(text):
    """รูปแบบ: ชื่อนัด : วันที่เวลา เช่น 'ประชุมทีม Voice AI : 2026-07-25 14:00'"""
    if ":" not in text:
        return "❌ รูปแบบ: /event ชื่อนัด : วันที่เวลา เช่น /event ประชุมลูกค้า : 2026-07-25 14:00"
    title, when = text.split(":", 1)
    title = title.strip()
    when = when.strip()
    events = load_calendar()
    new_id = (events[-1]["id"] + 1) if events else 1
    events.append({
        "id": new_id,
        "title": title,
        "when": when,
        "created": datetime.datetime.now().isoformat()
    })
    mem_save("calendar", events)
    log_event(f"📅 นัดใหม่: {title} ({when})")
    return f"📅 เพิ่มนัดหมายแล้ว: {title} — {when}"

def show_calendar():
    events = load_calendar()
    if not events:
        return "ยังไม่มีนัดหมายที่บันทึกไว้ ใช้ /event ชื่อนัด : วันที่เวลา เพื่อเพิ่ม"
    lines = ["📅 ตารางงานทั้งหมด:"]
    for e in sorted(events, key=lambda x: x["when"]):
        lines.append(f"{e['id']}. {e['title']} — {e['when']}")
    return "\n".join(lines)

def get_today_events():
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    return [e for e in load_calendar() if e["when"].startswith(today_str)]

# ============================================================
# PREFERENCES (นิสัย/วิธีทำงานของเจ้าของ — ให้ Chief ปรับตัวเข้าหา)
# ============================================================
def load_preferences():
    return mem_load("preferences", {})

def set_preference(text):
    """รูปแบบ: เรื่อง : รายละเอียด เช่น 'เวลาโฟกัสดีที่สุด : เช้า 8-11 โมง'"""
    if ":" not in text:
        return "❌ รูปแบบ: /prefer เรื่อง : รายละเอียด เช่น /prefer เวลาโฟกัสดีที่สุด : เช้า 8-11 โมง"
    key, value = text.split(":", 1)
    prefs = load_preferences()
    prefs[key.strip()] = value.strip()
    mem_save("preferences", prefs)
    log_event(f"🧭 อัปเดตนิสัยการทำงาน: {key.strip()}")
    return f"🧭 บันทึกแล้ว: {key.strip()} → {value.strip()}"

def show_preferences():
    prefs = load_preferences()
    if not prefs:
        return "ยังไม่มีข้อมูลนิสัย/วิธีทำงานที่บันทึกไว้ ใช้ /prefer เรื่อง : รายละเอียด เพื่อสอน Chief"
    lines = ["🧭 นิสัย/วิธีทำงานของคุณที่ Chief รู้:"]
    for k, v in prefs.items():
        lines.append(f"- {k}: {v}")
    return "\n".join(lines)

# ============================================================
# KNOWLEDGE (ความรู้/บริบทที่ Chief เรียนรู้เพิ่มระหว่างทาง)
# ============================================================
def load_knowledge():
    return mem_load("knowledge", [])

def add_knowledge(fact):
    knowledge = load_knowledge()
    knowledge.append({
        "fact": fact,
        "added": datetime.datetime.now().isoformat()
    })
    mem_save("knowledge", knowledge)
    return f"🧠 จำไว้แล้ว: {fact}"

def show_knowledge():
    knowledge = load_knowledge()
    if not knowledge:
        return "ยังไม่มีความรู้ที่บันทึกไว้ ใช้ /learn [ข้อความ] เพื่อสอนผมได้เลยครับ"
    lines = ["🧠 สิ่งที่จำไว้:"]
    for i, k in enumerate(knowledge, 1):
        lines.append(f"{i}. {k['fact']}")
    return "\n".join(lines)

# ============================================================
# WORKFLOWS (SOP / กระบวนการทำงาน)
# ============================================================
def load_workflows():
    return mem_load("workflows", [])

def add_workflow(text):
    """รูปแบบ: ชื่อ workflow : ขั้นตอน1, ขั้นตอน2, ขั้นตอน3"""
    if ":" in text:
        name, steps_raw = text.split(":", 1)
        steps = [s.strip() for s in steps_raw.split(",") if s.strip()]
    else:
        name, steps = text, []
    workflows = load_workflows()
    workflows.append({
        "name": name.strip(),
        "steps": steps,
        "created": datetime.datetime.now().isoformat()
    })
    mem_save("workflows", workflows)
    return f"🔁 บันทึก workflow แล้ว: {name.strip()} ({len(steps)} ขั้นตอน)"

def show_workflows():
    workflows = load_workflows()
    if not workflows:
        return "ยังไม่มี workflow ที่บันทึกไว้ ใช้ /workflow ชื่อ : ขั้นตอน1, ขั้นตอน2 เพื่อเพิ่ม"
    lines = ["🔁 Workflow ทั้งหมด:"]
    for i, w in enumerate(workflows, 1):
        lines.append(f"{i}. {w['name']}")
        for j, s in enumerate(w["steps"], 1):
            lines.append(f"     {j}. {s}")
    return "\n".join(lines)

# ============================================================
# DECISIONS LOG — ทุกเรื่องที่ AI วิเคราะห์ให้ (/decide, /team) ถูกบันทึกไว้
# รอให้เจ้าของตัดสินใจเอง แล้วปิดเรื่องด้วย /decided
# ============================================================
def log_decision(topic, options_summary):
    decisions = mem_load("decisions", [])
    new_id = (decisions[-1]["id"] + 1) if decisions else 1
    decisions.append({
        "id": new_id,
        "topic": topic,
        "options_presented": options_summary,
        "decided": None,
        "status": "pending",
        "created": datetime.datetime.now().isoformat(),
        "decided_at": None
    })
    mem_save("decisions", decisions)
    return new_id

def show_decisions():
    decisions = mem_load("decisions", [])
    if not decisions:
        return "ยังไม่มีเรื่องที่รอการตัดสินใจ"
    lines = ["⚖️ บันทึกการตัดสินใจ:"]
    for d in decisions:
        icon = "✅" if d["status"] == "decided" else "⏳"
        extra = f" → เลือก: {d['decided']}" if d.get("decided") else ""
        lines.append(f"{d['id']}. {icon} {d['topic']}{extra}")
    return "\n".join(lines)

def record_decision(decision_id, choice_text):
    decisions = mem_load("decisions", [])
    for d in decisions:
        if d["id"] == decision_id:
            d["decided"] = choice_text
            d["status"] = "decided"
            d["decided_at"] = datetime.datetime.now().isoformat()
            mem_save("decisions", decisions)
            log_event(f"⚖️ ตัดสินใจแล้ว: {d['topic']} → {choice_text}")
            return f"✅ บันทึกการตัดสินใจ #{decision_id} แล้ว: {choice_text}"
    return f"❌ ไม่พบเรื่อง #{decision_id} ลองพิมพ์ /decisions เพื่อดูรายการ"

def pending_decisions_count():
    decisions = mem_load("decisions", [])
    return len([d for d in decisions if d["status"] != "decided"])

# ============================================================
# COMPANY OS — ROCKS (เป้าหมายใหญ่รายไตรมาสแบบ EOS)
# ============================================================
def current_quarter():
    now = datetime.datetime.now()
    q = (now.month - 1) // 3 + 1
    return f"{now.year}-Q{q}"

def load_rocks():
    return mem_load("rocks", [])

def add_rock(title):
    rocks = load_rocks()
    new_id = (rocks[-1]["id"] + 1) if rocks else 1
    rocks.append({
        "id": new_id,
        "title": title,
        "quarter": current_quarter(),
        "status": "on-track",  # on-track | at-risk | done
        "created": datetime.datetime.now().isoformat()
    })
    mem_save("rocks", rocks)
    log_event(f"🪨 Rock ใหม่: {title}")
    return f"🪨 เพิ่ม Rock ไตรมาส {current_quarter()} แล้ว: {title}"

def show_rocks():
    rocks = load_rocks()
    q = current_quarter()
    this_q = [r for r in rocks if r["quarter"] == q]
    if not this_q:
        return f"ยังไม่มี Rock สำหรับไตรมาส {q} ใช้ /rock [ชื่อ] เพื่อเพิ่ม"
    icon = {"on-track": "🟢", "at-risk": "🟡", "done": "✅"}
    lines = [f"🪨 Rocks ไตรมาส {q}:"]
    for r in this_q:
        lines.append(f"{r['id']}. {icon.get(r['status'], '🟢')} {r['title']} ({r['status']})")
    return "\n".join(lines)

def set_rock_status(rock_id, status):
    valid = {"on-track", "at-risk", "done"}
    if status not in valid:
        return f"❌ สถานะต้องเป็นหนึ่งใน {', '.join(valid)}"
    rocks = load_rocks()
    for r in rocks:
        if r["id"] == rock_id:
            r["status"] = status
            mem_save("rocks", rocks)
            log_event(f"🪨 Rock '{r['title']}' เปลี่ยนสถานะเป็น {status}")
            return f"🪨 อัปเดตสถานะ Rock #{rock_id} เป็น {status} แล้ว"
    return f"❌ ไม่พบ Rock #{rock_id}"

def get_at_risk_rocks():
    q = current_quarter()
    return [r for r in load_rocks() if r["quarter"] == q and r["status"] == "at-risk"]

# ============================================================
# COMPANY OS — SCORECARD (ตัวชี้วัดรายสัปดาห์)
# ============================================================
def current_week():
    iso = datetime.datetime.now().isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"

def load_scorecard():
    return mem_load("scorecard", [])

def add_metric(text):
    """รูปแบบ: ชื่อ metric : เป้าหมาย"""
    if ":" not in text:
        return "❌ รูปแบบ: /metric ชื่อ : เป้าหมาย เช่น /metric ยอดขายใหม่ : 20"
    name, target_raw = text.split(":", 1)
    name = name.strip()
    try:
        target = float(target_raw.strip())
    except ValueError:
        return "❌ เป้าหมายต้องเป็นตัวเลข"
    metrics = load_scorecard()
    for m in metrics:
        if m["metric"].lower() == name.lower():
            m["target"] = target
            mem_save("scorecard", metrics)
            return f"📈 อัปเดตเป้าหมาย {name} เป็น {target} แล้ว"
    metrics.append({"metric": name, "target": target, "history": []})
    mem_save("scorecard", metrics)
    return f"📈 เพิ่มตัวชี้วัด {name} (เป้าหมาย {target}) แล้ว"

def log_metric(text):
    """รูปแบบ: ชื่อ metric : ค่า"""
    if ":" not in text:
        return "❌ รูปแบบ: /log ชื่อ : ค่า เช่น /log ยอดขายใหม่ : 15"
    name, value_raw = text.split(":", 1)
    name = name.strip()
    try:
        value = float(value_raw.strip())
    except ValueError:
        return "❌ ค่าต้องเป็นตัวเลข"
    metrics = load_scorecard()
    for m in metrics:
        if m["metric"].lower() == name.lower():
            week = current_week()
            m["history"] = [h for h in m["history"] if h["week"] != week]
            m["history"].append({"week": week, "value": value})
            mem_save("scorecard", metrics)
            return f"📊 บันทึก {name} สัปดาห์ {week} = {value} แล้ว"
    return f"❌ ไม่พบตัวชี้วัด '{name}' ใช้ /metric ชื่อ : เป้าหมาย เพื่อสร้างก่อน"

def show_scorecard():
    metrics = load_scorecard()
    if not metrics:
        return "ยังไม่มีตัวชี้วัดที่บันทึกไว้ ใช้ /metric ชื่อ : เป้าหมาย เพื่อเพิ่ม"
    lines = ["📈 Scorecard:"]
    for m in metrics:
        if m["history"]:
            latest = m["history"][-1]
            status_icon = "✅" if latest["value"] >= m["target"] else "⚠️"
            lines.append(f"{status_icon} {m['metric']}: {latest['value']} / เป้า {m['target']} (สัปดาห์ {latest['week']})")
        else:
            lines.append(f"➖ {m['metric']}: ยังไม่มีการบันทึกค่า (เป้า {m['target']})")
    return "\n".join(lines)

def get_off_target_metrics():
    metrics = load_scorecard()
    off = []
    for m in metrics:
        if m["history"] and m["history"][-1]["value"] < m["target"]:
            off.append(f"{m['metric']} ({m['history'][-1]['value']}/{m['target']})")
    return off

# ============================================================
# COMPANY OS — ISSUES LIST (EOS-style: Identify, Discuss, Solve)
# ============================================================
def load_issues():
    return mem_load("issues", [])

def add_issue(title):
    issues = load_issues()
    new_id = (issues[-1]["id"] + 1) if issues else 1
    issues.append({
        "id": new_id,
        "title": title,
        "status": "open",  # open | solved
        "resolution": None,
        "created": datetime.datetime.now().isoformat(),
        "solved_at": None
    })
    mem_save("issues", issues)
    log_event(f"🚩 ปัญหาใหม่: {title}")
    return f"🚩 บันทึกปัญหาแล้ว: {title}"

def show_issues():
    issues = load_issues()
    if not issues:
        return "ยังไม่มีปัญหาที่บันทึกไว้ ดีแล้ว 🎉"
    open_issues = [i for i in issues if i["status"] == "open"]
    lines = [f"🚩 ปัญหาที่ยังไม่แก้ ({len(open_issues)}):"]
    for i in open_issues:
        lines.append(f"{i['id']}. {i['title']}")
    solved = [i for i in issues if i["status"] == "solved"]
    if solved:
        lines.append(f"\n✅ แก้ไปแล้ว ({len(solved)}):")
        for i in solved[-5:]:
            lines.append(f"{i['id']}. {i['title']} → {i['resolution']}")
    return "\n".join(lines)

def solve_issue(issue_id, resolution):
    issues = load_issues()
    for i in issues:
        if i["id"] == issue_id:
            i["status"] = "solved"
            i["resolution"] = resolution
            i["solved_at"] = datetime.datetime.now().isoformat()
            mem_save("issues", issues)
            log_event(f"✅ แก้ปัญหาแล้ว: {i['title']} → {resolution}")
            return f"✅ แก้ปัญหา #{issue_id} แล้ว: {resolution}"
    return f"❌ ไม่พบปัญหา #{issue_id}"

def get_open_issues_count():
    return len([i for i in load_issues() if i["status"] == "open"])

# ============================================================
# MORNING BRIEFING — Chief ไม่รอคำสั่ง เปิดมาสรุปให้เองทุกครั้ง
# ============================================================
def _happened_since(ts_str, cutoff):
    if not ts_str:
        return False
    try:
        return datetime.datetime.fromisoformat(ts_str) >= cutoff
    except (ValueError, TypeError):
        return False

def get_session_gap_events():
    """อ่านจาก timeline.json (log กลางที่ทุกการกระทำเขียนเข้ามาเอง) เทียบกับตอนเปิดใช้ครั้งก่อน (last_seen) แล้วคืนรายการที่เปลี่ยนไป จากนั้นอัปเดต last_seen เป็นตอนนี้"""
    state = mem_load("current_state", {"active_goals": [], "focus": "", "last_updated": "", "last_seen": None})
    last_seen_str = state.get("last_seen")
    now = datetime.datetime.now()
    cutoff = datetime.datetime.fromisoformat(last_seen_str) if last_seen_str else (now - datetime.timedelta(days=1))

    timeline = mem_load("timeline", [])
    events = [e["text"] for e in timeline if _happened_since(e.get("at"), cutoff)]

    state["last_seen"] = now.isoformat()
    mem_save("current_state", state)
    return events

def build_morning_briefing():
    """สร้างสรุปเช้าแบบ Good morning — Chief พูดก่อนโดยไม่ต้องรอคำสั่ง"""
    events = get_session_gap_events()
    events_text = "\n".join([f"- {e}" for e in events]) if events else "ไม่มีความเคลื่อนไหวตั้งแต่ครั้งก่อนที่เปิดคุย"

    today_open = [t for t in load_tasks() if t["status"] != "done"]
    today_events = get_today_events()
    stale = get_stale_tasks()
    at_risk_rocks = get_at_risk_rocks()
    off_target = get_off_target_metrics()
    open_issues_n = get_open_issues_count()
    pending_dec = pending_decisions_count()

    context = f"""ความเปลี่ยนแปลงตั้งแต่ครั้งก่อนที่เปิดคุยกัน:
{events_text}

นัดหมายวันนี้ ({len(today_events)} นัด):
{chr(10).join(f"- {e['title']} ({e['when']})" for e in today_events) or "ไม่มี"}

งานที่ยังเปิดอยู่ตอนนี้ ({len(today_open)} งาน):
{chr(10).join(f"- {t['task']}" for t in today_open) or "ไม่มี"}

งานที่นิ่งไปนานไม่มีความเคลื่อนไหว: {len(stale)} งาน
Rock ที่ at-risk: {len(at_risk_rocks)} รายการ
ตัวชี้วัดต่ำกว่าเป้า: {len(off_target)} ตัว
ปัญหาที่ยังไม่แก้: {open_issues_n} เรื่อง
เรื่องที่รอการตัดสินใจของเจ้าของ: {pending_dec} เรื่อง"""

    system = f"""คุณคือ "Chief" มือขวาส่วนตัวของ {owner['name']} ที่บริษัท {company['name']}
งานตอนนี้: เขียนสรุปเปิดวันใหม่ (Morning Briefing) ให้เจ้าของ โดยไม่ต้องรอให้ถามก่อน

ใช้รูปแบบนี้เป๊ะๆ:

Good morning.
เมื่อคืนมีการเปลี่ยนแปลง [จำนวน] เรื่อง
• [รายการเปลี่ยนแปลง สั้น กระชับ ทีละบรรทัด]

Recommendation
1. [สิ่งที่แนะนำให้ทำก่อน]
2. [ต่อมา]
3. [ต่อมา]

Estimated focus: [จำนวนชั่วโมงโดยประมาณที่ต้องใช้สมาธิวันนี้]
Risk: [Low/Medium/High]

กติกา:
- Recommendation คือคำแนะนำเท่านั้น ไม่ใช่คำสั่ง เจ้าของเป็นคนตัดสินใจเองว่าจะทำตามหรือไม่
- ถ้าไม่มีความเคลื่อนไหวเลย ให้บอกตรงๆ ว่าเงียบ ไม่ต้องเสกข้อมูลขึ้นมาให้ดูมีเรื่อง
- กระชับที่สุด อ่านจบใน 15 วินาที ไม่ต้องทักทายซ้ำหรือใส่คำฟุ่มเฟือย"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": context}
        ]
    )
    return response.choices[0].message.content

# ============================================================
# STATUS REPORT
# ============================================================
def build_status_report():
    """สรุปสถานะแบบมือขวา: เป้าหมาย + งานค้าง + งานที่นิ่งไปนาน + เรื่องรอตัดสินใจ + Company OS — ไม่ฟันธง แค่รายงาน"""
    goals = load_goals()
    tasks = load_tasks()
    active_goals = [g for g in goals if g["status"] == "active"]
    pending_tasks = [t for t in tasks if t["status"] != "done"]
    stale = get_stale_tasks()
    pending_dec = pending_decisions_count()
    at_risk_rocks = get_at_risk_rocks()
    off_target = get_off_target_metrics()
    open_issues = get_open_issues_count()

    lines = ["📊 สรุปสถานะ ณ ตอนนี้", "-" * 30]

    lines.append(f"🪨 Rocks ไตรมาส {current_quarter()}: {len(load_rocks())} รายการ" + (f" (⚠️ at-risk {len(at_risk_rocks)} รายการ)" if at_risk_rocks else ""))
    for r in at_risk_rocks:
        lines.append(f"   - {r['title']}")

    if off_target:
        lines.append(f"\n📉 ตัวชี้วัดต่ำกว่าเป้า: {len(off_target)} ตัว")
        for m in off_target:
            lines.append(f"   - {m}")

    if open_issues:
        lines.append(f"\n🚩 ปัญหาที่ยังไม่แก้: {open_issues} เรื่อง (พิมพ์ /issues เพื่อดู)")

    lines.append(f"\n🎯 เป้าหมายที่เปิดอยู่: {len(active_goals)}")
    for g in active_goals:
        lines.append(f"   - {g['goal']}")

    lines.append(f"\n📋 งานค้าง: {len(pending_tasks)}")
    for t in pending_tasks:
        lines.append(f"   - {t['task']} ({t['status']})")

    if pending_dec:
        lines.append(f"\n⚖️ เรื่องที่รอการตัดสินใจของคุณ: {pending_dec} เรื่อง (พิมพ์ /decisions เพื่อดู)")

    if stale:
        lines.append(f"\n⚠️ งานที่นิ่งไปเกิน {STALE_DAYS} วัน (ยังไม่ปิด ยังไม่มีความเคลื่อนไหว):")
        for s in stale:
            lines.append(f"   - {s}")
        lines.append("\nไม่ได้บอกว่าต้องทำอะไรก่อนนะครับ แค่รายงานให้เห็นภาพ — คุณตัดสินใจเองว่าจะเดินหน้าตัวไหนก่อน")

    if not active_goals and not pending_tasks and not pending_dec and not at_risk_rocks and not off_target and not open_issues:
        lines.append("\n✨ ตอนนี้ไม่มีงาน เป้าหมาย เรื่องค้างตัดสินใจ หรือปัญหาค้างเลย")

    return "\n".join(lines)

# ============================================================
# DEPARTMENT AGENTS (พนักงานแต่ละแผนก ใต้ Chief of Staff — นิยามอยู่ใน memory/agents.json)
# ============================================================
def list_departments():
    lines = ["🏢 แผนกทั้งหมดใต้ Chief of Staff:"]
    for key, d in DEPARTMENTS.items():
        lines.append(f"   • {d['name']} ({key}) — {d['role']}")
    return "\n".join(lines)

def call_department(dept_key, request, consult_context=""):
    """เรียกพนักงานแผนกเดียวให้วิเคราะห์งาน โดยเห็นความเห็นแผนกก่อนหน้า (ถ้ามี) เพื่อจำลองการ 'ปรึกษากัน'"""
    dept = DEPARTMENTS[dept_key]
    extra_data = ""
    if dept_key == "research":
        extra_data = f"\n\nข้อมูลจากการค้นเว็บ:\n{web_search(request)}"

    system = f"""คุณคือพนักงานแผนก {dept['name']} ในทีมของ {owner['name']} (CEO) บริษัท {company['name']}
หน้าที่ของคุณ: {dept['role']}

กติกา:
- วิเคราะห์เฉพาะในมุมของแผนกคุณเท่านั้น อย่าก้าวก่ายแผนกอื่น
- ถ้ามีความเห็นจากแผนกอื่นที่ปรึกษามาก่อนหน้า ให้พิจารณาประกอบ และเห็นด้วย/แย้งได้ตรงๆ ถ้ามีเหตุผล
- ตอบสั้น กระชับ เป็น bullet points ไม่ต้องทักทาย
- ห้ามตัดสินใจแทน CEO เด็ดขาด แค่ให้ข้อมูล+มุมมองจากแผนกคุณ"""

    user_msg = f"งานที่ CEO ต้องการให้แผนกคุณช่วยดู: {request}"
    if consult_context:
        user_msg += f"\n\nความเห็นจากแผนกอื่นที่ปรึกษามาก่อนหน้าคุณ:\n{consult_context}"
    user_msg += extra_data

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg}
        ]
    )
    return response.choices[0].message.content

def route_departments(request):
    """Chief of Staff วิเคราะห์ว่างานนี้ควรส่งให้แผนกไหนบ้าง (เลือกเอง ไม่ต้องให้ CEO เลือก)"""
    dept_keys = ", ".join(DEPARTMENTS.keys())
    system = f"""คุณคือ Chief of Staff วิเคราะห์ว่างานที่ CEO สั่งมาเกี่ยวข้องกับแผนกไหนบ้าง
แผนกที่มีให้เลือก (ใช้ key ตรงตัว): {dept_keys}
ตอบกลับเป็น comma-separated ของ key แผนกเท่านั้น (เช่น: engineering,marketing) ห้ามอธิบายเพิ่ม เลือกเฉพาะแผนกที่เกี่ยวข้องจริง อย่างน้อย 1 แผนก อย่างมาก 4 แผนก"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": request}
        ]
    )
    raw = response.choices[0].message.content.strip().lower()
    chosen = [d.strip() for d in raw.split(",") if d.strip() in DEPARTMENTS]
    return chosen or list(DEPARTMENTS.keys())[:1]

def run_team_task(request):
    """Orchestration เต็มรูปแบบ: route -> ส่งงานต่อเนื่องแบบเห็นบริบทกัน (ปรึกษากัน) -> Chief of Staff สรุปให้ CEO ตัดสินใจ"""
    print("\n🧭 Chief of Staff: กำลังพิจารณาว่างานนี้เกี่ยวกับแผนกไหนบ้าง...")
    depts = route_departments(request)
    print(f"📨 ส่งงานให้แผนก: {', '.join(DEPARTMENTS[d]['name'] for d in depts)}")

    consult_context = ""
    reports = []
    for d in depts:
        print(f"   💼 {DEPARTMENTS[d]['name']} กำลังวิเคราะห์...")
        result = call_department(d, request, consult_context)
        reports.append((DEPARTMENTS[d]['name'], result))
        consult_context += f"\n[{DEPARTMENTS[d]['name']}]: {result}\n"

    system = """คุณคือ Chief of Staff สรุปความเห็นจากทุกแผนกให้ CEO แบบกระชับที่สุด
- รวมประเด็นสำคัญจากทุกแผนก ไม่พูดซ้ำ
- ถ้าแผนกใดมีความเห็นขัดแย้งกัน ให้ชี้ให้เห็นตรงๆ ว่าขัดกันตรงไหน
- ห้ามฟันธงว่า CEO ควรทำอะไร แค่สรุปข้อมูล+ทางเลือกให้ครบที่สุด
- จบด้วย "🤝 รอการตัดสินใจของคุณครับ" เสมอ"""
    compiled = "\n\n".join([f"### {name}\n{txt}" for name, txt in reports])
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"เรื่อง: {request}\n\nความเห็นจากแต่ละแผนก:\n{compiled}"}
        ]
    )
    return response.choices[0].message.content

# ============================================================
# SYSTEM PROMPT
# ============================================================
def build_system_prompt():
    goals = load_goals()
    tasks = load_tasks()
    goal_text = "\n".join([f"- {g['goal']}" for g in goals if g["status"] == "active"]) or "ยังไม่มีเป้าหมาย"
    task_text = "\n".join([f"- [{t['status']}] {t['task']}" for t in tasks if t["status"] != "done"]) or "ยังไม่มีงานค้าง"
    stale = get_stale_tasks()
    stale_text = ("\n".join([f"- {s}" for s in stale]) if stale else "ไม่มี")
    knowledge = load_knowledge()
    knowledge_text = ("\n".join([f"- {k['fact']}" for k in knowledge[-8:]]) if knowledge else "ยังไม่มี")
    pending_dec = pending_decisions_count()

    q = current_quarter()
    rocks_this_q = [r for r in load_rocks() if r["quarter"] == q]
    rocks_text = ("\n".join([f"- [{r['status']}] {r['title']}" for r in rocks_this_q]) if rocks_this_q else "ยังไม่มี Rock ในไตรมาสนี้")
    off_target = get_off_target_metrics()
    off_target_text = ("\n".join([f"- {m}" for m in off_target]) if off_target else "ไม่มี (หรือยังไม่ได้ตั้งตัวชี้วัด)")
    open_issues = get_open_issues_count()

    today_events = get_today_events()
    today_events_text = ("\n".join([f"- {e['title']} ({e['when']})" for e in today_events]) if today_events else "ไม่มีนัดวันนี้")

    prefs = load_preferences()
    prefs_text = ("\n".join([f"- {k}: {v}" for k, v in prefs.items()]) if prefs else "ยังไม่มีข้อมูล")

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""คุณคือ "Chief" มือขวาส่วนตัวของ {owner['name']} — คนที่เขาไว้ใจที่สุดในการติดตามงานและเป้าหมาย ที่บริษัท {company['name']}
วันที่และเวลาปัจจุบัน: {now}

## ข้อมูลเจ้าของ
- ชื่อ: {owner['name']}
- บริษัท: {company['name']}
- เป้าหมายหลัก: {owner.get('goal', '')}

## นิสัย/วิธีทำงานของเจ้าของที่ควรปรับตัวเข้าหา:
{prefs_text}

## นัดหมายวันนี้:
{today_events_text}

## Rocks ไตรมาส {q} (เป้าหมายใหญ่ระดับบริษัท):
{rocks_text}

## ตัวชี้วัดที่ต่ำกว่าเป้า (Scorecard):
{off_target_text}

## ปัญหาที่ยังไม่แก้ (Issues): {open_issues} เรื่อง

## เป้าหมายที่บันทึกไว้:
{goal_text}

## งานค้างตอนนี้:
{task_text}

## งานที่นิ่งไปนาน (ไม่มีความเคลื่อนไหว {STALE_DAYS} วันขึ้นไป):
{stale_text}

## สิ่งที่เคยเรียนรู้เกี่ยวกับบริบทงาน (ล่าสุด):
{knowledge_text}

## เรื่องที่รอเจ้าของตัดสินใจอยู่: {pending_dec} เรื่อง

## บทบาทของคุณ — มือขวาที่สนิทที่สุด ไม่ใช่ผู้ตัดสินใจเชิงกลยุทธ์
- จำทุกงาน ทุกเป้าหมาย เชื่อมทุกบทสนทนากลับมาที่สิ่งที่เจ้าของกำลังทำอยู่เสมอ
- เชิงรุก: ถ้าเห็นงานค้าง ความเสี่ยง หรือโอกาส ให้พูดออกมาตรงๆ ไม่ต้องรอถาม รวมถึง Rock ที่ at-risk, ตัวชี้วัดที่ต่ำกว่าเป้า, และปัญหาที่ค้างนาน
- เวลาต้อง "ตัดสินใจเชิงกลยุทธ์" (/decide หรือคำถามที่มีทางเลือกกระทบธุรกิจ เช่น จะเลือกแผน A หรือ B) หน้าที่คุณคือ วิเคราะห์ข้อมูล เสนอทางเลือกพร้อม pros/cons ให้ครบและตรงไปตรงมาที่สุด — แต่**ห้ามฟันธงหรือเลือกแทนเจ้าของเด็ดขาด** อำนาจตัดสินใจสุดท้ายเป็นของเจ้าของคนเดียวเสมอ ปิดท้ายด้วยประโยคทำนอง "การตัดสินใจสุดท้ายอยู่ที่คุณครับ" แทนการบอกว่า "ควรเลือกข้อ X"
- กระชับ ไม่ยืดยาว ไม่พูดซ้ำสิ่งที่เจ้าของรู้อยู่แล้ว

## ⚡ คุณเรียกฟังก์ชันจริงได้เอง — อย่าแค่ตอบว่าจะทำ ให้ลงมือทำเลย
กฎ "ห้ามตัดสินใจแทนเจ้าของ" ด้านบน ใช้กับ**การตัดสินใจเชิงกลยุทธ์เท่านั้น** ไม่ได้แปลว่าให้คุณลังเลที่จะ**ลงมือทำ**สิ่งที่เจ้าของสั่งตรงๆ อยู่แล้ว

เมื่อเจ้าของพูดสิ่งที่เป็น "คำสั่งให้ทำ" ไม่ใช่ "คำถามให้เลือก" — เช่น "ช่วยเพิ่มงานให้หน่อย", "บันทึกลูกค้าใหม่", "ตั้ง Rock เรื่องนี้ให้หน่อย", "ปิดปัญหานี้ที" — **ให้เรียกฟังก์ชัน (tool) ที่ตรงกับคำสั่งนั้นทันที** แล้วค่อยสรุปผลให้เจ้าของทราบว่าทำอะไรไปแล้ว อย่าตอบแค่ "ได้ครับ เดี๋ยวเพิ่มให้" เฉยๆ โดยไม่เรียกฟังก์ชันจริง เพราะเจ้าของจะไม่เห็นผลลัพธ์อะไรเลย

รายการคำสั่ง `/goals`, `/task` ฯลฯ ด้านล่างเป็นแค่ **ทางลัดสำหรับพิมพ์ตรงๆ** ของเจ้าของเท่านั้น — เวลาเจ้าของพิมพ์เป็นภาษาธรรมชาติแทน หน้าที่ของ**คุณเอง**คือเรียกฟังก์ชันที่มีให้ ไม่ใช่ปล่อยผ่านไปเฉยๆ

## คำสั่งพิเศษที่รองรับ (ทางลัดที่เจ้าของพิมพ์ตรงๆ ได้ ไม่ต้องผ่านคุณ)
/goals, /goal, /tasks, /task, /done, /status, /morning, /projects, /project, /clients, /client,
/calendar, /event, /preferences, /prefer, /timeline,
/knowledge, /learn, /workflows, /workflow, /decisions, /decided, /rocks, /rock, /rock-status,
/scorecard, /metric, /log, /issues, /issue, /solve, /plan, /research, /decide,
/draft, /team, /departments, /clear, /help

## ทีมงานใต้คุณ
มีแผนกลูกทีม {len(DEPARTMENTS)} แผนก ({', '.join(d['name'] for d in DEPARTMENTS.values())}) ที่คุณ (Chief of Staff) เรียกใช้ผ่านคำสั่ง /team ได้ — คุณเป็นคนกลางที่กระจายงาน รวบรวมความเห็น และสรุปให้เจ้าของตัดสินใจ ไม่ใช่แผนกเหล่านั้นเอง

## สไตล์การตอบ
- ภาษาไทยเป็นหลัก สลับอังกฤษเมื่อจำเป็น
- ตรงไปตรงมา ไม่ยืดยาว
- จบทุก task ด้วย "⚡ ขั้นต่อไป:" เสมอ (เว้นแต่เคสที่ต้องให้เจ้าของตัดสินใจ ให้ใช้ "🤝 รอการตัดสินใจของคุณ:" แทน)"""

# ============================================================
# CLIENT
# ============================================================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

conversation_history = load_history()

# ============================================================
# TELEGRAM — ส่ง Morning Briefing (หรือข้อความอื่นๆ) เข้ามือถือโดยตรง
# ============================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(text):
    """ส่งข้อความไปยัง Telegram ผ่าน Bot API — ถ้ายังไม่ตั้งค่า token/chat_id ไว้ จะข้ามเงียบๆ ไม่ error"""

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = json.dumps(
            {"chat_id": TELEGRAM_CHAT_ID, "text": text}
        ).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status == 200

    except Exception as exc:
        print(f"Telegram message delivery failed ({type(exc).__name__})")
        return False
