"""
detector.py - Smart Gender Detector [FIXED v3]
===============================================
FIXES:
- Face ID is now position-based (stable grid cells) - no histogram instability
- UI aur TTS DONO update hote hain jab face detect ho
- Greet cooldown: same position par 20 sec baad dobara greet
- Female bias correction
- Thread-safe callbacks
"""

import cv2
import numpy as np
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict

try:
    from deepface import DeepFace
    DEEPFACE_OK = True
except ImportError:
    DEEPFACE_OK = False
    print("[Detector] WARNING: DeepFace not installed.")


# ─────────────────────────────────────────────
#  DetectionResult
# ─────────────────────────────────────────────
@dataclass
class DetectionResult:
    scenario: str
    male_count: int
    female_count: int
    total_faces: int
    confidence: float
    faces: List[dict]
    is_new_visitor: bool = False

    @property
    def greeting_text(self) -> str:
        return {
            "none":         "Welcome to AI Exhibition!",
            "male":         "Welcome Sir!",
            "female":       "Welcome Ma'am!",
            "group_male":   f"Welcome Gentlemen! ({self.male_count} guests)",
            "group_female": f"Welcome Ladies! ({self.female_count} guests)",
            "group_mixed":  f"Welcome Everyone! ({self.total_faces} guests)",
        }.get(self.scenario, "Welcome!")

    @property
    def speech_text(self) -> str:
        return {
            "none":         "",
            "male":         "Welcome Sir! Enjoy the AI Exhibition.",
            "female":       "Welcome Madam! Enjoy the AI Exhibition.",
            "group_male":   f"Welcome Gentlemen! Enjoy the AI Exhibition.",
            "group_female": f"Welcome Ladies! Enjoy the AI Exhibition.",
            "group_mixed":  f"Welcome everyone! Enjoy the AI Exhibition.",
        }.get(self.scenario, "")

    @property
    def emoji(self) -> str:
        return {
            "none": "👀", "male": "👨", "female": "👩",
            "group_male": "👨‍👨‍👦", "group_female": "👩‍👩‍👧",
            "group_mixed": "👨‍👩‍👧‍👦"
        }.get(self.scenario, "🤖")

    @property
    def color_theme(self) -> str:
        return {
            "none": "#00BFFF", "male": "#4FC3F7", "female": "#F48FB1",
            "group_male": "#29B6F6", "group_female": "#EC407A",
            "group_mixed": "#AB47BC"
        }.get(self.scenario, "#00BFFF")


# ─────────────────────────────────────────────
#  Simple Face Zone Tracker
#  (position-based: screen ko grid cells mein divide karo)
# ─────────────────────────────────────────────
class FaceZone:
    """
    Ek face zone track karta hai.
    Face ki position ko 80x80 pixel grid cell mein snap karta hai.
    Yeh approach histogram se zyada stable hai.
    """
    GREET_COOLDOWN = 20.0   # seconds

    def __init__(self, cell_x: int, cell_y: int, gender: str, conf: float):
        self.cell_x = cell_x
        self.cell_y = cell_y
        self.gender = gender
        self.confidence = conf
        self.gender_votes: Dict[str, int] = {gender: 1}
        self.last_seen = time.time()
        self.miss_frames = 0
        self.greeted = False
        self.greeted_at = 0.0

    @property
    def zone_id(self) -> str:
        return f"z_{self.cell_x}_{self.cell_y}"

    def update(self, gender: str, conf: float):
        self.last_seen = time.time()
        self.miss_frames = 0
        self.confidence = conf
        self.gender_votes[gender] = self.gender_votes.get(gender, 0) + 1
        # Dominant gender (voting)
        self.gender = max(self.gender_votes, key=self.gender_votes.get)

    def needs_greeting(self) -> bool:
        if not self.greeted:
            return True
        if time.time() - self.greeted_at > self.GREET_COOLDOWN:
            self.greeted = False
            return True
        return False

    def mark_greeted(self):
        self.greeted = True
        self.greeted_at = time.time()

    @property
    def is_stale(self) -> bool:
        return self.miss_frames > 6


def face_to_cell(x, y, w, h, cell_size=80):
    """Face bbox center ko grid cell mein convert karo."""
    cx = (x + w // 2) // cell_size
    cy = (y + h // 2) // cell_size
    return cx, cy


# ─────────────────────────────────────────────
#  GenderDetector
# ─────────────────────────────────────────────
class GenderDetector:

    def __init__(self):
        self._lock        = threading.Lock()
        self._res_lock    = threading.Lock()
        self._running     = False
        self._cap         = None
        self._callback    = None
        self._latest_frame = None
        self._zones: Dict[str, FaceZone] = {}

        self._last_analysis = 0.0
        self._analysis_interval = 1.0   # seconds

        # Previous scenario - UI ko tab update karo jab kuch badla ho
        self._prev_scenario = "none"
        self._prev_total    = 0

        cascade = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade2 = cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml"
        self._casc1 = cv2.CascadeClassifier(cascade)
        self._casc2 = cv2.CascadeClassifier(cascade2)

        self._latest_result = DetectionResult(
            "none", 0, 0, 0, 0.0, [], False)

    # ── Public ────────────────────────────────
    def start(self, callback=None):
        self._callback = callback
        self._running  = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def stop(self):
        self._running = False
        if self._cap:
            self._cap.release()

    @property
    def latest_result(self):
        with self._res_lock:
            return self._latest_result

    # ── Camera loop ───────────────────────────
    def _loop(self):
        self._cap = cv2.VideoCapture(0)
        if not self._cap.isOpened():
            print("[Detector] No camera found — Demo mode")
            self._demo()
            return

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        print("[Detector] Camera OK")

        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                time.sleep(0.03)
                continue

            self._latest_frame = frame.copy()

            now = time.time()
            if now - self._last_analysis >= self._analysis_interval:
                self._last_analysis = now
                self._process(frame)

            annotated = self._annotate(frame.copy())
            cv2.imshow("AI Exhibition - Camera Preview (Press Q to hide)", annotated)
            if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q')):
                cv2.destroyAllWindows()

        self._cap.release()
        cv2.destroyAllWindows()

    # ── Core processing ───────────────────────
    def _process(self, frame: np.ndarray):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cv2.equalizeHist(gray, gray)

        # Detect with both cascades
        f1 = self._casc1.detectMultiScale(gray, 1.1, 5, minSize=(55, 55))
        f2 = self._casc2.detectMultiScale(gray, 1.1, 5, minSize=(55, 55))

        bboxes = []
        if len(f1) > 0: bboxes += list(f1)
        if len(f2) > 0: bboxes += list(f2)
        bboxes = self._nms(bboxes)

        # ── No faces ──────────────────────────
        if not bboxes:
            with self._lock:
                for z in self._zones.values():
                    z.miss_frames += 1
                self._prune()

            result = DetectionResult("none", 0, 0, 0, 0.0, [], False)
            self._publish(result)
            return

        # ── DeepFace analysis ─────────────────
        if not DEEPFACE_OK:
            return

        try:
            df = DeepFace.analyze(
                img_path=frame,
                actions=["gender"],
                enforce_detection=False,
                silent=True,
                detector_backend="opencv"
            )
            if isinstance(df, dict):
                df = [df]
        except Exception as e:
            print(f"[Detector] DeepFace error: {e}")
            # Even if DeepFace fails, still show detected faces
            result = DetectionResult("none", 0, 0, 0, 0.0, [], False)
            self._publish(result)
            return

        # ── Parse DeepFace results ────────────
        detected = []
        for r in df:
            reg = r.get("region", {})
            rx, ry, rw, rh = reg.get("x",0), reg.get("y",0), reg.get("w",0), reg.get("h",0)
            if rw < 40 or rh < 40:
                continue

            gscores = r.get("gender", {"Man": 50, "Woman": 50})
            man_s   = gscores.get("Man",   gscores.get("man",   50))
            woman_s = gscores.get("Woman", gscores.get("woman", 50))

            # Female bias fix: accept Woman if score >= 30%
            if woman_s >= 30:
                gender = "Woman"
                conf   = woman_s / 100.0
            else:
                gender = "Man"
                conf   = man_s   / 100.0

            cell_x, cell_y = face_to_cell(rx, ry, rw, rh)
            detected.append({
                "gender": gender, "conf": conf,
                "cell_x": cell_x, "cell_y": cell_y,
                "x": rx, "y": ry, "w": rw, "h": rh,
            })

        if not detected:
            result = DetectionResult("none", 0, 0, 0, 0.0, [], False)
            self._publish(result)
            return

        # ── Update zones & check new visitors ─
        with self._lock:
            seen_zones = set()
            any_new    = False

            for d in detected:
                zid = f"z_{d['cell_x']}_{d['cell_y']}"
                seen_zones.add(zid)

                if zid in self._zones:
                    self._zones[zid].update(d["gender"], d["conf"])
                else:
                    self._zones[zid] = FaceZone(
                        d["cell_x"], d["cell_y"], d["gender"], d["conf"])

                if self._zones[zid].needs_greeting():
                    self._zones[zid].mark_greeted()
                    any_new = True

            # Increment miss for zones not seen this frame
            for zid, z in self._zones.items():
                if zid not in seen_zones:
                    z.miss_frames += 1

            self._prune()

            # Count active zones
            active  = [z for z in self._zones.values() if z.miss_frames == 0]
            males   = [z for z in active if z.gender == "Man"]
            females = [z for z in active if z.gender == "Woman"]
            total   = len(active)
            avg_c   = sum(z.confidence for z in active) / total if total else 0.0
            scenario = self._get_scenario(len(males), len(females))

            face_list = [{"gender": z.gender, "confidence": z.confidence,
                          "x": d.get("x",0), "y": d.get("y",0),
                          "w": d.get("w",0), "h": d.get("h",0)}
                         for z, d in zip(active, detected[:len(active)])]

        result = DetectionResult(
            scenario=scenario,
            male_count=len(males),
            female_count=len(females),
            total_faces=total,
            confidence=avg_c,
            faces=face_list,
            is_new_visitor=any_new,
        )
        self._publish(result)

    def _publish(self, result: DetectionResult):
        with self._res_lock:
            self._latest_result = result

        # ALWAYS call callback so UI stays live
        if self._callback:
            self._callback(result)

    def _prune(self):
        stale = [k for k, z in self._zones.items() if z.is_stale]
        for k in stale:
            del self._zones[k]

    def _get_scenario(self, m: int, f: int) -> str:
        t = m + f
        if t == 0:   return "none"
        if t == 1:   return "male" if m else "female"
        if f == 0:   return "group_male"
        if m == 0:   return "group_female"
        return "group_mixed"

    def _nms(self, boxes: list, overlap=0.4) -> list:
        if not boxes:
            return []
        result, used = [], set()
        for i, a in enumerate(boxes):
            if i in used: continue
            for j, b in enumerate(boxes):
                if i == j or j in used: continue
                if self._iou(a, b) > overlap:
                    used.add(j)
            result.append(a)
        return result

    def _iou(self, a, b) -> float:
        ax,ay,aw,ah = a;  bx,by,bw,bh = b
        ix = max(ax,bx);  iy = max(ay,by)
        iw = min(ax+aw, bx+bw)-ix
        ih = min(ay+ah, by+bh)-iy
        if iw<=0 or ih<=0: return 0.0
        inter = iw*ih
        return inter / (aw*ah + bw*bh - inter)

    def _annotate(self, frame: np.ndarray) -> np.ndarray:
        r = self.latest_result
        for face in r.faces:
            x,y,w,h = face["x"], face["y"], face["w"], face["h"]
            col = (255,160,50) if face["gender"]=="Man" else (200,80,255)
            lbl = f"{'Male' if face['gender']=='Man' else 'Female'} {face['confidence']*100:.0f}%"
            cv2.rectangle(frame,(x,y),(x+w,y+h),col,2)
            cv2.putText(frame,lbl,(x,y-8),cv2.FONT_HERSHEY_SIMPLEX,0.6,col,2)
        info = f"Faces:{r.total_faces} M:{r.male_count} F:{r.female_count} | {r.scenario} | new={r.is_new_visitor}"
        cv2.putText(frame,info,(8,frame.shape[0]-8),cv2.FONT_HERSHEY_SIMPLEX,0.48,(0,255,180),1)
        return frame

    # ── Demo mode (no camera) ─────────────────
    def _demo(self):
        scenarios = [
            DetectionResult("none",  0,0,0,0.0,[],False),
            DetectionResult("male",  1,0,1,0.93,[],True),
            DetectionResult("male",  1,0,1,0.93,[],False),
            DetectionResult("male",  1,0,1,0.93,[],False),
            DetectionResult("none",  0,0,0,0.0,[],False),
            DetectionResult("female",0,1,1,0.88,[],True),
            DetectionResult("female",0,1,1,0.88,[],False),
            DetectionResult("none",  0,0,0,0.0,[],False),
            DetectionResult("group_mixed",2,2,4,0.85,[],True),
            DetectionResult("group_mixed",2,2,4,0.85,[],False),
            DetectionResult("none",  0,0,0,0.0,[],False),
        ]
        print("[Detector] Demo mode active")
        for i, s in enumerate(scenarios * 99):
            if not self._running: break
            with self._res_lock:
                self._latest_result = s
            if self._callback:
                self._callback(s)
            time.sleep(2.5)
