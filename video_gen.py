"""
video_gen.py — สร้างวิดีโอด้วย AI ผ่าน fal.ai (โมเดล Kling)

ออกแบบมาสำหรับ NOX Studio โดยเฉพาะ: ใช้ "image-to-video" ไม่ใช่ text-to-video
ล้วนๆ เพราะต้องส่งภาพ Character Sheet ของ NOX เป็นภาพต้นแบบ (reference)
เพื่อให้หน้าตาตัวละครในวิดีโอตรงกับต้นฉบับมากที่สุด — ตรงตาม Golden Rule
ของ NOX Studio ("ถ้าภาพไม่เหมือน Character Sheet = ไม่ผ่าน")

ต้องมี FAL_KEY อยู่ใน environment variable (ตั้งเป็น Secret บน Hugging Face
Space ห้าม hardcode ในโค้ดเด็ดขาด)
"""
import os

try:
    import fal_client
    _FAL_AVAILABLE = True
except ImportError:
    _FAL_AVAILABLE = False

# endpoint คุณภาพสูงสุดที่รองรับภาพต้นแบบ (reference image) ผ่าน start_image_url
# และมี native audio ในตัว — เหมาะกับงาน teaser ที่ต้องการคุณภาพสูง
_ENDPOINT = "fal-ai/kling-video/v2.1/standard/image-to-video"

# โฟลเดอร์เก็บวิดีโอที่สร้างเสร็จแล้ว (ดาวน์โหลดมาเก็บไว้ในเครื่อง Chief เอง
# กันกรณี URL จาก fal.ai หมดอายุ)
VIDEO_OUTPUT_DIR = os.path.join("data", "generated_videos")


def _check_fal_ready():
    if not _FAL_AVAILABLE:
        return "❌ ยังไม่ได้ติดตั้งไลบรารี fal-client — เพิ่ม 'fal-client' ใน requirements.txt แล้ว deploy ใหม่"
    if not os.environ.get("FAL_KEY"):
        return "❌ ยังไม่ได้ตั้งค่า FAL_KEY — ไปที่ Space Settings → Repository secrets แล้วเพิ่ม FAL_KEY ก่อนใช้งานฟีเจอร์นี้"
    return None


def generate_video_from_image(image_path, prompt, duration="5", generate_audio=True):
    """
    สร้างวิดีโอจากภาพต้นแบบ (เช่น Character Sheet ของ NOX) + คำบรรยาย

    image_path: path ไฟล์ภาพในเครื่อง (จะอัปโหลดขึ้น fal.ai storage ให้อัตโนมัติ)
                หรือจะเป็น URL ที่เข้าถึงได้จากสาธารณะอยู่แล้วก็ได้
    prompt: คำบรรยายฉาก/การเคลื่อนไหวที่ต้องการ (ภาษาอังกฤษจะได้ผลดีกว่า)
    duration: ความยาววิดีโอเป็นวินาที ("5" หรือ "10")
    generate_audio: สร้างเสียงประกอบไปด้วยไหม (ปิดได้ถ้าจะเอาไปเสียง TTS/เพลงเอง)

    คืนค่า: dict {"success": bool, "video_url": str, "local_path": str, "message": str}
    """
    error = _check_fal_ready()
    if error:
        return {"success": False, "video_url": None, "local_path": None, "message": error}

    if not image_path:
        return {"success": False, "video_url": None, "local_path": None,
                "message": "❌ ต้องมีภาพต้นแบบ (Character Sheet) เสมอ — ห้ามสร้างแบบ text-to-video ล้วนๆ เพราะจะคุมหน้าตาตัวละครไม่ได้"}

    try:
        # ถ้าเป็น path ไฟล์ในเครื่อง ต้องอัปโหลดขึ้น fal.ai storage ก่อน เพราะ
        # API ต้องการ URL ที่เข้าถึงได้จากอินเทอร์เน็ต ไม่รับไฟล์ในเครื่องตรงๆ
        if image_path.startswith("http://") or image_path.startswith("https://"):
            image_url = image_path
        else:
            image_url = fal_client.upload_file(image_path)

        def _on_update(update):
            # log ความคืบหน้าไว้ใน server log เผื่อ debug (ไม่กระทบผู้ใช้)
            if isinstance(update, fal_client.InProgress):
                for log in update.logs:
                    print(f"[video_gen] {log.get('message', '')}")

        result = fal_client.subscribe(
            _ENDPOINT,
            arguments={
                "prompt": prompt,
                "image_url": image_url,
                "duration": str(duration),
                "generate_audio": bool(generate_audio),
            },
            with_logs=True,
            on_queue_update=_on_update,
        )

        video_url = result.get("video", {}).get("url")
        if not video_url:
            return {"success": False, "video_url": None, "local_path": None,
                    "message": f"❌ fal.ai ไม่ได้ส่ง video URL กลับมา — ผลลัพธ์ดิบ: {result}"}

        # ดาวน์โหลดมาเก็บไว้ในเครื่อง Chief เอง กัน URL หมดอายุภายหลัง
        local_path = _download_video(video_url)

        return {
            "success": True,
            "video_url": video_url,
            "local_path": local_path,
            "message": f"✅ สร้างวิดีโอสำเร็จ ({duration} วินาที)",
        }

    except Exception as e:
        return {"success": False, "video_url": None, "local_path": None,
                "message": f"❌ สร้างวิดีโอไม่สำเร็จ: {e}"}


def _download_video(video_url):
    import urllib.request
    import time

    os.makedirs(VIDEO_OUTPUT_DIR, exist_ok=True)
    filename = f"nox_video_{int(time.time())}.mp4"
    local_path = os.path.join(VIDEO_OUTPUT_DIR, filename)
    urllib.request.urlretrieve(video_url, local_path)
    return local_path
