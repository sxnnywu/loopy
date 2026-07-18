"""Facial-expression signals via MediaPipe Face Landmarker (open-source) — Person B.

Jay's idea: for talking-head clips, expression and head movement are engagement
cues. We report, per clip:
  - smile_frac      : fraction of frames with a smile
  - teeth_frac      : fraction of frames with mouth open (teeth showing)
  - head_motion     : how much the head turns/moves over the clip
  - face_frac       : fraction of frames a face is detected

Diagnostic stats (ranked by amount), not engagement inputs yet — validate
"more expression = more engaging" against labelled pairs first.

Needs the face_landmarker.task model (cached to /cache).
"""

import numpy as np

from backend.scoring.objective import _sample_frames

_LANDMARKER = None
_TASK_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"


def _load(cache_dir: str = "/cache"):
    global _LANDMARKER
    if _LANDMARKER is None:
        import os
        import urllib.request

        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        path = f"{cache_dir}/mediapipe/face_landmarker.task"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            urllib.request.urlretrieve(_TASK_URL, path)
        opts = vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=path),
            output_face_blendshapes=True,
            num_faces=1,
        )
        _LANDMARKER = vision.FaceLandmarker.create_from_options(opts)
    return _LANDMARKER


def analyze_face(video_path: str, cache_dir: str = "/cache", fps: int = 3) -> dict:
    import mediapipe as mp

    frames = _sample_frames(video_path, 256, 256, fps, gray=False)
    if frames is None:
        return {"smile_frac": 0.0, "teeth_frac": 0.0, "head_motion": 0.0, "face_frac": 0.0}
    lm = _load(cache_dir)

    smiles, teeth, faces, nose_x = 0, 0, 0, []
    for f in frames:
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=f.astype("uint8"))
        res = lm.detect(img)
        if not res.face_landmarks:
            continue
        faces += 1
        bs = {b.category_name: b.score for b in res.face_blendshapes[0]} if res.face_blendshapes else {}
        smile = max(bs.get("mouthSmileLeft", 0), bs.get("mouthSmileRight", 0))
        if smile > 0.3:
            smiles += 1
        if bs.get("jawOpen", 0) > 0.2:
            teeth += 1
        nose_x.append(res.face_landmarks[0][1].x)  # landmark 1 ~ nose bridge

    n = len(frames)
    head_motion = float(np.std(nose_x)) if len(nose_x) > 1 else 0.0
    return {
        "smile_frac": round(smiles / n, 3),
        "teeth_frac": round(teeth / n, 3),
        "head_motion": round(head_motion, 4),
        "face_frac": round(faces / n, 3),
    }
