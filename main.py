import ctypes
import difflib
import json
import os
import re
import sys
import time
import threading
import urllib.request
import zipfile
from ctypes import wintypes
from pathlib import Path

# Πριν από το Qt, ώστε οι συντεταγμένες οθόνης να είναι σε πραγματικά pixel.
try:
    _user32 = ctypes.windll.user32
    _user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    _user32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL
    _user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

from PySide6 import QtCore, QtGui, QtWidgets
from PIL import Image, ImageFilter, ImageGrab, ImageOps
import numpy as np
import pytesseract

def resource_dir():
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent


ROOT = resource_dir()
APP_NAME = "Metafrasi"
ICON_FILE = ROOT / "metafrasi.ico"
MODEL_DIR = ROOT / "models" / "translate-en_el-1_9"
MODEL_URL = "https://argos-net.com/v1/translate-en_el-1_9.argosmodel"
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", ".")) / APP_NAME
OLD_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", ".")) / "Metafrash"


def log(message):
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(DATA_DIR / "metafrasi.log", "a", encoding="utf-8") as handle:
            handle.write(message + "\n")
    except Exception:
        pass


TESSDATA_DIR = ""


def find_tesseract():
    global TESSDATA_DIR
    candidates = [
        ROOT / "tesseract" / "tesseract.exe",
        Path(sys.executable).resolve().parent / "tesseract" / "tesseract.exe",
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    ]
    for path in candidates:
        if path.is_file():
            tessdata = path.parent / "tessdata"
            if (tessdata / "eng.traineddata").is_file():
                TESSDATA_DIR = str(tessdata)
                os.environ["TESSDATA_PREFIX"] = TESSDATA_DIR
            os.environ["PATH"] = str(path.parent) + os.pathsep + os.environ.get("PATH", "")
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(str(path.parent))
            return str(path)
    return str(candidates[-1])


pytesseract.pytesseract.tesseract_cmd = find_tesseract()

user32 = ctypes.windll.user32

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_FRAMECHANGED = 0x0020
WDA_EXCLUDEFROMCAPTURE = 0x00000011
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
WM_NCHITTEST = 0x0084
HTCLIENT = 1
HTTRANSPARENT = -1
MOD_SHIFT = 0x0004
MOD_CONTROL = 0x0002
MOD_ALT = 0x0001
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
VK_Q = 0x51
HOTKEY_QUIT_ID = 1
HOTKEY_PAUSE_ID = 2
HOTKEY_RESELECT_ID = 3
HOTKEY_SETTINGS_ID = 4

SETTINGS_FILE = DATA_DIR / "settings.json"
DEFAULT_SHORTCUTS = {
    "pause": "F6",
    "reselect": "F7",
    "settings": "F8",
    "quit": "Ctrl+Shift+Q",
}

if ctypes.sizeof(ctypes.c_void_p) == 8:
    _get_window_long = user32.GetWindowLongPtrW
    _set_window_long = user32.SetWindowLongPtrW
else:
    _get_window_long = user32.GetWindowLongW
    _set_window_long = user32.SetWindowLongW

_get_window_long.argtypes = [ctypes.c_void_p, ctypes.c_int]
_get_window_long.restype = ctypes.c_ssize_t
_set_window_long.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
_set_window_long.restype = ctypes.c_ssize_t
user32.SetWindowPos.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_uint,
]
user32.SetWindowPos.restype = wintypes.BOOL
user32.SetWindowDisplayAffinity.argtypes = [ctypes.c_void_p, ctypes.c_uint]
user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
user32.RegisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.WindowFromPoint.restype = ctypes.c_void_p
user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
user32.GetAncestor.restype = ctypes.c_void_p
user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = wintypes.BOOL


def _enum_monitors():
    monitors = []

    def callback(hmonitor, hdc, lprc, data):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
            rect = info.rcMonitor
            monitors.append((rect.left, rect.top, rect.right, rect.bottom))
        return 1

    enum_proc = ctypes.WINFUNCTYPE(
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.POINTER(RECT),
        ctypes.c_ssize_t,
    )
    user32.EnumDisplayMonitors(None, None, enum_proc(callback), 0)
    return monitors


def _monitor_for_screen(screen):
    monitors = _enum_monitors()
    if not monitors:
        geo = screen.geometry()
        return (geo.x(), geo.y(), geo.x() + geo.width(), geo.y() + geo.height())
    if len(monitors) == 1:
        return monitors[0]

    dpr = screen.devicePixelRatio()
    geo = screen.geometry()
    target_w = geo.width() * dpr
    target_h = geo.height() * dpr
    best = monitors[0]
    best_score = None
    for left, top, right, bottom in monitors:
        score = abs((right - left) - target_w) + abs((bottom - top) - target_h)
        if best_score is None or score < best_score:
            best = (left, top, right, bottom)
            best_score = score
    return best


def logical_bbox_to_physical(x1, y1, x2, y2):
    """Qt δίνει λογικά pixel. Το DXGI και το ImageGrab θέλουν φυσικά pixel."""
    center = QtCore.QPoint(int((x1 + x2) / 2), int((y1 + y2) / 2))
    screen = QtGui.QGuiApplication.screenAt(center) or QtGui.QGuiApplication.primaryScreen()
    geo = screen.geometry()
    left, top, right, bottom = _monitor_for_screen(screen)
    scale_x = (right - left) / max(1, geo.width())
    scale_y = (bottom - top) / max(1, geo.height())
    px1 = int(round(left + (x1 - geo.x()) * scale_x))
    py1 = int(round(top + (y1 - geo.y()) * scale_y))
    px2 = int(round(left + (x2 - geo.x()) * scale_x))
    py2 = int(round(top + (y2 - geo.y()) * scale_y))
    physical = (min(px1, px2), min(py1, py2), max(px1, px2), max(py1, py2))
    return physical, (left, top, right, bottom)


def clip_bbox_to_window(bbox):
    """Κόβει μόνο ό,τι ξεχειλίζει έξω από το παράθυρο του παιχνιδιού."""
    x1, y1, x2, y2 = bbox
    point = wintypes.POINT(int((x1 + x2) / 2), int((y1 + y2) / 2))
    hwnd = user32.WindowFromPoint(point)
    if not hwnd:
        return bbox
    root = user32.GetAncestor(hwnd, 2) or hwnd  # GA_ROOT
    rect = RECT()
    if not user32.GetWindowRect(root, ctypes.byref(rect)):
        return bbox
    clipped = (
        max(x1, rect.left + 2),
        max(y1, rect.top + 2),
        min(x2, rect.right - 2),
        min(y2, rect.bottom - 2),
    )
    if clipped[2] - clipped[0] < 20 or clipped[3] - clipped[1] < 20:
        return bbox
    return clipped


def physical_to_logical(bbox, monitor_rect):
    px1, py1, px2, py2 = bbox
    left, top, right, bottom = monitor_rect
    center = QtCore.QPoint(int((px1 + px2) / 2), int((py1 + py2) / 2))
    screen = QtGui.QGuiApplication.screenAt(center) or QtGui.QGuiApplication.primaryScreen()
    geo = screen.geometry()
    scale_x = geo.width() / max(1, right - left)
    scale_y = geo.height() / max(1, bottom - top)
    return (
        int(round(geo.x() + (px1 - left) * scale_x)),
        int(round(geo.y() + (py1 - top) * scale_y)),
        int(round(geo.x() + (px2 - left) * scale_x)),
        int(round(geo.y() + (py2 - top) * scale_y)),
    )


def _clamp_region(region, width, height):
    left, top, right, bottom = region
    left = max(0, min(int(left), width - 1))
    top = max(0, min(int(top), height - 1))
    right = max(left + 1, min(int(right), width))
    bottom = max(top + 1, min(int(bottom), height))
    return left, top, right, bottom


def _is_black_bgra(frame):
    # Το alpha είναι 255 ακόμα και σε μαύρο καρέ, οπότε μετράμε μόνο το χρώμα.
    return float(frame[:, :, :3].mean()) < 2.0


def _is_black_image(img):
    sample = img.convert("L").resize((32, 32))
    return float(np.asarray(sample).mean()) < 2.0


def _bgra_to_image(frame):
    rgb = np.ascontiguousarray(frame[:, :, 2::-1])
    return Image.fromarray(rgb, "RGB")


def open_game_camera(monitor_rect):
    """DXGI Desktop Duplication: πιάνει DirectX παιχνίδια, όχι μόνο παράθυρα GDI."""
    sys.coinit_flags = 0
    import bettercam

    mon_left, mon_top, mon_right, mon_bottom = monitor_rect
    device_idx = 0
    output_idx = 0
    factory = bettercam.__factory
    for didx, outputs in enumerate(factory.outputs):
        for oidx, output in enumerate(outputs):
            rect = output.desc.DesktopCoordinates
            if rect.left == mon_left and rect.top == mon_top and rect.right == mon_right and rect.bottom == mon_bottom:
                device_idx = didx
                output_idx = oidx
                break
        else:
            continue
        break

    camera = bettercam.create(
        device_idx=device_idx,
        output_idx=output_idx,
        output_color="BGRA",
    )
    width, height = camera.width, camera.height
    return camera, width, height


def _otsu_level(gray):
    histogram = gray.histogram()
    total = sum(histogram)
    if total == 0:
        return 128
    sum_total = sum(index * count for index, count in enumerate(histogram))
    background_sum = 0
    background_weight = 0
    best_variance = 0
    level = 128
    for index, count in enumerate(histogram):
        background_weight += count
        if background_weight == 0:
            continue
        foreground_weight = total - background_weight
        if foreground_weight == 0:
            break
        background_sum += index * count
        background_mean = background_sum / background_weight
        foreground_mean = (sum_total - background_sum) / foreground_weight
        variance = background_weight * foreground_weight * (background_mean - foreground_mean) ** 2
        if variance > best_variance:
            best_variance = variance
            level = index
    return level


COMMON_WORDS = {
    "a", "about", "again", "all", "also", "an", "and", "another", "any", "are",
    "as", "at", "available", "be", "been", "before", "but", "by", "can", "can't",
    "cannot", "changed", "continue", "cursor", "do", "does", "don't", "down",
    "end", "file", "for", "from", "get", "go", "have", "he", "her", "here",
    "him", "his", "how", "i", "if", "in", "into", "is", "it", "its", "just",
    "keep", "know", "let", "like", "look", "me", "more", "my", "need", "no",
    "not", "now", "of", "on", "one", "or", "our", "out", "over", "rise",
    "said", "see", "she", "so", "some", "stops", "than", "that", "the",
    "their", "them", "then", "there", "these", "they", "think", "this",
    "those", "time", "times", "to", "too", "try", "update", "up", "us",
    "use", "using", "version", "was", "we", "were", "what", "when", "where",
    "which", "who", "will", "with", "working", "would", "you", "your",
}

OCR_FIXES = {
    "avadadable": "Available",
    "avaliable": "Available",
    "matem.py": "main.py",
    "matemp.y": "main.py",
    "filechanged": "File changed",
    "updateavailable": "Update Available",
    "tryagain": "Try again",
}


def _binarize(gray, keep_bright):
    level = _otsu_level(gray)
    if keep_bright:
        mask = gray.point(lambda pixel: 255 if pixel > max(level, 140) else 0)
    else:
        mask = gray.point(lambda pixel: 0 if pixel > min(level, 140) else 255)
    scaled = mask.resize((mask.width * 2, mask.height * 2), Image.Resampling.BILINEAR)
    pad = 10
    canvas = Image.new("L", (scaled.width + pad * 2, scaled.height + pad * 2), 0 if keep_bright else 255)
    canvas.paste(scaled, (pad, pad))
    return canvas


def _useful_line(line):
    letters = sum(ch.isalpha() for ch in line)
    if letters < 2:
        return False
    if letters / max(len(line), 1) < 0.28:
        return False
    lowered = line.lower()
    if lowered.startswith("http") or "www." in lowered:
        return False
    return True


def _split_glued_words(text):
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([A-Za-z])(\d)", r"\1 \2", text)
    text = re.sub(r"(\d)([A-Za-z])", r"\1 \2", text)
    parts = []
    for raw in text.split():
        key = raw.lower()
        if key in OCR_FIXES:
            parts.append(OCR_FIXES[key])
            continue
        if len(raw) < 12 or " " in raw or not raw.isalpha():
            parts.append(raw)
            continue
        broken = _break_long_word(raw)
        parts.append(broken)
    return " ".join(parts)


def _break_long_word(word):
    lower = word.lower()
    if lower in COMMON_WORDS:
        return word
    start = 0
    pieces = []
    while start < len(lower):
        match = None
        for end in range(len(lower), start + 1, -1):
            if lower[start:end] in COMMON_WORDS and end - start >= 2:
                match = word[start:end]
                start = end
                break
        if match is None:
            return word
        pieces.append(match)
    return " ".join(pieces) if len(pieces) >= 2 else word


def _clean_ocr_text(text):
    text = text.replace("|", "I").replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = _split_glued_words(text)
    text = " ".join(text.split())
    for wrong, right in OCR_FIXES.items():
        text = re.sub(re.escape(wrong), right, text, flags=re.IGNORECASE)
    return text


def _ocr_score(text):
    words = [word for word in re.findall(r"[A-Za-z']+", text)]
    if not words:
        return -100
    known = sum(1 for word in words if word.lower() in COMMON_WORDS)
    glued = sum(1 for word in words if len(word) > 16)
    return known * 4 + len(words) - glued * 6


def _region_is_small(img):
    return img.height <= 90 or (img.width * img.height) < 35000


def _is_valid_subtitle(text, small=False):
    if _mostly_greek(text):
        return False
    words = [word for word in re.findall(r"[A-Za-zΑ-Ωα-ωΆ-Ώά-ώ']+", text) if len(word) >= 2]
    letters = sum(ch.isalpha() for ch in text)
    if letters < 4 or not words:
        return False
    if small or len(words) >= 2 or letters >= 7:
        return True
    return False


def _ocr_from_image(img, psm):
    raw = pytesseract.image_to_string(
        img,
        lang="eng",
        config=f"--oem 3 --psm {psm} -c preserve_interword_spaces=1",
    )
    lines = []
    for line in raw.splitlines():
        line = " ".join(line.split())
        if _useful_line(line):
            lines.append(line)
    return _clean_ocr_text(" ".join(lines))


def _prepare_gray(img):
    gray = ImageOps.autocontrast(img.convert("L"))
    scaled = gray.resize((gray.width * 2, gray.height * 2), Image.Resampling.BILINEAR)
    canvas = Image.new("L", (scaled.width + 20, scaled.height + 20), 255)
    canvas.paste(scaled, (10, 10))
    return canvas


def read_text(img):
    small = _region_is_small(img)
    gray = ImageOps.autocontrast(img.convert("L"))
    psm = 7 if small else 6
    candidates = []
    for source in (_prepare_gray(img), _binarize(gray, True), _binarize(gray, False)):
        text = _ocr_from_image(source, psm)
        if not text:
            continue
        candidates.append(text)
        if _is_valid_subtitle(text, small=small):
            return text
    if not candidates:
        return ""
    best = max(candidates, key=_ocr_score)
    return best if _is_valid_subtitle(best, small=small) else ""


def _mostly_greek(text):
    greek = sum(1 for ch in text if "\u0370" <= ch <= "\u03ff" or "\u1f00" <= ch <= "\u1fff")
    latin = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    return greek > latin and greek >= 3


def _text_chunks(text):
    chunks = []
    for line in text.splitlines():
        line = " ".join(line.split())
        if not line:
            continue
        parts = re.split(r"(?<=[.!?;:])\s+", line)
        pending = ""
        for part in parts:
            if pending and len(pending) + len(part) > 180:
                chunks.append(pending)
                pending = part
            else:
                pending = (pending + " " + part).strip()
        if pending:
            chunks.append(pending)
    return chunks


def same_subtitle(previous, current):
    if not previous or not current:
        return False
    if previous == current:
        return True
    return difflib.SequenceMatcher(None, previous, current).ratio() >= 0.98


def model_is_ready():
    return (MODEL_DIR / "model" / "model.bin").is_file() and (MODEL_DIR / "sentencepiece.model").is_file()


def ensure_translation_model():
    if model_is_ready():
        return
    MODEL_DIR.parent.mkdir(parents=True, exist_ok=True)
    archive = MODEL_DIR.parent / "translate-en_el-1_9.argosmodel"
    request = urllib.request.Request(MODEL_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=180) as response, open(archive, "wb") as output:
        while True:
            chunk = response.read(1024 * 256)
            if not chunk:
                break
            output.write(chunk)
    with zipfile.ZipFile(archive) as package:
        package.extractall(MODEL_DIR.parent)
    archive.unlink(missing_ok=True)
    if not model_is_ready():
        raise RuntimeError("Το μοντέλο αγγλικά→ελληνικά δεν εγκαταστάθηκε.")


class LocalTranslator:
    """Τοπική μετάφραση Argos (CTranslate2), χωρίς Google."""

    def __init__(self):
        import ctranslate2
        import sentencepiece

        ensure_translation_model()
        self.sp = sentencepiece.SentencePieceProcessor()
        self.sp.Load(str(MODEL_DIR / "sentencepiece.model"))
        self.engine = ctranslate2.Translator(
            str(MODEL_DIR / "model"),
            device="cpu",
            compute_type="int8",
            inter_threads=1,
        )
        self.cache = {}

    def translate(self, text):
        cached = self.cache.get(text)
        if cached is not None:
            return cached
        chunks = _text_chunks(text)
        if not chunks:
            return ""
        encoded = []
        passthrough = []
        for chunk in chunks:
            if _mostly_greek(chunk):
                encoded.append(None)
                passthrough.append(chunk)
            else:
                encoded.append(self.sp.encode(chunk, out_type=str))
                passthrough.append(None)
        to_translate = [pieces for pieces in encoded if pieces]
        results = []
        if to_translate:
            results = self.engine.translate_batch(
                to_translate,
                beam_size=2,
                max_decoding_length=128,
                replace_unknowns=True,
            )
        lines = []
        result_index = 0
        for pieces, original in zip(encoded, passthrough):
            if pieces is None:
                lines.append(original)
                continue
            greek = self.sp.decode(results[result_index].hypotheses[0]).replace("\u2581", " ")
            result_index += 1
            greek = " ".join(greek.split())
            if greek:
                lines.append(greek)
        greek_text = "\n".join(lines)
        self.cache[text] = greek_text
        if len(self.cache) > 400:
            self.cache.clear()
            self.cache[text] = greek_text
        return greek_text


def pin_overlay(hwnd):
    style = _get_window_long(hwnd, GWL_EXSTYLE)
    style &= ~WS_EX_TRANSPARENT
    style |= WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
    _set_window_long(hwnd, GWL_EXSTYLE, style)
    user32.SetWindowPos(
        hwnd,
        HWND_TOPMOST,
        0,
        0,
        0,
        0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW | SWP_FRAMECHANGED,
    )
    # Η μετάφραση μένει ορατή, αλλά δεν μπαίνει στη λήψη της οθόνης.
    user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)


def raise_overlay(hwnd):
    user32.SetWindowPos(
        hwnd,
        HWND_TOPMOST,
        0,
        0,
        0,
        0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
    )


def load_shortcuts():
    for path in (SETTINGS_FILE, OLD_DATA_DIR / "settings.json"):
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            return {
                key: str(saved.get(key) or default)
                for key, default in DEFAULT_SHORTCUTS.items()
            }
        except (OSError, ValueError, TypeError):
            continue
    return DEFAULT_SHORTCUTS.copy()


def save_shortcuts(shortcuts):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(
        json.dumps(shortcuts, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def sequence_to_windows_hotkey(text):
    sequence = QtGui.QKeySequence(text)
    if sequence.isEmpty():
        raise ValueError("Η συντόμευση είναι κενή.")
    combination = sequence[0]
    qt_key = combination.key()
    qt_key = qt_key.value if hasattr(qt_key, "value") else int(qt_key)
    qt_modifiers = combination.keyboardModifiers()
    modifiers = MOD_NOREPEAT
    if qt_modifiers & QtCore.Qt.ControlModifier:
        modifiers |= MOD_CONTROL
    if qt_modifiers & QtCore.Qt.ShiftModifier:
        modifiers |= MOD_SHIFT
    if qt_modifiers & QtCore.Qt.AltModifier:
        modifiers |= MOD_ALT
    if qt_modifiers & QtCore.Qt.MetaModifier:
        modifiers |= MOD_WIN

    if QtCore.Qt.Key_F1.value <= qt_key <= QtCore.Qt.Key_F24.value:
        virtual_key = 0x70 + qt_key - QtCore.Qt.Key_F1.value
    elif 0x30 <= qt_key <= 0x39 or 0x41 <= qt_key <= 0x5A:
        virtual_key = qt_key
    elif qt_key == QtCore.Qt.Key_Space.value:
        virtual_key = 0x20
    else:
        raise ValueError("Χρησιμοποίησε γράμμα, αριθμό, Space ή F1–F24.")
    return modifiers, virtual_key


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, shortcuts, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Metafrasi — Ρυθμίσεις")
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)
        self.setMinimumWidth(420)

        form = QtWidgets.QFormLayout()
        self.edits = {}
        labels = (
            ("pause", "Παύση / συνέχεια:"),
            ("reselect", "Νέα περιοχή:"),
            ("settings", "Ρυθμίσεις:"),
            ("quit", "Έξοδος:"),
        )
        for key, title in labels:
            editor = QtWidgets.QKeySequenceEdit(QtGui.QKeySequence(shortcuts[key]))
            editor.setMaximumSequenceLength(1)
            form.addRow(title, editor)
            self.edits[key] = editor

        note = QtWidgets.QLabel(
            "Πάτησε τη συντόμευση που θέλεις, π.χ. Ctrl+F6 ή Alt+T."
        )
        note.setWordWrap(True)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.button(QtWidgets.QDialogButtonBox.Save).setText("Αποθήκευση")
        buttons.button(QtWidgets.QDialogButtonBox.Cancel).setText("Ακύρωση")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def shortcuts(self):
        return {
            key: editor.keySequence().toString(QtGui.QKeySequence.PortableText)
            for key, editor in self.edits.items()
        }


class GlobalHotkeyThread:
    """Windows hotkeys on their own message-loop thread."""

    def __init__(self, bindings):
        self.bindings = bindings
        self.callbacks = {item[0]: item[3] for item in bindings}
        self.registered_ids = []
        self.failures = []
        self.ready = threading.Event()
        self.thread_id = 0
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()
        self.ready.wait(2)
        return self.failures

    def _run(self):
        self.thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        try:
            for hotkey_id, modifiers, virtual_key, _callback, label in self.bindings:
                if user32.RegisterHotKey(
                    None, hotkey_id, modifiers, virtual_key
                ):
                    self.registered_ids.append(hotkey_id)
                else:
                    self.failures.append(label)
            self.ready.set()

            message = wintypes.MSG()
            while user32.GetMessageW(
                ctypes.byref(message), None, 0, 0
            ) > 0:
                if message.message == WM_HOTKEY:
                    callback = self.callbacks.get(message.wParam)
                    if callback is not None:
                        callback()
        finally:
            for hotkey_id in self.registered_ids:
                user32.UnregisterHotKey(None, hotkey_id)
            self.ready.set()

    def stop(self):
        if self.thread_id:
            user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)
        if self.thread.is_alive():
            self.thread.join(timeout=1)


class AreaSelector(QtWidgets.QWidget):
    """Διαφανής επιλογή περιοχής, ώστε να φαίνεται το παιχνίδι από κάτω."""

    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.begin = QtCore.QPoint()
        self.end = QtCore.QPoint()
        self.begin_global = QtCore.QPoint()
        self.end_global = QtCore.QPoint()
        self.is_drawing = False

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.Window
            | QtCore.Qt.NoDropShadowWindowHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))

        virtual = QtCore.QRect()
        for screen in QtGui.QGuiApplication.screens():
            virtual = virtual.united(screen.geometry())
        self.setGeometry(virtual)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0, 70))
        painter.setPen(QtGui.QColor(255, 255, 255))
        painter.setFont(QtGui.QFont("Segoe UI", 14))
        painter.drawText(
            self.rect().adjusted(16, 28, -16, 0),
            QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop,
            "Σύρε γύρω από τους υπότιτλους.\n"
            "Το παιχνίδι πρέπει να είναι borderless, όχι exclusive fullscreen.\n"
            "Ctrl+Shift+Q για έξοδο.",
        )
        if self.is_drawing:
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 180, 255), 2))
            painter.setBrush(QtGui.QBrush(QtGui.QColor(0, 180, 255, 40)))
            painter.drawRect(QtCore.QRect(self.begin, self.end))

    def mousePressEvent(self, event):
        self.begin = event.position().toPoint()
        self.end = self.begin
        self.begin_global = event.globalPosition().toPoint()
        self.end_global = self.begin_global
        self.is_drawing = True
        self.update()

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            self.end = event.position().toPoint()
            self.end_global = event.globalPosition().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        self.is_drawing = False
        self.end_global = event.globalPosition().toPoint()
        x1 = min(self.begin_global.x(), self.end_global.x())
        y1 = min(self.begin_global.y(), self.end_global.y())
        x2 = max(self.begin_global.x(), self.end_global.x())
        y2 = max(self.begin_global.y(), self.end_global.y())
        if x2 - x1 > 10 and y2 - y1 > 10:
            # Κρύβεται πρώτα ο selector, ώστε να βρούμε το παιχνίδι από κάτω.
            self.hide()
            QtWidgets.QApplication.processEvents()
            self.callback((x1, y1, x2, y2))
            self.close()
        else:
            sys.exit()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            sys.exit()


class CaptureGuide(QtWidgets.QWidget):
    """Λεπτό περίγραμμα στην περιοχή που πραγματικά διαβάζεται."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.WindowTransparentForInput
            | QtCore.Qt.WindowDoesNotAcceptFocus
            | QtCore.Qt.Tool
            | QtCore.Qt.NoDropShadowWindowHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)

    def showEvent(self, event):
        super().showEvent(event)
        pin_overlay(int(self.winId()))

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 200, 255), 2))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))

    def set_area(self, x1, y1, x2, y2):
        self.setGeometry(int(x1), int(y1), max(2, int(x2 - x1)), max(2, int(y2 - y1)))
        self.show()
        pin_overlay(int(self.winId()))


class GameOverlay(QtWidgets.QWidget):
    """Διαφανής μπάρα που μένει πάνω από το παιχνίδι χωρίς να παίρνει τα κλικ."""

    update_text_signal = QtCore.Signal(str)
    request_reselect = QtCore.Signal()
    pause_hotkey_signal = QtCore.Signal()
    reselect_hotkey_signal = QtCore.Signal()
    settings_hotkey_signal = QtCore.Signal()
    quit_hotkey_signal = QtCore.Signal()

    def __init__(self, subtitle_area):
        super().__init__()
        self.logical_area = subtitle_area
        self.physical_bbox, self.monitor_rect = logical_bbox_to_physical(*subtitle_area)
        self.physical_bbox = clip_bbox_to_window(self.physical_bbox)
        self.dx_region = None
        self.camera = None
        self.last_text = ""
        self._last_image_token = None
        self._last_scene = None
        self._last_ocr_time = 0.0
        self._misses = 0
        self._warned_black = False
        self._use_dxgi = False
        self._paused = threading.Event()
        self._stopped = threading.Event()
        self.shortcuts = load_shortcuts()
        self._settings_open = False
        self._hotkey_manager = None
        self.guide = CaptureGuide()
        self.pause_hotkey_signal.connect(self.toggle_pause)
        self.reselect_hotkey_signal.connect(self.reselect_area)
        self.settings_hotkey_signal.connect(self.open_settings)
        self.quit_hotkey_signal.connect(self.close_overlay)
        self.init_ui()
        self._update_guide()

        self._top_timer = QtCore.QTimer(self)
        self._top_timer.timeout.connect(self._keep_on_top)
        self._top_timer.start(300)

        self.worker_thread = threading.Thread(target=self.translation_loop, daemon=True)
        self.worker_thread.start()

    def init_ui(self):
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.WindowDoesNotAcceptFocus
            | QtCore.Qt.NoDropShadowWindowHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.close_button = QtWidgets.QPushButton("×", self)
        self.close_button.clicked.connect(self.close_overlay)
        self.close_button.setToolTip("Κλείσιμο")

        self.pause_button = QtWidgets.QPushButton("Ⅱ", self)
        self.pause_button.clicked.connect(self.toggle_pause)
        self.pause_button.setToolTip("Παύση / συνέχεια (F6)")

        self.reselect_button = QtWidgets.QPushButton("⌖", self)
        self.reselect_button.clicked.connect(self.reselect_area)
        self.reselect_button.setToolTip("Νέα περιοχή ανάγνωσης (F7)")

        self.settings_button = QtWidgets.QPushButton("⚙", self)
        self.settings_button.clicked.connect(self.open_settings)
        self.settings_button.setToolTip("Ρυθμίσεις συντομεύσεων")

        control_style = (
            """
            QPushButton {
                color: #FFFFFF;
                background-color: #111111;
                border: none;
                border-radius: 6px;
                font-size: 20px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                color: #55C8FF;
            }
            """
        )
        for button in (
            self.settings_button,
            self.reselect_button,
            self.pause_button,
            self.close_button,
        ):
            button.setFixedSize(26, 26)
            button.setCursor(QtCore.Qt.PointingHandCursor)
            button.setFocusPolicy(QtCore.Qt.NoFocus)
            button.setStyleSheet(control_style)
        self.close_button.setStyleSheet(
            control_style + "QPushButton:hover { color: #FF5A5A; }"
        )

        self.label = QtWidgets.QLabel("Φόρτωση...", self)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setTextFormat(QtCore.Qt.PlainText)
        self.label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.label.setStyleSheet(
            """
            color: #FFFFFF;
            background-color: #111111;
            font-family: "Segoe UI";
            font-size: 20px;
            font-weight: 600;
            border-radius: 8px;
            padding: 8px 122px 8px 16px;
            """
        )
        layout.addWidget(self.label)
        self.update_text_signal.connect(self.set_translated_text)
        self.place_bar()

    def place_bar(self):
        x1, y1, x2, y2 = self.logical_area
        screen = QtGui.QGuiApplication.screenAt(
            QtCore.QPoint(int((x1 + x2) / 2), int((y1 + y2) / 2))
        ) or QtGui.QGuiApplication.primaryScreen()
        bounds = screen.availableGeometry()
        width = max(320, min(int(bounds.width() * 0.72), bounds.width() - 24))
        self.label.setFixedWidth(width - 4)
        height = min(150, max(56, self.label.sizeHint().height() + 6))
        left = bounds.x() + (bounds.width() - width) // 2
        # Σαν υπότιτλοι ταινίας: πάντα στο κάτω κέντρο, πάνω από τη γραμμή εργασιών.
        margin = max(18, int(bounds.height() * 0.03))
        top = bounds.y() + bounds.height() - margin - height
        capture = QtCore.QRect(int(x1), int(y1), max(1, int(x2 - x1)), max(1, int(y2 - y1)))
        bar = QtCore.QRect(int(left), int(top), int(width), int(height))
        if bar.intersects(capture) and y2 + 8 + height <= bounds.y() + bounds.height():
            top = y2 + 8
        self.setFixedSize(int(width), int(height))
        self.move(int(left), int(top))
        right = self.width() - 28
        self.close_button.move(right, 0)
        self.pause_button.move(right - 28, 0)
        self.reselect_button.move(right - 56, 0)
        self.settings_button.move(right - 84, 0)
        for button in (
            self.settings_button,
            self.reselect_button,
            self.pause_button,
            self.close_button,
        ):
            button.raise_()

    def showEvent(self, event):
        super().showEvent(event)
        pin_overlay(int(self.winId()))
        self.register_hotkeys()
        for button in (
            self.settings_button,
            self.reselect_button,
            self.pause_button,
            self.close_button,
        ):
            button.raise_()

    def nativeEvent(self, eventType, message):
        try:
            if message:
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == WM_NCHITTEST:
                    x = ctypes.c_short(msg.lParam & 0xFFFF).value
                    y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                    local = self.mapFromGlobal(QtCore.QPoint(x, y))
                    for button in (
                        self.settings_button,
                        self.reselect_button,
                        self.pause_button,
                        self.close_button,
                    ):
                        if button.geometry().adjusted(-3, -6, 3, 6).contains(local):
                            return True, HTCLIENT
                    return True, HTTRANSPARENT
        except Exception:
            pass
        return False, 0

    def _update_guide(self):
        x1, y1, x2, y2 = physical_to_logical(self.physical_bbox, self.monitor_rect)
        self.guide.set_area(x1, y1, x2, y2)

    def close_overlay(self):
        self._stopped.set()
        self._top_timer.stop()
        self.unregister_hotkeys()
        if self.guide is not None:
            self.guide.close()
        self.close()
        QtWidgets.QApplication.quit()

    def unregister_hotkeys(self):
        if self._hotkey_manager is not None:
            self._hotkey_manager.stop()
            self._hotkey_manager = None

    def register_hotkeys(self):
        self.unregister_hotkeys()
        try:
            parsed = {
                key: sequence_to_windows_hotkey(self.shortcuts[key])
                for key in DEFAULT_SHORTCUTS
            }
        except ValueError:
            self.shortcuts = DEFAULT_SHORTCUTS.copy()
            parsed = {
                key: sequence_to_windows_hotkey(value)
                for key, value in DEFAULT_SHORTCUTS.items()
            }
        bindings = [
            (
                HOTKEY_PAUSE_ID,
                *parsed["pause"],
                self.pause_hotkey_signal.emit,
                self.shortcuts["pause"],
            ),
            (
                HOTKEY_RESELECT_ID,
                *parsed["reselect"],
                self.reselect_hotkey_signal.emit,
                self.shortcuts["reselect"],
            ),
            (
                HOTKEY_SETTINGS_ID,
                *parsed["settings"],
                self.settings_hotkey_signal.emit,
                self.shortcuts["settings"],
            ),
            (
                HOTKEY_QUIT_ID,
                *parsed["quit"],
                self.quit_hotkey_signal.emit,
                self.shortcuts["quit"],
            ),
        ]
        self._hotkey_manager = GlobalHotkeyThread(bindings)
        failures = self._hotkey_manager.start()
        self._update_shortcut_tooltips()
        return failures

    def _update_shortcut_tooltips(self):
        self.pause_button.setToolTip(
            f"Παύση / συνέχεια ({self.shortcuts['pause']})"
        )
        self.reselect_button.setToolTip(
            f"Νέα περιοχή ανάγνωσης ({self.shortcuts['reselect']})"
        )
        self.settings_button.setToolTip(
            f"Ρυθμίσεις ({self.shortcuts['settings']})"
        )
        self.close_button.setToolTip(
            f"Κλείσιμο ({self.shortcuts['quit']})"
        )

    def open_settings(self):
        if getattr(self, "_settings_open", False):
            return
        self._settings_open = True
        old_shortcuts = self.shortcuts.copy()
        self.unregister_hotkeys()
        dialog = SettingsDialog(old_shortcuts)
        accepted = dialog.exec() == QtWidgets.QDialog.Accepted
        new_shortcuts = dialog.shortcuts() if accepted else None
        if not accepted:
            self.register_hotkeys()
            self._settings_open = False
            return

        try:
            parsed = {
                key: sequence_to_windows_hotkey(new_shortcuts[key])
                for key in DEFAULT_SHORTCUTS
            }
            if len(set(parsed.values())) != len(parsed):
                raise ValueError("Οι συντομεύσεις πρέπει να είναι διαφορετικές μεταξύ τους.")
        except ValueError as error:
            self.shortcuts = old_shortcuts
            self.register_hotkeys()
            self._settings_open = False
            QtWidgets.QMessageBox.warning(self, "Συντομεύσεις", str(error))
            return

        self.shortcuts = new_shortcuts
        failures = self.register_hotkeys()
        if failures:
            self.shortcuts = old_shortcuts
            self.register_hotkeys()
            QtWidgets.QMessageBox.warning(
                self,
                "Συντομεύσεις",
                "Η συντόμευση χρησιμοποιείται από άλλο πρόγραμμα: "
                + ", ".join(failures),
            )
            self._settings_open = False
            return
        save_shortcuts(self.shortcuts)
        self._settings_open = False

    def toggle_pause(self):
        if self._paused.is_set():
            self._paused.clear()
            self.pause_button.setText("Ⅱ")
            self.setWindowOpacity(1.0)
            self.guide.setWindowOpacity(1.0)
        else:
            self._paused.set()
            self.pause_button.setText("▶")
            self.setWindowOpacity(0.18)
            self.guide.setWindowOpacity(0.18)
        self._update_shortcut_tooltips()

    def reselect_area(self):
        self._paused.set()
        self.guide.hide()
        self.hide()
        self.request_reselect.emit()

    def set_capture_area(self, area):
        self.logical_area = area
        self.physical_bbox, self.monitor_rect = logical_bbox_to_physical(*area)
        self.physical_bbox = clip_bbox_to_window(self.physical_bbox)
        self.dx_region = None
        self.last_text = ""
        self._last_image_token = None
        self._last_scene = None
        self._last_ocr_time = 0.0
        self._misses = 0
        self._warned_black = False
        self._use_dxgi = False
        self.pause_button.setText("Ⅱ")
        self._update_shortcut_tooltips()
        self.setWindowOpacity(1.0)
        self._paused.clear()
        self.place_bar()
        self._update_guide()
        self.update_text_signal.emit("Αναμονή για υπότιτλους...")
        self.show()
        pin_overlay(int(self.winId()))

    def _keep_on_top(self):
        if self.isVisible():
            raise_overlay(int(self.winId()))
            if self.guide.isVisible():
                raise_overlay(int(self.guide.winId()))

    def set_translated_text(self, text):
        self.label.setText(text)
        self.place_bar()

    def _image_token(self, img):
        sample = img.convert("L").resize((48, 16), Image.Resampling.BILINEAR)
        sample = sample.filter(ImageFilter.GaussianBlur(2))
        pixels = (np.asarray(sample, dtype=np.uint16) // 24).astype(np.uint8)
        return hash(pixels.tobytes())

    def _scene_changed(self, img):
        sample = np.asarray(
            img.convert("L").resize((6, 3), Image.Resampling.BOX), dtype=np.uint16
        )
        signature = (sample // 40).astype(np.uint8).tobytes()
        previous = self._last_scene
        self._last_scene = signature
        if previous is None:
            return False
        changed = sum(a != b for a, b in zip(previous, signature))
        return changed >= 8

    def _grab_dxgi(self):
        if self.camera is None or self.dx_region is None:
            return None
        try:
            frame = self.camera.grab(self.dx_region)
        except Exception as error:
            log(f"Σφάλμα DXGI: {error}")
            self.camera = None
            self._use_dxgi = False
            return None
        if frame is not None and not _is_black_bgra(frame):
            return _bgra_to_image(frame)
        return None

    def capture_image(self):
        if self.camera is not None and self.dx_region is not None:
            frame = self._grab_dxgi()
            if frame is not None:
                self._use_dxgi = True
                return frame
        grabbed = ImageGrab.grab(bbox=self.physical_bbox)
        if not _is_black_image(grabbed):
            return grabbed
        if self.camera is None:
            self._open_camera()
            frame = self._grab_dxgi()
            if frame is not None:
                self._use_dxgi = True
                return frame
        self._warn_black()
        return None

    def _warn_black(self):
        if self._warned_black:
            return
        self._warned_black = True
        self.update_text_signal.emit(
            "Μαύρη εικόνα. Βάλε το παιχνίδι σε borderless windowed, όχι exclusive fullscreen."
        )

    def _open_camera(self):
        try:
            camera, width, height = open_game_camera(self.monitor_rect)
            mon_left, mon_top, _, _ = self.monitor_rect
            px1, py1, px2, py2 = self.physical_bbox
            self.dx_region = _clamp_region(
                (px1 - mon_left, py1 - mon_top, px2 - mon_left, py2 - mon_top),
                width,
                height,
            )
            self.camera = camera
            log("Λήψη παιχνιδιού: DXGI")
        except Exception as error:
            log(f"Το DXGI δεν ξεκίνησε, χρήση ImageGrab: {error}")
            self.camera = None

    def translation_loop(self):
        self.update_text_signal.emit("Φόρτωση τοπικού μεταφραστή...")
        try:
            translator = LocalTranslator()
        except Exception as error:
            log(f"Ο τοπικός μεταφραστής δεν ξεκίνησε: {error}")
            self.update_text_signal.emit("Δεν φορτώθηκε ο τοπικός μεταφραστής.")
            return
        log("Μετάφραση: τοπικά, αγγλικά → ελληνικά")
        self._open_camera()
        self.update_text_signal.emit("Αναμονή για υπότιτλους...")
        showed_error = False

        while not self._stopped.is_set():
            if self._paused.is_set():
                time.sleep(0.1)
                continue
            started = time.perf_counter()
            try:
                img = self.capture_image()
                if img is not None:
                    token = self._image_token(img)
                    now = time.perf_counter()
                    should_read = token != self._last_image_token or (
                        not self.last_text and now - self._last_ocr_time >= 0.7
                    )
                    if should_read:
                        self._last_image_token = token
                        self._last_ocr_time = now
                        current_text = read_text(img)
                        if current_text and _is_valid_subtitle(
                            current_text, small=_region_is_small(img)
                        ):
                            self._misses = 0
                            if current_text != self.last_text:
                                self.last_text = current_text
                                try:
                                    translated = translator.translate(current_text)
                                    if translated:
                                        showed_error = False
                                        self.update_text_signal.emit(translated)
                                except Exception as trans_err:
                                    log(f"Σφάλμα μετάφρασης: {trans_err}")
                                    if not showed_error:
                                        showed_error = True
                                        self.update_text_signal.emit("Σφάλμα μετάφρασης.")
                        else:
                            self._misses += 1
                            if self._misses >= 6 and self.last_text:
                                self.last_text = ""
                                self.update_text_signal.emit("Αναμονή για υπότιτλους...")
            except Exception as error:
                log(f"Σφάλμα OCR: {error}")
                if not showed_error:
                    showed_error = True
                    self.update_text_signal.emit("Δεν διαβάζεται το κείμενο της οθόνης.")

            elapsed = time.perf_counter() - started
            time.sleep(max(0.05, 0.12 - elapsed))


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    if ICON_FILE.is_file():
        app.setWindowIcon(QtGui.QIcon(str(ICON_FILE)))

    overlay_window = None
    selector_window = None

    def show_selector():
        nonlocal overlay_window, selector_window
        if selector_window is not None and selector_window.isVisible():
            selector_window.raise_()
            selector_window.activateWindow()
            return
        if overlay_window is not None:
            overlay_window._paused.set()
            overlay_window.guide.hide()
            overlay_window.hide()
        selector_window = AreaSelector(start_overlay)
        selector_window.show()
        selector_window.raise_()
        selector_window.activateWindow()

    def start_overlay(area):
        nonlocal overlay_window, selector_window
        if selector_window is not None:
            selector_window.close()
            selector_window = None
        if overlay_window is None:
            overlay_window = GameOverlay(area)
            overlay_window.request_reselect.connect(show_selector)
            overlay_window.show()
        else:
            overlay_window.set_capture_area(area)

    show_selector()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
