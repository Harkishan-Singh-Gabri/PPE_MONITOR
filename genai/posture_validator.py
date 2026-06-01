import threading
import time
import cv2
import base64
from groq import Groq
from utils.logger import log
from utils.config_loader import get_env

client = Groq(api_key=get_env("GROQ_API_KEY"))
MODEL  = "meta-llama/llama-4-scout-17b-16e-instruct"

_validation_results = {}    # {worker_id: "PENDING"|"FALL_CONFIRMED"|"FALSE_ALARM"}
_pending            = set()
_last_groq_call     = 0
GROQ_MIN_INTERVAL   = 0.5


def _frame_to_base64(frame) -> str:
    _, buffer = cv2.imencode(".jpg", frame)
    return base64.b64encode(buffer).decode("utf-8")


def _build_prompt(worker_id: str, angles: dict) -> str:
    neck = angles.get("neck", "N/A")
    back = angles.get("back", "N/A")
    knee = angles.get("knee", "N/A")

    return f"""You are a workplace safety expert reviewing a potential fall incident at a construction site.

An automated system has flagged a possible FALL for Worker {worker_id}.

Evidence:
- Rapid downward body movement detected
- Neck Angle: {neck}°
- Back/Trunk Angle: {back}°
- Knee Angle: {knee}°

Your job: Determine if this is a REAL FALL (accident) or a FALSE ALARM (normal movement like crouching, sitting, or bending).

Construction context:
- Workers regularly crouch, sit, kneel, and bend — these are NOT falls
- A real fall involves sudden uncontrolled collapse, loss of balance, or person ending up on ground unexpectedly
- Look at the image carefully for signs of distress, unnatural position, or collapse

FALL_CONFIRMED if:
- Person appears to have fallen or collapsed uncontrolled
- Body is in an unnatural horizontal position unexpectedly
- Signs of accident or injury visible

FALSE_ALARM if:
- Worker is intentionally crouching or sitting to work
- Movement appears controlled and task-related
- Normal construction activity

Decision Rule: If uncertain, output UNCERTAIN.

FINAL INSTRUCTION: Reply with exactly one of these three words only:
FALL_CONFIRMED
FALSE_ALARM
UNCERTAIN"""


def validate_async(angles: dict, worker_id: str, frame=None):
    global _last_groq_call

    now = time.time()
    if now - _last_groq_call < GROQ_MIN_INTERVAL:
        return
    if worker_id in _pending:
        return

    _last_groq_call = now
    _validation_results[worker_id] = "PENDING"
    frame_copy = frame.copy() if frame is not None else None

    def _run():
        _pending.add(worker_id)
        try:
            prompt = _build_prompt(worker_id, angles)

            if frame_copy is not None:
                b64      = _frame_to_base64(frame_copy)
                messages = [{
                    "role": "user",
                    "content": [
                        {"type": "text",      "text": prompt},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{b64}"
                        }}
                    ]
                }]
            else:
                messages = [{"role": "user", "content": prompt}]

            response = client.chat.completions.create(
                model      = MODEL,
                messages   = messages,
                max_tokens = 5,
            )

            result = response.choices[0].message.content.strip().upper()

            if result not in ("FALL_CONFIRMED", "FALSE_ALARM", "UNCERTAIN"):
                log.warning(f"Unexpected Groq response: '{result}' — defaulting UNCERTAIN")
                result = "UNCERTAIN"

            _validation_results[worker_id] = result
            log.debug(f"Groq fall validation [{worker_id}]: {result}")

        except Exception as e:
            log.warning(f"Groq validation failed: {e} — defaulting FALSE_ALARM")
            _validation_results[worker_id] = "UNCERTAIN"
        finally:
            _pending.discard(worker_id)

    threading.Thread(target=_run, daemon=True).start()


def get_validation_result(worker_id: str) -> str:
    """
    Returns:
      None             — not yet triggered
      "PENDING"        — Groq thinking
      "FALL_CONFIRMED" — real fall, alert
      "FALSE_ALARM"    — suppress
    """
    return _validation_results.get(worker_id, None)