"""
⚠️ STUB ชั่วคราว — ไม่ใช่ไฟล์จริง

nox_project_manager.py ตัวจริง (สำหรับ "Chief Designer Mode": สแกนโฟลเดอร์
โปรเจกต์ภายนอก เช็คไฟล์ที่เสร็จแล้ว แนะนำว่าควรทำอะไรต่อ) ยังไม่ได้ถูก
อัปโหลดเข้าระบบ ไฟล์นี้เป็นแค่ stub ให้ app.py import ได้โดยไม่ error
เพื่อให้ฟีเจอร์อื่นๆ ทั้งหมดใช้งานได้ตามปกติก่อน

คำสั่งที่ยังใช้ไม่ได้จนกว่าจะมีไฟล์จริง: /continue, /lock, /link-project
(จะตอบกลับข้อความแจ้งชัดเจนว่ายังไม่พร้อมใช้งาน ไม่ใช่แกล้งทำเป็นทำงานได้
หรือพังแบบเงียบๆ)

เมื่อมีไฟล์จริงแล้ว ให้แทนที่ไฟล์นี้ทั้งไฟล์ได้เลย ไม่ต้องแก้ app.py เพิ่ม
เพราะ app.py import มาแค่ 4 ฟังก์ชันนี้ ชื่อ/พารามิเตอร์ต้องตรงกันแบบนี้:
    next_action(project_dir) -> str
    set_status(project_dir, filename, status) -> str
    resolve_project_path(name) -> str | None
    save_project_path(name, path) -> None
"""

_STUB_NOTICE = (
    "⚠️ ฟีเจอร์นี้ยังไม่พร้อมใช้งาน — nox_project_manager.py ตัวจริงยังไม่ได้ติดตั้ง "
    "(ตอนนี้ใช้ stub ชั่วคราวอยู่) ใช้คำสั่งอื่นของ Chief ได้ตามปกติครับ"
)


def next_action(project_dir):
    """ในสถานการณ์จริงจะไม่ถูกเรียกเลย เพราะ resolve_project_path()
    คืน None เสมอ ทำให้ app.py ดักจับและตอบ error message ไปก่อนถึงตรงนี้
    เก็บไว้เผื่อกรณีเรียกตรงในอนาคต จะได้ไม่ crash"""
    return _STUB_NOTICE


def set_status(project_dir, filename, status):
    return _STUB_NOTICE


def resolve_project_path(name):
    """คืน None เสมอ — ทำให้ /continue และ /lock ใน app.py แสดงข้อความ
    'ไม่พบโฟลเดอร์' ที่มีอยู่แล้วในตัว handle_command() แทนที่จะพังหรือ
    แกล้งทำเป็นเจอโฟลเดอร์จริง"""
    return None


def save_project_path(name, path):
    """ไม่บันทึกอะไรจริง (ไม่มีที่เก็บถาวรใน stub นี้) — /link-project
    จะยังตอบว่า 'เชื่อมแล้ว' ตาม UI เดิม แต่การเชื่อมนี้จะหายไปเมื่อรีสตาร์ท
    และ /continue จะยังใช้ไม่ได้อยู่ดีจนกว่าจะมีไฟล์จริง"""
    return None
