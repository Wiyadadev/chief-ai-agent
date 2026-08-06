import gradio as gr
import base64
import io
import os
import json
import tempfile
from datetime import datetime as dt_class
from memory.store import *
from nox_project_manager import (
    next_action as nox_next_action,
    set_status as nox_set_status,
    resolve_project_path as nox_resolve_project_path,
    save_project_path as nox_save_project_path,
)

# ============================================================
# Hugging Face ZeroGPU requires at least one @spaces.GPU-decorated
# function to exist, or it throws a runtime error on startup — even
# though this app never actually needs a GPU (it only calls the
# OpenAI API). This dummy function exists purely to satisfy that
# check. Wrapped in try/except so running locally (no `spaces`
# package installed, no HF Spaces environment) still works fine.
# ============================================================
try:
    import spaces

    @spaces.GPU
    def _zerogpu_keepalive():
        return True
except ImportError:
    pass

# ============================================================
# SLASH COMMAND HANDLER (ให้ Web UI ทำงานเหมือน CLI เป๊ะ)
# ============================================================
def handle_command(text):
    """คืนคำตอบถ้าเป็นคำสั่งที่ทำได้ทันทีโดยไม่ต้องเรียก AI, คืน None ถ้าไม่ใช่คำสั่ง (ให้ไปคุยกับ AI ปกติ)"""
    if text == "/help":
        return ("📋 คำสั่งทั้งหมด:\n"
                "/goals — แสดงเป้าหมายทั้งหมด\n"
                "/goal [ข้อความ] — บันทึกเป้าหมายใหม่\n"
                "/tasks — แสดงงานทั้งหมด\n"
                "/task [ข้อความ] — บันทึกงานใหม่\n"
                "/done [เลข] — ปิดงาน (เลขดูจาก /tasks)\n"
                "/status — สรุปสถานะทั้งหมด\n"
                "/morning — Morning Briefing (เรียกซ้ำได้ทุกเมื่อ)\n"
                "/projects — แสดงโปรเจกต์ทั้งหมด\n"
                "/project [ชื่อ] — เพิ่มโปรเจกต์ใหม่\n"
                "/contacts — แสดงผู้ติดต่อทั้งหมด\n"
                "/contact [ชื่อ|โน้ต] — เพิ่มผู้ติดต่อใหม่\n"
                "/knowledge — แสดงสิ่งที่ Chief เรียนรู้ไว้\n"
                "/learn [ข้อความ] — สอนข้อมูล/บริบทให้ Chief จำ\n"
                "/workflows — แสดง workflow ทั้งหมด\n"
                "/workflow ชื่อ : ขั้นตอน1, ขั้นตอน2 — บันทึก workflow ใหม่\n"
                "/decide [ปัญหา] — วิเคราะห์และเสนอทางเลือก (บันทึกลง decisions log)\n"
                "/decisions — ดูเรื่องที่รอ/ตัดสินใจไปแล้ว\n"
                "/decided [เลข] [สิ่งที่เลือก] — บันทึกว่าคุณตัดสินใจอะไรไปแล้ว\n"
                "/rocks — Rocks (เป้าหมายใหญ่) ไตรมาสนี้\n"
                "/rock [ชื่อ] — เพิ่ม Rock ใหม่\n"
                "/rock-status [เลข] [on-track|at-risk|done] — อัปเดตสถานะ Rock\n"
                "/scorecard — ดูตัวชี้วัดทั้งหมด\n"
                "/metric [ชื่อ] : [เป้าหมาย] — สร้าง/แก้ตัวชี้วัด\n"
                "/log [ชื่อ] : [ค่า] — บันทึกค่าตัวชี้วัดสัปดาห์นี้\n"
                "/issues — ปัญหาที่ยังไม่แก้ทั้งหมด\n"
                "/issue [ชื่อ] — บันทึกปัญหาใหม่\n"
                "/solve [เลข] [วิธีแก้] — ปิดปัญหา\n"
                "/departments — แสดงแผนกทั้งหมดในทีม\n"
                "/team [งาน] — ส่งงานให้ทีมช่วยวิเคราะห์ (ปรึกษากันเองแล้วสรุป)\n"
                "/plan [เรื่อง] — วาง action plan\n"
                "/research [หัวข้อ] — ค้นเว็บและสรุป\n"
                "/draft [ประเภท] — ร่างเอกสาร/อีเมล/โพสต์\n"
                "/link-project [ชื่อ] : [path] — ผูกชื่อย่อเข้ากับโฟลเดอร์โปรเจกต์เอกสาร (เช่น NOX_Studio)\n"
                "/continue [ชื่อ|path] — 'Chief Designer Mode': สแกนโฟลเดอร์ เช็คว่าไฟล์ไหนเสร็จแล้ว บอกว่าควรทำอะไรต่อ\n"
                "/lock [ชื่อ] [ไฟล์] — ปิดล็อกไฟล์ว่าเสร็จสมบูรณ์แล้ว (กัน Chief แก้/สร้างซ้ำ)")

    if text.startswith("/link-project "):
        body = text[len("/link-project "):].strip()
        if ":" not in body:
            return "❌ รูปแบบ: /link-project ชื่อโปรเจกต์ : path เต็มของโฟลเดอร์\nเช่น /link-project NOX_Studio : C:\\Users\\Apple\\Documents\\NOX_Studio"
        name, path = [p.strip() for p in body.split(":", 1)]
        nox_save_project_path(name, path)
        return f"✅ เชื่อม '{name}' → {path} แล้ว\nพิมพ์ /continue {name} ได้เลยครั้งต่อไป"

    if text.startswith("/continue"):
        arg = text[len("/continue"):].strip()
        if not arg:
            return "❌ ใช้แบบ: /continue [ชื่อโปรเจกต์ที่เคย /link-project ไว้] หรือ /continue [path เต็ม]"
        project_dir = nox_resolve_project_path(arg)
        if project_dir is None:
            return (f"❌ ไม่พบโฟลเดอร์ '{arg}'\n"
                    f"หมายเหตุ: ฟีเจอร์นี้ใช้ได้เฉพาะตอนรัน Chief ในเครื่องที่มีโฟลเดอร์นี้อยู่จริงเท่านั้น "
                    f"(ใช้ไม่ได้ถ้ารันบน Hugging Face Space)\n"
                    f"ลองผูก path ก่อนด้วย /link-project {arg} : [path เต็ม]")
        return nox_next_action(project_dir)

    if text.startswith("/lock "):
        parts = text[len("/lock "):].strip().split(" ", 1)
        if len(parts) < 2:
            return "❌ ใช้แบบ: /lock [ชื่อโปรเจกต์] [ชื่อไฟล์]"
        proj_name, filename = parts
        project_dir = nox_resolve_project_path(proj_name)
        if project_dir is None:
            return f"❌ ไม่พบโปรเจกต์ '{proj_name}' — เช็คชื่อ หรือ /link-project ก่อน"
        return nox_set_status(project_dir, filename, "Locked")

    if text == "/goals":
        return show_goals()

    if text.startswith("/goal "):
        return save_goal(text[6:].strip())

    if text == "/tasks":
        return show_tasks()

    if text.startswith("/task "):
        return add_task(text[6:].strip())

    if text.startswith("/done "):
        try:
            idx = int(text[6:].strip())
            return complete_task(idx)
        except ValueError:
            return "❌ ใส่เลขงานด้วยครับ เช่น /done 2 (ดูเลขจาก /tasks)"

    if text == "/status":
        return build_status_report()

    if text == "/morning":
        briefing = build_morning_briefing()
        send_telegram_message(briefing)
        return briefing

    if text == "/departments":
        return list_departments()

    if text.startswith("/team "):
        result = run_team_task(text[6:].strip())
        log_decision(text[6:].strip(), result)
        return result

    if text == "/projects":
        return show_projects()

    if text.startswith("/project "):
        return add_project(text[9:].strip())

    if text == "/contacts":
        return show_contacts()

    if text.startswith("/contact "):
        return add_contact(text[9:].strip())

    if text == "/knowledge":
        return show_knowledge()

    if text.startswith("/learn "):
        return add_knowledge(text[7:].strip())

    if text == "/workflows":
        return show_workflows()

    if text.startswith("/workflow "):
        return add_workflow(text[10:].strip())

    if text == "/decisions":
        return show_decisions()

    if text.startswith("/decided "):
        rest = text[9:].strip()
        if " " in rest:
            id_str, choice = rest.split(" ", 1)
            try:
                return record_decision(int(id_str), choice.strip())
            except ValueError:
                return "❌ รูปแบบ: /decided [เลข] [สิ่งที่เลือก] เช่น /decided 1 เลือกแผน A"
        return "❌ รูปแบบ: /decided [เลข] [สิ่งที่เลือก] เช่น /decided 1 เลือกแผน A"

    if text == "/rocks":
        return show_rocks()

    if text.startswith("/rock "):
        return add_rock(text[6:].strip())

    if text.startswith("/rock-status "):
        rest = text[13:].strip()
        if " " in rest:
            id_str, status = rest.split(" ", 1)
            try:
                return set_rock_status(int(id_str), status.strip())
            except ValueError:
                return "❌ รูปแบบ: /rock-status [เลข] [on-track|at-risk|done]"
        return "❌ รูปแบบ: /rock-status [เลข] [on-track|at-risk|done]"

    if text == "/scorecard":
        return show_scorecard()

    if text.startswith("/metric "):
        return add_metric(text[8:].strip())

    if text.startswith("/log "):
        return log_metric(text[5:].strip())

    if text == "/issues":
        return show_issues()

    if text.startswith("/issue "):
        return add_issue(text[7:].strip())

    if text.startswith("/solve "):
        rest = text[7:].strip()
        if " " in rest:
            id_str, resolution = rest.split(" ", 1)
            try:
                return solve_issue(int(id_str), resolution.strip())
            except ValueError:
                return "❌ รูปแบบ: /solve [เลข] [วิธีแก้] เช่น /solve 1 คุยกับทีมแล้วปรับ SLA"
        return "❌ รูปแบบ: /solve [เลข] [วิธีแก้] เช่น /solve 1 คุยกับทีมแล้วปรับ SLA"

    return None


# ---- คำสั่งที่ไม่ตอบทันที แต่แปลงเป็น prompt แล้วส่งต่อให้ AI (เหมือน CLI) ----
def expand_ai_command(text):
    if text.startswith("/research "):
        query = text[10:].strip()
        search_result = web_search(query)
        return f"ค้นหาข้อมูลเรื่อง '{query}' และได้ผลลัพธ์นี้:\n{search_result}\n\nสรุปและวิเคราะห์ให้หน่อย พร้อม insight ที่เกี่ยวกับเป้าหมายของฉัน"
    if text.startswith("/plan "):
        topic = text[6:].strip()
        return f"ช่วยวาง action plan สำหรับ '{topic}' ให้หน่อย แตกเป็น steps ชัดเจน พร้อม timeline และเจ้าของ task"
    if text.startswith("/decide "):
        problem = text[8:].strip()
        return f"ช่วยวิเคราะห์ปัญหา '{problem}' ให้หน่อย เสนอทางเลือกพร้อม pros/cons และแนะนำว่าควรเลือกอะไร"
    if text.startswith("/draft "):
        doc_type = text[7:].strip()
        return f"ช่วยร่าง {doc_type} ให้หน่อย ในสไตล์ที่เหมาะสม professional และ effective"
    return text


# ============================================================
# FUNCTION CALLING — ให้ AI เรียกฟังก์ชันจริงใน memory/store.py ได้เอง
# ตอนคุยแบบภาษาธรรมชาติ (ไม่ใช่แค่พิมพ์ slash command ตรงตัวเท่านั้น)
#
# ก่อนหน้านี้ client.chat.completions.create(...) ไม่เคยส่ง tools=
# เข้าไปเลย ทำให้ GPT "พูดว่าจะทำ" ได้อย่างเดียว แต่เรียกฟังก์ชันจริง
# ไม่ได้ — ส่วนนี้คือการต่อ "สมอง" (GPT) เข้ากับ "มือ" (ฟังก์ชันจริง)
# ============================================================
def _tool(name, description, properties, required=None):
    """สร้าง OpenAI tool schema แบบสั้นๆ ลดโค้ดซ้ำ"""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required if required is not None else list(properties.keys()),
            },
        },
    }


# ---- shim ฟังก์ชัน: บางฟังก์ชันจริงรับ string รูปแบบเฉพาะ (เช่น "ชื่อ : ค่า")
# แต่อยากให้ AI ส่ง argument แยกฟิลด์ชัดเจนแทนการยัด string เดียวเอง จะได้แม่นยำกว่า ----
def _tool_add_client(name, note=""):
    text = f"{name}|{note}" if note else name
    return add_client(text)

def _tool_add_event(title, when):
    return add_event(f"{title} : {when}")

def _tool_set_preference(key, value):
    return set_preference(f"{key} : {value}")

def _tool_add_workflow(name, steps=None):
    steps = steps or []
    text = f"{name} : {', '.join(steps)}" if steps else name
    return add_workflow(text)


TOOLS = [
    # ---- action ที่แก้ไขข้อมูลจริง ----
    _tool("add_task", "บันทึกงานใหม่ที่ต้องทำ", {
        "task_text": {"type": "string", "description": "รายละเอียดของงานที่ต้องทำ"}
    }),
    _tool("complete_task", "ปิดงานที่ทำเสร็จแล้ว โดยใช้เลขลำดับงาน", {
        "index": {"type": "integer", "description": "เลขลำดับของงาน (ดูจาก show_tasks)"}
    }),
    _tool("save_goal", "บันทึกเป้าหมายใหม่ของเจ้าของ", {
        "goal_text": {"type": "string", "description": "เนื้อหาของเป้าหมาย"}
    }),
    _tool("add_project", "เพิ่มโปรเจกต์ใหม่เข้าระบบ", {
        "name": {"type": "string", "description": "ชื่อโปรเจกต์"}
    }),
    _tool("add_client_tool", "เพิ่มลูกค้า/ผู้ติดต่อใหม่", {
        "name": {"type": "string", "description": "ชื่อลูกค้า"},
        "note": {"type": "string", "description": "โน้ตเพิ่มเติมเกี่ยวกับลูกค้า (ถ้ามี)"},
    }, required=["name"]),
    _tool("add_event_tool", "เพิ่มนัดหมาย/เดดไลน์ลงปฏิทิน", {
        "title": {"type": "string", "description": "ชื่อนัดหมาย"},
        "when": {"type": "string", "description": "วันเวลาของนัด เช่น 2026-08-10 14:00"},
    }),
    _tool("set_preference_tool", "บันทึกนิสัย/วิธีทำงานของเจ้าของ ให้ Chief ปรับตัวเข้าหา", {
        "key": {"type": "string", "description": "หัวข้อของนิสัย/วิธีทำงาน"},
        "value": {"type": "string", "description": "รายละเอียด"},
    }),
    _tool("add_knowledge", "บันทึกความรู้/บริบทใหม่ที่ Chief ควรจำไว้", {
        "fact": {"type": "string", "description": "ข้อมูล/บริบทที่ต้องการให้ Chief จำ"}
    }),
    _tool("add_workflow_tool", "บันทึก workflow/SOP ใหม่", {
        "name": {"type": "string", "description": "ชื่อ workflow"},
        "steps": {
            "type": "array",
            "items": {"type": "string"},
            "description": "รายการขั้นตอนของ workflow ตามลำดับ",
        },
    }, required=["name"]),
    _tool("add_rock", "เพิ่ม Rock (เป้าหมายใหญ่ระดับบริษัทของไตรมาสนี้)", {
        "title": {"type": "string", "description": "ชื่อ Rock"}
    }),
    _tool("set_rock_status", "อัปเดตสถานะของ Rock", {
        "rock_id": {"type": "integer", "description": "เลข ID ของ Rock (ดูจาก show_rocks)"},
        "status": {"type": "string", "enum": ["on-track", "at-risk", "done"], "description": "สถานะใหม่"},
    }),
    _tool("add_metric", "สร้างตัวชี้วัด (metric) ใหม่ใน Scorecard พร้อมเป้าหมาย", {
        "text": {"type": "string", "description": "รูปแบบ 'ชื่อ metric : เป้าหมาย' เช่น 'ยอดขายใหม่ : 20'"}
    }),
    _tool("log_metric", "บันทึกค่าตัวชี้วัดของสัปดาห์นี้", {
        "text": {"type": "string", "description": "รูปแบบ 'ชื่อ metric : ค่า' เช่น 'ยอดขายใหม่ : 15'"}
    }),
    _tool("add_issue", "บันทึกปัญหาใหม่ที่ยังไม่ได้แก้", {
        "title": {"type": "string", "description": "รายละเอียดปัญหา"}
    }),
    _tool("solve_issue", "ปิดปัญหาที่แก้ไขแล้ว", {
        "issue_id": {"type": "integer", "description": "เลข ID ของปัญหา (ดูจาก show_issues)"},
        "resolution": {"type": "string", "description": "วิธีที่ใช้แก้ปัญหานี้"},
    }),
    _tool("record_decision", "บันทึกว่าเจ้าของตัดสินใจเลือกอะไรไปแล้ว สำหรับเรื่องที่เคยบันทึกไว้ใน decisions log", {
        "decision_id": {"type": "integer", "description": "เลข ID ของเรื่องที่ตัดสินใจ (ดูจาก show_decisions)"},
        "choice_text": {"type": "string", "description": "สิ่งที่เจ้าของเลือก"},
    }),
    _tool("run_team_task", "ส่งงานให้ทีมหลายแผนกช่วยวิเคราะห์พร้อมกันแล้วสรุปความเห็นกลับมา ใช้เมื่อคำถามซับซ้อน กว้าง หรือกระทบหลายแผนก", {
        "request": {"type": "string", "description": "รายละเอียดงาน/คำถามที่ต้องการให้ทีมช่วยวิเคราะห์"}
    }),
    _tool("web_search", "ค้นหาข้อมูลจากเว็บ ใช้เมื่อข้อมูลที่มีอยู่ในระบบไม่พอตอบคำถาม", {
        "query": {"type": "string", "description": "คำค้นหา"}
    }),
    # ---- read-only lookup ที่ยังไม่ได้อยู่ใน system prompt context อยู่แล้ว ----
    _tool("show_clients", "แสดงรายชื่อลูกค้า/ผู้ติดต่อทั้งหมด", {}, required=[]),
    _tool("show_calendar", "แสดงตารางนัดหมายทั้งหมด", {}, required=[]),
    _tool("show_timeline", "แสดงเหตุการณ์ล่าสุดที่เกิดขึ้นในระบบ", {}, required=[]),
    _tool("list_departments", "แสดงรายชื่อแผนกทั้งหมดที่เรียกใช้ผ่าน /team ได้", {}, required=[]),
    _tool("show_projects", "แสดงโปรเจกต์ทั้งหมด", {}, required=[]),
    _tool("show_workflows", "แสดง workflow/SOP ทั้งหมดที่เคยบันทึกไว้", {}, required=[]),
    _tool("show_decisions", "แสดงรายการเรื่องที่รอ/ตัดสินใจไปแล้วทั้งหมด", {}, required=[]),
]

TOOL_DISPATCH = {
    "add_task": lambda **kw: add_task(kw["task_text"]),
    "complete_task": lambda **kw: complete_task(int(kw["index"])),
    "save_goal": lambda **kw: save_goal(kw["goal_text"]),
    "add_project": lambda **kw: add_project(kw["name"]),
    "add_client_tool": lambda **kw: _tool_add_client(kw["name"], kw.get("note", "")),
    "add_event_tool": lambda **kw: _tool_add_event(kw["title"], kw["when"]),
    "set_preference_tool": lambda **kw: _tool_set_preference(kw["key"], kw["value"]),
    "add_knowledge": lambda **kw: add_knowledge(kw["fact"]),
    "add_workflow_tool": lambda **kw: _tool_add_workflow(kw["name"], kw.get("steps")),
    "add_rock": lambda **kw: add_rock(kw["title"]),
    "set_rock_status": lambda **kw: set_rock_status(int(kw["rock_id"]), kw["status"]),
    "add_metric": lambda **kw: add_metric(kw["text"]),
    "log_metric": lambda **kw: log_metric(kw["text"]),
    "add_issue": lambda **kw: add_issue(kw["title"]),
    "solve_issue": lambda **kw: solve_issue(int(kw["issue_id"]), kw["resolution"]),
    "record_decision": lambda **kw: record_decision(int(kw["decision_id"]), kw["choice_text"]),
    "run_team_task": lambda **kw: run_team_task(kw["request"]),
    "web_search": lambda **kw: web_search(kw["query"]),
    "show_clients": lambda **kw: show_clients(),
    "show_calendar": lambda **kw: show_calendar(),
    "show_timeline": lambda **kw: show_timeline(),
    "list_departments": lambda **kw: list_departments(),
    "show_projects": lambda **kw: show_projects(),
    "show_workflows": lambda **kw: show_workflows(),
    "show_decisions": lambda **kw: show_decisions(),
}

MAX_TOOL_ROUNDS = 5  # กันไม่ให้ AI เรียก tool วนไม่รู้จบ (ผิดปกติ) — บังคับสรุปคำตอบหลังครบรอบ


def execute_tool_call(tool_call):
    """รันฟังก์ชันจริงตามที่ AI ขอ คืนผลลัพธ์เป็น string เสมอ (กัน error ไม่ให้ทั้งเทิร์นพัง)"""
    name = tool_call.function.name
    try:
        args = json.loads(tool_call.function.arguments or "{}")
    except json.JSONDecodeError:
        return f"❌ อ่านพารามิเตอร์ของ {name} ไม่สำเร็จ"

    fn = TOOL_DISPATCH.get(name)
    if fn is None:
        return f"❌ ไม่รู้จักฟังก์ชัน {name}"

    try:
        result = fn(**args)
        return str(result)
    except Exception as e:
        return f"❌ เรียก {name} ไม่สำเร็จ: {e}"


# ============================================================
# VOICE INTERACTION — thin layer over the existing chat() pipeline
# ============================================================
def speech_to_text(audio_path):
    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    return transcript.text.strip()


def text_to_speech(text):
    if not text or not text.strip():
        return None

    audio_path = os.path.join(
        tempfile.gettempdir(),
        f"vyada_voice_response_{os.getpid()}.mp3"
    )

    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text,
        response_format="mp3"
    )
    response.stream_to_file(audio_path)

    return audio_path


def voice_chat(audio_path, chat_history):
    print(f"[voice_chat] audio_path received: {audio_path!r}")  # DEBUG: ดูใน HF Space Logs

    if not audio_path:
        no_audio_msg = "⚠️ ไม่พบไฟล์เสียง — ลองกด Record แล้วพูด แล้วกด Stop ก่อนกด 'ส่งเสียง' อีกครั้งครับ"
        updated_history = chat_history + [
            {"role": "assistant", "content": no_audio_msg}
        ]
        return updated_history, None, build_dashboard_html()

    try:
        # Speech-to-Text
        message = speech_to_text(audio_path)

        if not message:
            return chat_history, None, build_dashboard_html()

        # ใช้ chat() เดิมโดยตรง
        updated_history, _, _, dashboard_html = chat(
            message,
            chat_history,
            None
        )

        # ใช้ข้อความตอบกลับล่าสุดสำหรับ Text-to-Speech
        assistant_reply = updated_history[-1]["content"]
        response_audio = text_to_speech(assistant_reply)

        return updated_history, response_audio, dashboard_html

    except Exception as e:
        import traceback
        traceback.print_exc()  # DEBUG: ดูสาเหตุเต็มๆ ใน HF Space Logs
        error_message = f"❌ Voice Error: {e}"
        updated_history = chat_history + [
            {"role": "assistant", "content": error_message}
        ]
        return updated_history, None, build_dashboard_html()


def hands_free_chat(text, chat_history):
    """
    ใช้กับโหมด Hands-free: ข้อความมาจาก Web Speech API ในเบราว์เซอร์
    (ถอดเสียงเป็นข้อความฝั่ง client แล้ว) จึงข้ามขั้นตอน speech_to_text
    ไปเลย ไม่แตะ chief/ หรือ memory/ เหมือน voice_chat เดิม
    """
    if not text or not text.strip():
        return chat_history, None, build_dashboard_html()

    try:
        updated_history, _, _, dashboard_html = chat(text, chat_history, None)
        assistant_reply = updated_history[-1]["content"]
        response_audio = text_to_speech(assistant_reply)
        return updated_history, response_audio, dashboard_html
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_message = f"❌ Hands-free Error: {e}"
        updated_history = chat_history + [
            {"role": "assistant", "content": error_message}
        ]
        return updated_history, None, build_dashboard_html()


# ============================================================
# HOME / "CHIEF DESK" — หน้าแรกแบบ Executive Dashboard
# ใช้ข้อมูล/ฟังก์ชันเดิมทั้งหมด ไม่แตะ memory/ หรือ chief logic เลย
# ============================================================
def build_chief_recommendation():
    """เรียก AI ตัวเดียวกับ chat() แต่ถามคำถามเจาะจงสั้นๆ เพื่อได้คำแนะนำของวันนี้"""
    try:
        messages = [
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": (
                "ดูจาก Rocks, Tasks, Scorecard และ Issues ที่มีอยู่ตอนนี้ "
                "แล้วสรุปสั้นๆ 1-2 ประโยคว่าวันนี้ควรโฟกัสเรื่องอะไรก่อน "
                "ตอบแบบให้คำแนะนำเลยตรงๆ ไม่ต้องถามกลับ ไม่ต้องมีคำนำ"
            )}
        ]
        response = client.chat.completions.create(model=MODEL, messages=messages, max_tokens=200)
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ ยังสร้างคำแนะนำไม่ได้ตอนนี้ ({e}) — ลองกดรีเฟรชอีกครั้ง"


def build_activity_log_html(limit=8):
    """
    Activity Log แบบย่อ แทนกล่องแชทใหญ่ — ดึงจาก conversation_history เดิม
    หมายเหตุ: ระบบยังไม่ได้เก็บ timestamp ต่อข้อความ เลยแสดงแค่ลำดับเหตุการณ์
    (ถ้าอยากได้เวลาแม่นๆ ต้องเพิ่มการบันทึก timestamp ตอน append เข้า conversation_history)
    """
    items = conversation_history[-(limit * 2):]
    if not items:
        return '<div class="activity-log empty">ยังไม่มีกิจกรรมวันนี้</div>'

    rows = []
    for m in items:
        role = "You" if m["role"] == "user" else "Chief"
        content = m["content"] if isinstance(m["content"], str) else str(m["content"])
        text = content.strip().replace("\n", " ")
        if len(text) > 90:
            text = text[:90] + "…"
        icon = "🗣️" if role == "You" else "🤖"
        rows.append(
            f'<div class="activity-row"><span class="activity-icon">{icon}</span>'
            f'<span class="activity-role">{role}</span>'
            f'<span class="activity-text">{text}</span></div>'
        )
    return '<div class="activity-log">' + "".join(reversed(rows)) + '</div>'


def refresh_home_widgets():
    """เรียกซ้ำหลัง event ต่างๆ เพื่อให้ Home tab อัปเดตตาม โดยไม่ต้องแก้ฟังก์ชันเดิม"""
    return build_dashboard_html(), build_activity_log_html()


def log_recommendation_action(action_label, recommendation_text):
    """บันทึกว่า Approve/Reject/Review คำแนะนำอะไรไป ให้ขึ้นใน Activity Log
    (เป็น stub เบื้องต้น — ยังไม่ได้ผูกกับระบบ decision log เต็มรูปแบบ)"""
    note = f"{action_label}: {recommendation_text}"
    conversation_history.append({"role": "user", "content": f"[Chief Recommendation] {action_label}"})
    conversation_history.append({"role": "assistant", "content": f"รับทราบครับ — {note}"})
    save_history(conversation_history)
    return build_activity_log_html()


# ============================================================
# MORNING BRIEFING LOADER — ต้องนิยามที่นี่ (นอก with gr.Blocks())
# เพราะเป็นแค่ plain helper function ไม่ใช่ส่วนของ UI layout
# ถ้าไปแทรกกลาง `with gr.Blocks()` จะทำให้ Python ตัดบล็อกนั้น
# แล้วโค้ด event wiring ที่ตามมาจะพังด้วย IndentationError
# ============================================================
def show_morning_briefing():
    try:
        briefing = build_morning_briefing()
    except Exception as e:
        import traceback
        traceback.print_exc()
        briefing = f"❌ build_morning_briefing() Error: {e}"
        conversation_history.append({"role": "assistant", "content": briefing})
        save_history(conversation_history)
        return [{"role": "assistant", "content": briefing}], build_dashboard_html()

    try:
        send_telegram_message(briefing)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Telegram Error: {e}")

    conversation_history.append({"role": "assistant", "content": briefing})
    save_history(conversation_history)
    return [{"role": "assistant", "content": briefing}], build_dashboard_html()


# ============================================================
# DASHBOARD — แผงตัวเลขสด ให้ความรู้สึกเปิดมาแล้วเจอออฟฟิศ ไม่ใช่แค่แชท
# ============================================================
def build_dashboard_html():
    tasks = load_tasks()
    open_tasks = len([t for t in tasks if t["status"] != "done"])
    stale = len(get_stale_tasks())

    q = current_quarter()
    rocks_q = [r for r in load_rocks() if r["quarter"] == q]
    at_risk = len([r for r in rocks_q if r["status"] == "at-risk"])
    done_rocks = len([r for r in rocks_q if r["status"] == "done"])

    metrics = load_scorecard()
    off_target = len(get_off_target_metrics())

    open_issues = get_open_issues_count()
    pending_dec = pending_decisions_count()

    def card(icon, label, value, sub, warn=False):
        cls = "stat-card warn" if warn else "stat-card"
        return f'''<div class="{cls}">
            <div class="stat-icon">{icon}</div>
            <div class="stat-value">{value}</div>
            <div class="stat-label">{label}</div>
            <div class="stat-sub">{sub}</div>
        </div>'''

    cards = [
        card("🪨", "Rocks", str(len(rocks_q)), f"ไตรมาส {q}" + (f" · {at_risk} at-risk" if at_risk else f" · {done_rocks} เสร็จแล้ว" if done_rocks else ""), warn=at_risk > 0),
        card("📋", "งานเปิดอยู่", str(open_tasks), f"{stale} นิ่งไปนาน" if stale else "อัปเดตล่าสุด", warn=stale > 0),
        card("📈", "Scorecard", str(len(metrics)), f"{off_target} ต่ำกว่าเป้า" if off_target else "ทุกตัวถึงเป้า" if metrics else "ยังไม่ตั้งตัวชี้วัด", warn=off_target > 0),
        card("🚩", "Issues", str(open_issues), "ยังไม่แก้" if open_issues else "ไม่มีปัญหาค้าง", warn=open_issues > 0),
        card("⚖️", "รอตัดสินใจ", str(pending_dec), "Decisions" if pending_dec else "ไม่มีเรื่องค้าง", warn=pending_dec > 0),
    ]

    return f'<div class="dashboard">{"".join(cards)}</div>'


# ============================================================
# CHAT FUNCTION
# ============================================================
def chat(message, chat_history, image):
    try:
        original_message = message or ""
        stripped = original_message.strip()

        if stripped == "/clear":
            return clear_chat()

        # ---- คำสั่งที่ทำงานทันที ไม่ต้องเรียก AI (ไม่รองรับพร้อมรูปภาพ) ----
        if stripped and not image:
            cmd_result = handle_command(stripped)
            if cmd_result is not None:
                conversation_history.append({"role": "user", "content": original_message})
                conversation_history.append({"role": "assistant", "content": cmd_result})
                save_history(conversation_history)
                chat_history = chat_history + [
                    {"role": "user", "content": original_message},
                    {"role": "assistant", "content": cmd_result}
                ]
                return chat_history, "", None, build_dashboard_html()

            message = expand_ai_command(stripped)

        messages = [{"role": "system", "content": build_system_prompt()}]
        messages.extend(conversation_history[-20:])

        if image is not None:
            from PIL import Image
            img = Image.open(image)
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            img_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            user_content = [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                {"type": "text", "text": message if message.strip() else "วิเคราะห์รูปภาพนี้ให้หน่อยครับ"}
            ]
        else:
            user_content = message

        messages.append({"role": "user", "content": user_content})

        # ---- Function-calling loop: ให้ AI เรียกฟังก์ชันจริงได้เอง ไม่ใช่แค่ตอบข้อความ ----
        agent_reply = None
        tool_rounds = 0
        while True:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=1500
            )
            response_msg = response.choices[0].message

            if not response_msg.tool_calls:
                agent_reply = response_msg.content
                break

            # AI ขอเรียกฟังก์ชันจริง — เก็บ assistant message ที่มี tool_calls เข้า history ก่อน
            messages.append({
                "role": "assistant",
                "content": response_msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in response_msg.tool_calls
                ],
            })

            # รันฟังก์ชันจริงทีละตัว แล้วส่งผลลัพธ์กลับเข้า messages ด้วย role "tool"
            for tc in response_msg.tool_calls:
                result_text = execute_tool_call(tc)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_text,
                })

            tool_rounds += 1
            if tool_rounds >= MAX_TOOL_ROUNDS:
                # ครบรอบที่กันไว้แล้ว — บังคับให้สรุปคำตอบสุดท้าย ไม่ให้เรียก tool เพิ่มอีก
                final_response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    max_tokens=1500
                )
                agent_reply = final_response.choices[0].message.content
                break

        conversation_history.append({"role": "user", "content": message or "[ส่งรูปภาพ]"})
        conversation_history.append({"role": "assistant", "content": agent_reply})
        save_history(conversation_history)

        if stripped.startswith("/decide "):
            log_decision(stripped[8:].strip(), agent_reply)
            agent_reply += "\n\n📌 บันทึกไว้ใน decisions log แล้ว — พิมพ์ /decisions เพื่อดู หรือ /decided [เลข] [สิ่งที่เลือก] เมื่อคุณตัดสินใจแล้ว"

        display_msg = f"📷 {original_message}" if (image and original_message.strip()) else ("📷 [ส่งรูปภาพ]" if image else original_message)
        chat_history = chat_history + [
            {"role": "user", "content": display_msg},
            {"role": "assistant", "content": agent_reply}
        ]
        return chat_history, "", None, build_dashboard_html()

    except Exception as e:
        chat_history = chat_history + [
            {"role": "user", "content": message or ""},
            {"role": "assistant", "content": f"❌ Error: {e}"}
        ]
        return chat_history, "", None, build_dashboard_html()


def clear_chat():
    global conversation_history
    conversation_history = []
    save_history([])
    return [], "", None, build_dashboard_html()


# ============================================================
# CSS
# ============================================================
css = """
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg: #0c0f13;
    --surface: #12161c;
    --surface-raised: #181d25;
    --border: #262d38;
    --ink: #eae7de;
    --muted: #6b7480;
    --brass: #c9a769;
    --brass-bright: #e8c98a;
    --teal: #52c7ae;
}

body, .gradio-container { background: var(--bg) !important; font-family: 'Inter', sans-serif !important; color: var(--ink) !important; }

.wrap-col { max-width: 780px; margin: 0 auto; padding: 0 1rem 3rem; }

/* ---------- LETTERHEAD HEADER ---------- */
.app-header { text-align: center; padding: 2.6rem 1rem 1.6rem; position: relative; }
.app-header .kicker { font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; letter-spacing: 4px; text-transform: uppercase; color: var(--muted); margin: 0 0 10px; }
.app-header h1 { font-family: 'Fraunces', serif; font-optical-sizing: auto; font-size: 3.4rem; font-weight: 600; letter-spacing: -0.01em; color: var(--ink); margin: 0; line-height: 1; }
.app-header h1 span { background: linear-gradient(120deg, var(--brass) 10%, var(--brass-bright) 50%, var(--brass) 90%); -webkit-background-clip: text; background-clip: text; color: transparent; }
.app-header .role { font-size: 0.85rem; color: var(--muted); margin: 10px 0 0; font-family: 'Inter', sans-serif; }
.app-header .role b { color: var(--ink); font-weight: 500; }
.rule { max-width: 340px; margin: 20px auto 0; height: 3px; background: linear-gradient(90deg, transparent, var(--border) 20%, var(--border) 80%, transparent); position: relative; }
.rule::after { content: ""; position: absolute; top: 6px; left: 50%; transform: translateX(-50%); width: 200px; height: 1px; background: linear-gradient(90deg, transparent, var(--border) 20%, var(--border) 80%, transparent); }

/* ---------- ORG STRIP (breadcrumb of the real hierarchy) ---------- */
.org-strip { display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 6px; margin: 22px 0 4px; font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; }
.org-chip { padding: 4px 11px; border: 1px solid var(--border); border-radius: 20px; color: var(--muted); background: var(--surface); }
.org-chip.lead { color: var(--brass-bright); border-color: rgba(201,167,105,0.4); }
.org-sep { color: var(--border); }

/* ---------- STATUS BAR ---------- */
.status-bar { display: flex; align-items: center; justify-content: center; gap: 9px; padding: 7px 16px; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; font-size: 0.7rem; color: var(--muted); font-family: 'JetBrains Mono', monospace; margin: 18px 0 14px; }
.dot { width: 6px; height: 6px; border-radius: 50%; background: var(--teal); box-shadow: 0 0 7px var(--teal); animation: blink 2.2s ease-in-out infinite; }

/* ---------- DASHBOARD (office-board feel) ---------- */
.dashboard { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin-bottom: 16px; }
.stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 12px 10px; text-align: center; transition: border-color .2s, transform .2s; }
.stat-card:hover { border-color: rgba(201,167,105,0.4); transform: translateY(-1px); }
.stat-card.warn { border-color: rgba(201,167,105,0.55); background: linear-gradient(180deg, rgba(201,167,105,0.07), var(--surface) 60%); }
.stat-icon { font-size: 1.05rem; margin-bottom: 2px; opacity: 0.9; }
.stat-value { font-family: 'Fraunces', serif; font-size: 1.7rem; font-weight: 600; color: var(--ink); line-height: 1; }
.stat-card.warn .stat-value { color: var(--brass-bright); }
.stat-label { font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; letter-spacing: 1px; text-transform: uppercase; color: var(--muted); margin-top: 4px; }
.stat-sub { font-size: 0.68rem; color: #4a5058; margin-top: 2px; }
.stat-card.warn .stat-sub { color: var(--brass); }
@media (max-width: 640px) { .dashboard { grid-template-columns: repeat(2, 1fr); } }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.35} }

/* ---------- CHAT PANEL ---------- */
#chatbot { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 16px !important; height: 500px !important; box-shadow: 0 20px 50px -30px rgba(0,0,0,0.6) !important; }

#msg-box textarea { background: var(--surface-raised) !important; border: 1px solid var(--border) !important; border-radius: 14px !important; color: var(--ink) !important; font-size: 0.92rem !important; padding: 12px 16px !important; resize: none !important; transition: border-color .15s, box-shadow .15s !important; }
#msg-box textarea:focus { border-color: var(--brass) !important; box-shadow: 0 0 0 3px rgba(201,167,105,0.15) !important; outline: none !important; }
#msg-box textarea::placeholder { color: #4a5058 !important; }

#image-upload { border: 1px dashed var(--border) !important; border-radius: 14px !important; background: var(--surface-raised) !important; }

#send-btn { background: var(--brass) !important; border: none !important; border-radius: 12px !important; color: #14110a !important; font-weight: 600 !important; font-size: 0.9rem !important; transition: background .15s, box-shadow .15s !important; }
#send-btn:hover { background: var(--brass-bright) !important; box-shadow: 0 0 20px rgba(201,167,105,0.35) !important; }
#clear-btn { background: transparent !important; border: 1px solid var(--border) !important; border-radius: 12px !important; color: var(--muted) !important; font-size: 0.86rem !important; }
#clear-btn:hover { border-color: var(--muted) !important; color: var(--ink) !important; }

/* ---------- COMMAND CLUSTERS ---------- */
.cmd-wrap { margin-top: 14px; }
.cmd-group { margin-bottom: 8px; }
.cmd-label { font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; letter-spacing: 2px; text-transform: uppercase; color: #454b54; margin: 0 0 5px 2px; }
.cmd-row { display: flex; flex-wrap: wrap; gap: 6px; }
.cmd-btn { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 20px !important; color: var(--muted) !important; font-size: 0.72rem !important; padding: 4px 13px !important; font-family: 'JetBrains Mono', monospace !important; cursor: pointer !important; transition: all .15s !important; }
.cmd-btn:hover { border-color: var(--brass) !important; color: var(--brass-bright) !important; background: rgba(201,167,105,0.08) !important; }

footer, .built-with { display: none !important; }
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--brass); }

/* ---------- HOME / CHIEF DESK ---------- */
.chief-desk-header { text-align: center; padding: 1rem 0 0.4rem; }
.chief-desk-header .kicker { font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; letter-spacing: 3px; text-transform: uppercase; color: var(--muted); margin: 0 0 6px; }
.chief-desk-header h2 { font-family: 'Fraunces', serif; font-size: 1.9rem; font-weight: 600; color: var(--ink); margin: 0; }
.chief-desk-header .date-line { font-size: 0.8rem; color: var(--muted); margin: 4px 0 0; }

.activity-log { display: flex; flex-direction: column; gap: 6px; max-height: 260px; overflow-y: auto; padding: 10px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; }
.activity-log.empty { color: var(--muted); font-size: 0.85rem; text-align: center; padding: 20px; }
.activity-row { display: flex; align-items: baseline; gap: 8px; font-size: 0.82rem; padding: 4px 2px; border-bottom: 1px solid var(--border); }
.activity-row:last-child { border-bottom: none; }
.activity-icon { flex-shrink: 0; }
.activity-role { font-weight: 600; color: var(--brass-bright); flex-shrink: 0; }
.activity-text { color: var(--muted); }
"""

# ============================================================
# UI — Gradio 6.x
# ============================================================
_org_chips = "".join([f'<span class="org-chip">{d["name"]}</span><span class="org-sep">/</span>' for d in DEPARTMENTS.values()])[:-len('<span class="org-sep">/</span>')]

_head_script = r"""
<script>
function fillCmd(cmd) {
    const ta = document.querySelector('#msg-box textarea');
    if (ta) { ta.value = cmd; ta.focus(); ta.dispatchEvent(new Event('input', {bubbles:true})); }
}

// ============================================================
// HANDS-FREE MODE — ฟังตลอดเวลาผ่าน Web Speech API ของเบราว์เซอร์
// (ฟรี, ทำงานฝั่ง client, ไม่เสีย API cost จนกว่าจะได้ยินคำปลุก)
// รองรับดีสุดบน Chrome (desktop/Android). Safari/iOS จำกัดมาก
// ============================================================
let hf_recognition = null;
let hf_active = false;

const HF_WAKE_WORDS = ['เฮ้ชีฟ', 'เฮ้ ชีฟ', 'hey chief', 'เฮ้ไวยดา', 'เฮ้ vyada', 'okay chief', 'โอเคชีฟ', 'vyada', 'ไวยดา'];

// ============================================================
// INTENT MAP — ฟังเฉพาะประโยคเหล่านี้เท่านั้น (ไม่ตีความทุกอย่างที่พูด)
// triggers: คำ/ประโยคที่ถ้าเจอใน transcript ถือว่าตรง (substring match)
// prefix: true = ตัดคำ trigger ออกแล้วเอาข้อความที่เหลือมาต่อท้าย (สำหรับคำสั่งที่มีรายละเอียดต่อท้าย)
// prompt: ข้อความเต็มที่จะส่งเข้า Chief จริงๆ (ให้ AI ทำงานตามเจตนา ไม่ใช่แค่คำสั้นๆ)
// ============================================================
const HF_INTENTS = [
    { triggers: ['วันนี้บริษัทเป็นยังไง'],
      prompt: 'สรุปภาพรวมบริษัทวันนี้: KPI, งานด่วน, ความเสี่ยง, และสิ่งที่ควรทำก่อน' },
    { triggers: ['สรุปเช้านี้', 'สรุปตอนเช้า'],
      prompt: 'ทำ Morning Briefing: Calendar, Rocks, และ Priority วันนี้' },
    { triggers: ['วันนี้ฉันควรทำอะไรก่อน', 'วันนี้ทำอะไรก่อนดี'],
      prompt: 'วิเคราะห์ Priorities วันนี้ จัดลำดับงาน พร้อมให้เหตุผล' },
    { triggers: ['เพิ่มงาน'], prefix: true,
      prompt: (rest) => `สร้าง Task ใหม่: "${rest}" กำหนด Priority ให้เหมาะสม และถาม Deadline ถ้ายังไม่มี` },
    { triggers: ['งานค้างมีอะไร', 'งานค้างมีอะไรบ้าง'],
      prompt: 'แสดงงานค้างทั้งหมด เรียงตามความสำคัญ' },
    { triggers: ['งานเสี่ยง'],
      prompt: 'วิเคราะห์งานที่ใกล้ Deadline และมีความเสี่ยง พร้อมแจ้งเตือน' },
    { triggers: ['บริษัทตอนนี้เป็นยังไง'],
      prompt: 'แสดง Scorecard, Rocks, Issues และ Projects ของบริษัทตอนนี้' },
    { triggers: ['มีปัญหาอะไร', 'มีปัญหาอะไรบ้าง'],
      prompt: 'เปิดรายการ Issues ทั้งหมด พร้อมเสนอวิธีแก้' },
    { triggers: ['เป้าหมายไตรมาสนี้'],
      prompt: 'แสดง Rocks ไตรมาสนี้พร้อมเปอร์เซ็นต์ความคืบหน้า' },
    { triggers: ['เรียก cto', 'เรียกซีทีโอ'],
      prompt: 'สลับเป็น CTO Mode' },
    { triggers: ['เรียก marketing', 'เรียกมาร์เก็ตติ้ง'],
      prompt: 'สลับเป็น Marketing และวิเคราะห์งานด้าน Marketing' },
    { triggers: ['เรียก sales', 'เรียกเซลส์'],
      prompt: 'สลับเป็น Sales และวิเคราะห์ยอดขาย' },
    { triggers: ['ประชุมทีม'],
      prompt: 'ให้ทุก Agent (CEO, CTO, Marketing, Sales, CFO) แสดงความคิดเห็นเกี่ยวกับสถานการณ์ตอนนี้' },
    { triggers: ['ช่วยหาข้อมูล'], prefix: true,
      prompt: (rest) => `ช่วย Research เรื่อง: "${rest}" สรุปพร้อมแหล่งอ้างอิง` },
    { triggers: ['วิเคราะห์คู่แข่ง'],
      prompt: 'Research คู่แข่งและทำ SWOT analysis' },
    { triggers: ['เงินสดเหลือเท่าไหร่', 'เงินสดเหลือเท่าไร'],
      prompt: 'แสดง Cash คงเหลือ และ Burn Rate ปัจจุบัน' },
    { triggers: ['เดือนนี้เป็นยังไง'],
      prompt: 'สรุปรายรับ รายจ่าย และกำไรเดือนนี้' },
    { triggers: ['ฉันควรโฟกัสอะไร'],
      prompt: 'วิเคราะห์ทั้งบริษัทแล้วแนะนำ 3 เรื่องที่ควรโฟกัส' },
    { triggers: ['ถ้าเป็น ceo จะทำอะไร', 'ถ้าเป็นซีอีโอจะทำอะไร'],
      prompt: 'วิเคราะห์สถานการณ์แล้วเสนอ Action Plan แบบที่ CEO ควรทำ' },
    { triggers: ['บริษัทเสี่ยงตรงไหน'],
      prompt: 'วิเคราะห์ Risk ของบริษัทตอนนี้ทั้งหมด' },
    { triggers: ['จัดการให้เลย'],
      prompt: 'สร้าง Workflow และมอบหมายทีมที่เกี่ยวข้องให้ทำงานนี้ต่อ' },
    { triggers: ['ทำต่อเอง'],
      prompt: 'ทำ Workflow ที่ค้างอยู่ต่อ แล้วรายงาน Progress' },
    { triggers: ['ดูแลต่อให้ที'],
      prompt: 'วิเคราะห์สถานการณ์ มอบหมายทีมที่เกี่ยวข้อง สร้าง Task หากจำเป็น และแจ้งเฉพาะสิ่งที่ต้องอนุมัติจากฉัน' },
    { triggers: ['คิดแทนฉัน'],
      prompt: 'วิเคราะห์ทางเลือกที่มี เปรียบเทียบข้อดีข้อเสีย แล้วสรุปคำแนะนำพร้อมเหตุผล' },
    { triggers: ['สรุปให้จบ'],
      prompt: 'รวบรวมข้อมูลทั้งหมดที่มี สรุปสาระสำคัญ และเสนอแผนปฏิบัติ 3-5 ขั้นตอนที่ชัดเจน' },
];

function hf_matchIntent(transcript) {
    const lower = transcript.toLowerCase();
    for (const intent of HF_INTENTS) {
        for (const trig of intent.triggers) {
            const idx = lower.indexOf(trig.toLowerCase());
            if (idx !== -1) {
                if (intent.prefix) {
                    const rest = transcript.slice(idx + trig.length).replace(/^[:\s]+/, '').trim();
                    return rest ? intent.prompt(rest) : null; // ต้องมีรายละเอียดต่อท้ายด้วย
                }
                return intent.prompt;
            }
        }
    }
    return null; // ไม่ตรงกับประโยคที่รู้จัก — เงียบ ไม่ทำอะไร
}

function hf_updateIndicator(on) {
    const dot = document.querySelector('#hf-indicator');
    if (dot) {
        dot.style.background = on ? '#22c55e' : '#555';
        dot.title = on ? 'Hands-free: กำลังฟัง...' : 'Hands-free: ปิดอยู่';
    }
}

function hf_sendCommand(text) {
    const box = document.querySelector('#handsfree-box textarea');
    const btn = document.querySelector('#handsfree-send-btn');
    if (box && btn) {
        box.value = text;
        box.dispatchEvent(new Event('input', {bubbles: true}));
        setTimeout(() => btn.click(), 80);
    }
}

function hf_startListening() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert('เบราว์เซอร์นี้ไม่รองรับ Hands-free — ลองใช้ Chrome ครับ');
        return;
    }
    if (hf_active) return;
    hf_active = true;

    hf_recognition = new SpeechRecognition();
    hf_recognition.lang = 'th-TH';
    hf_recognition.continuous = true;
    hf_recognition.interimResults = false;

    hf_recognition.onresult = (event) => {
        const last = event.results[event.results.length - 1];
        const transcript = (last[0].transcript || '').trim();
        console.log('[handsfree] heard:', transcript);
        const lower = transcript.toLowerCase();
        for (const w of HF_WAKE_WORDS) {
            const idx = lower.indexOf(w.toLowerCase());
            if (idx !== -1) {
                const afterWake = transcript.slice(idx + w.length).trim();
                if (afterWake) {
                    const matchedPrompt = hf_matchIntent(afterWake);
                    if (matchedPrompt) {
                        console.log('[handsfree] matched intent, sending:', matchedPrompt);
                        hf_sendCommand(matchedPrompt);
                    } else {
                        console.log('[handsfree] no matching intent — ignored');
                    }
                }
                break;
            }
        }
    };

    hf_recognition.onend = () => {
        // เบราว์เซอร์หยุดฟังเองหลังเงียบไปพักหนึ่ง — เริ่มใหม่อัตโนมัติถ้ายังเปิดโหมดอยู่
        if (hf_active) {
            try { hf_recognition.start(); } catch (e) { /* already starting */ }
        }
    };

    hf_recognition.onerror = (e) => {
        console.warn('[handsfree] error:', e.error);
    };

    hf_recognition.start();
    hf_updateIndicator(true);
}

function hf_stopListening() {
    hf_active = false;
    if (hf_recognition) hf_recognition.stop();
    hf_updateIndicator(false);
}

function hf_toggle() {
    if (hf_active) hf_stopListening();
    else hf_startListening();
}

// ============================================================
// AUTO-SCROLL — เลื่อนกล่องแชทลงล่างสุดอัตโนมัติทุกครั้งที่มีข้อความใหม่
// ไม่ต้องเลื่อนขึ้นไปหาคำตอบเอง
// ============================================================
function hf_scrollChatToBottom() {
    const box = document.querySelector('#chatbot .bubble-wrap, #chatbot [data-testid="bot"], #chatbot .wrap');
    const scrollable = document.querySelector('#chatbot .bubble-wrap') || document.querySelector('#chatbot');
    if (scrollable) {
        scrollable.scrollTop = scrollable.scrollHeight;
    }
}

(function watchChatbot() {
    const target = document.querySelector('#chatbot');
    if (!target) { setTimeout(watchChatbot, 500); return; }
    const observer = new MutationObserver(() => {
        // รอ DOM วาดเสร็จก่อนค่อยเลื่อน
        setTimeout(hf_scrollChatToBottom, 50);
    });
    observer.observe(target, { childList: true, subtree: true });
})();
</script>
"""

with gr.Blocks(title=f"Chief — VYADA Systems · {owner['name']}") as demo:

    gr.HTML(f"""
    <div class="app-header">
        <p class="kicker">VYADA Systems · Executive Console</p>
        <h1>Chief<span>.</span></h1>
        <p class="role">Chief of Staff for <b>{owner['name']}</b> · reports facts and options, never decides for you</p>
        <div class="rule"></div>
        <div class="org-strip">
            <span class="org-chip lead">{owner['name']} (CEO)</span>
            <span class="org-sep">→</span>
            <span class="org-chip lead">Chief of Staff</span>
            <span class="org-sep">→</span>
            {_org_chips}
        </div>
    </div>
    """)

    with gr.Column(elem_classes="wrap-col"):

        with gr.Tabs():
            with gr.Tab("🏠 Home"):
                gr.HTML(f"""
                <div class="chief-desk-header">
                    <p class="kicker">Chief Desk</p>
                    <h2>Good Morning, {owner['name']}</h2>
                    <p class="date-line">{dt_class.now().strftime('%A, %d %B %Y')}</p>
                </div>
                """)

                home_dashboard = gr.HTML(build_dashboard_html())

                gr.Markdown("### Chief Recommendation")
                chief_reco_box = gr.Markdown(build_chief_recommendation())
                with gr.Row():
                    reco_review_btn = gr.Button("🔍 Review", size="sm")
                    reco_approve_btn = gr.Button("✅ Approve", size="sm", variant="primary")
                    reco_ignore_btn = gr.Button("✖️ Ignore", size="sm")
                    reco_refresh_btn = gr.Button("🔄 รีเฟรชคำแนะนำ", size="sm")

                gr.Markdown("### ⚖️ Decision Center")
                decision_center_box = gr.Markdown(show_decisions())

                gr.Markdown("### Activity")
                activity_log_box = gr.HTML(build_activity_log_html())

                gr.Markdown("---")
                with gr.Row():
                    home_speak_btn = gr.Button("🎤 Speak", elem_id="home-speak-btn", scale=1)
                    home_ask_input = gr.Textbox(
                        placeholder="⌨ Ask Chief...",
                        show_label=False,
                        scale=4,
                    )
                    home_ask_btn = gr.Button("➜", scale=0, min_width=50)

            with gr.Tab("💬 Command Center"):
                gr.HTML("""
                <div class="status-bar">
                    <div class="dot"></div>
                    <span>gpt-4.1-mini &nbsp;·&nbsp; connected &nbsp;·&nbsp; vision on</span>
                </div>
                """)

                dashboard = gr.HTML(build_dashboard_html())

                # Gradio 6.x: gr.Chatbot ต้องการ type="messages"
                chatbot = gr.Chatbot(
                    elem_id="chatbot",
                    show_label=False,
                    height=500,
                )

                with gr.Accordion("📎 แนบรูปภาพ (Vision)", open=False):
                    image_input = gr.Image(
                        type="filepath",
                        show_label=False,
                        elem_id="image-upload",
                        height=160,
                    )

                with gr.Accordion("🎙️ Voice Interaction", open=True):
                    voice_input = gr.Audio(
                        sources=["microphone", "upload"],
                        type="filepath",
                        label="พูดกับ Chief",
                    )
                    voice_btn = gr.Button("🎙️ ส่งเสียง", variant="secondary")
                    voice_output = gr.Audio(
                        label="เสียงตอบกลับจาก Chief",
                        autoplay=True,
                        interactive=False,
                    )

                    gr.HTML("""
                    <div style="display:flex; align-items:center; gap:8px; margin-top:10px;">
                        <span id="hf-indicator" title="Hands-free: ปิดอยู่"
                              style="width:10px; height:10px; border-radius:50%; background:#555; display:inline-block;"></span>
                        <span style="font-size:13px; color:#aaa;">
                            พูด "เฮ้ชีฟ ..." ได้เลยหลังเปิดโหมด — ไม่ต้องกดอะไรอีก
                        </span>
                    </div>
                    """)
                    hf_toggle_btn = gr.Button(
                        "🎙️ เปิดโหมด Hands-free (กดครั้งเดียว)",
                        variant="primary",
                        elem_id="hf-toggle-btn",
                    )
                    # กล่อง/ปุ่มที่ซ่อนไว้ — เป็นสะพานให้ JS ยัดข้อความที่ได้ยินเข้าสู่ pipeline
                    # text -> chat() -> text_to_speech เดิม โดยไม่แตะ logic เดิมเลย
                    handsfree_input = gr.Textbox(elem_id="handsfree-box", visible=False, lines=1)
                    handsfree_send_btn = gr.Button("hf-send", elem_id="handsfree-send-btn", visible=False)

                with gr.Row():
                    msg = gr.Textbox(
                        placeholder="พิมพ์ข้อความ หรือ /help /status /team ...",
                        show_label=False,
                        elem_id="msg-box",
                        scale=5,
                        lines=2,
                        max_lines=6,
                    )
                    with gr.Column(scale=1, min_width=90):
                        send_btn = gr.Button("ส่ง ⚡", elem_id="send-btn")
                        clear_btn = gr.Button("🗑 ล้าง", elem_id="clear-btn")

                gr.HTML("""
                <div class="cmd-wrap">
                    <div class="cmd-group">
                        <p class="cmd-label">ติดตามงาน</p>
                        <div class="cmd-row">
                            <button class="cmd-btn" onclick="fillCmd('/status')">/status</button>
                            <button class="cmd-btn" onclick="fillCmd('/tasks')">/tasks</button>
                            <button class="cmd-btn" onclick="fillCmd('/task ')">/task</button>
                            <button class="cmd-btn" onclick="fillCmd('/goals')">/goals</button>
                        </div>
                    </div>
                    <div class="cmd-group">
                        <p class="cmd-label">งานเชิงลึก</p>
                        <div class="cmd-row">
                            <button class="cmd-btn" onclick="fillCmd('/plan ')">/plan</button>
                            <button class="cmd-btn" onclick="fillCmd('/research ')">/research</button>
                            <button class="cmd-btn" onclick="fillCmd('/decide ')">/decide</button>
                            <button class="cmd-btn" onclick="fillCmd('/draft ')">/draft</button>
                        </div>
                    </div>
                    <div class="cmd-group">
                        <p class="cmd-label">Company OS</p>
                        <div class="cmd-row">
                            <button class="cmd-btn" onclick="fillCmd('/rocks')">/rocks</button>
                            <button class="cmd-btn" onclick="fillCmd('/rock ')">/rock</button>
                            <button class="cmd-btn" onclick="fillCmd('/scorecard')">/scorecard</button>
                            <button class="cmd-btn" onclick="fillCmd('/log ')">/log</button>
                            <button class="cmd-btn" onclick="fillCmd('/issues')">/issues</button>
                            <button class="cmd-btn" onclick="fillCmd('/issue ')">/issue</button>
                        </div>
                    </div>
                    <div class="cmd-group">
                        <p class="cmd-label">ทีมงาน</p>
                        <div class="cmd-row">
                            <button class="cmd-btn" onclick="fillCmd('/departments')">/departments</button>
                            <button class="cmd-btn" onclick="fillCmd('/team ')">/team</button>
                            <button class="cmd-btn" onclick="fillCmd('/help')">/help</button>
                        </div>
                    </div>
                </div>
                """)

    # ================================================================
    # EVENT WIRING — ทุกอย่างเยื้องอยู่ในบล็อก `with gr.Blocks()` เดียวกัน
    # อย่างสม่ำเสมอ (แก้จากเดิมที่บาง .click() หลุดออกไปอยู่นอกบล็อก)
    # ================================================================
    demo.load(show_morning_briefing, inputs=None, outputs=[chatbot, dashboard])
    demo.load(refresh_home_widgets, inputs=None, outputs=[home_dashboard, activity_log_box])

    send_btn.click(chat, inputs=[msg, chatbot, image_input], outputs=[chatbot, msg, image_input, dashboard]) \
        .then(refresh_home_widgets, outputs=[home_dashboard, activity_log_box])
    msg.submit(chat, inputs=[msg, chatbot, image_input], outputs=[chatbot, msg, image_input, dashboard]) \
        .then(refresh_home_widgets, outputs=[home_dashboard, activity_log_box])
    clear_btn.click(clear_chat, outputs=[chatbot, msg, image_input, dashboard]) \
        .then(refresh_home_widgets, outputs=[home_dashboard, activity_log_box])

    voice_btn.click(
        voice_chat,
        inputs=[voice_input, chatbot],
        outputs=[chatbot, voice_output, dashboard],
    ).then(refresh_home_widgets, outputs=[home_dashboard, activity_log_box])

    handsfree_send_btn.click(
        hands_free_chat,
        inputs=[handsfree_input, chatbot],
        outputs=[chatbot, voice_output, dashboard],
    ).then(refresh_home_widgets, outputs=[home_dashboard, activity_log_box])

    hf_toggle_btn.click(None, js="hf_toggle")

    # ---- Home / Chief Desk wiring ----
    home_speak_btn.click(None, js="hf_toggle")  # ใช้ toggle เดียวกับ hands-free ใน Command Center

    home_ask_btn.click(chat, inputs=[home_ask_input, chatbot, image_input], outputs=[chatbot, home_ask_input, image_input, dashboard]) \
        .then(refresh_home_widgets, outputs=[home_dashboard, activity_log_box])
    home_ask_input.submit(chat, inputs=[home_ask_input, chatbot, image_input], outputs=[chatbot, home_ask_input, image_input, dashboard]) \
        .then(refresh_home_widgets, outputs=[home_dashboard, activity_log_box])

    reco_refresh_btn.click(build_chief_recommendation, outputs=[chief_reco_box])

    reco_review_btn.click(
        lambda text: log_recommendation_action("🔍 Review", text),
        inputs=[chief_reco_box],
        outputs=[activity_log_box],
    )

    reco_approve_btn.click(
        lambda text: log_recommendation_action("✅ Approve", text),
        inputs=[chief_reco_box],
        outputs=[activity_log_box],
    )

    reco_ignore_btn.click(
        lambda text: log_recommendation_action("✖️ Ignore", text),
        inputs=[chief_reco_box],
        outputs=[activity_log_box],
    )


if __name__ == "__main__":
    demo.launch(
        css=css,
        head=_head_script,
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        inbrowser=True,
    )
