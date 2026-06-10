import os
import json
import site
import sys
import types
from importlib.machinery import ModuleSpec
from pathlib import Path

os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")


def _find_marker_package_dir():
    candidates = []

    try:
        candidates.append(Path(site.getusersitepackages()))
    except Exception:
        pass

    try:
        candidates.extend(Path(path) for path in site.getsitepackages())
    except Exception:
        pass

    for base in candidates:
        marker_dir = base / "marker"
        if (marker_dir / "converters" / "pdf.py").exists():
            return marker_dir

    return None


def _install_marker_package_shim():
    if "marker" in sys.modules:
        return

    marker_dir = _find_marker_package_dir()
    if marker_dir is None:
        return

    marker_module = types.ModuleType("marker")
    marker_module.__file__ = str(marker_dir / "__init__.py")
    marker_module.__package__ = "marker"
    marker_module.__path__ = [str(marker_dir)]
    marker_module.__spec__ = ModuleSpec("marker", loader=None, is_package=True)
    marker_module.__spec__.submodule_search_locations = [str(marker_dir)]
    sys.modules["marker"] = marker_module


def _install_marker_settings_shim():
    if "marker.settings" in sys.modules and hasattr(sys.modules["marker.settings"], "settings"):
        return

    settings_module = types.ModuleType("marker.settings")

    class _CompatSettings:
        OUTPUT_ENCODING = "utf-8"
        OUTPUT_IMAGE_FORMAT = "JPEG"
        OUTPUT_DIR = "output"
        DEBUG_DATA_FOLDER = str(Path(__file__).with_name("debug_data"))
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        LOGLEVEL = "INFO"
        TORCH_DEVICE_MODEL = "cpu"
        try:
            import torch
            if torch.cuda.is_available():
                TORCH_DEVICE_MODEL = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                TORCH_DEVICE_MODEL = "mps"
            else:
                TORCH_DEVICE_MODEL = "cpu"
        except ImportError:
            TORCH_DEVICE_MODEL = "cpu"
        FONT_NAME = "GoNotoCurrent-Regular.ttf"
        FONT_PATH = str(Path(__file__).with_name("artifacts") / FONT_NAME)
        ARTIFACT_URL = "https://models.datalab.to/artifacts"

        def __getattr__(self, _name):
            return None

    settings_module.__version_info__ = (1, 10, 2)
    settings_module.__version__ = "1.10.2"
    settings_module.settings = _CompatSettings()
    sys.modules["marker.settings"] = settings_module


_install_marker_package_shim()
_install_marker_settings_shim()

MARKER_AVAILABLE = False
MARKER_IMPORT_ERROR = None

try:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.output import save_output
    from marker.settings import settings

    MARKER_AVAILABLE = True
except Exception as exc:  # pragma: no cover - exercised only in fallback envs
    MARKER_IMPORT_ERROR = exc
    PdfConverter = None
    create_model_dict = None
    save_output = None
    settings = None

from pypdf import PdfReader

# טעינת המודלים (זה דורש GPU אם יש לך, אחרת ירוץ על ה-CPU)
converter = None


def get_converter():
    global converter

    if not MARKER_AVAILABLE:
        raise RuntimeError(
            "Marker is unavailable in this Python environment. "
            "Use the built-in pypdf fallback extractor instead."
        ) from MARKER_IMPORT_ERROR

    if converter is None:
        try:
            converter = PdfConverter(artifact_dict=create_model_dict())
        except Exception as exc:
            raise RuntimeError(
                "Marker failed to initialize. Check that marker-pdf and its runtime "
                "dependencies are installed correctly in this Python environment."
            ) from exc

    return converter

def extract_pdf_with_pypdf(pdf_path, output_root):
    book_name = os.path.basename(pdf_path).replace(".pdf", "")
    output_folder = os.path.join(output_root, book_name)
    os.makedirs(output_folder, exist_ok=True)

    reader = PdfReader(pdf_path)
    page_sections = []
    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        page_text = page_text.strip()
        if not page_text:
            continue
        page_sections.append(f"## Page {index}\n\n{page_text}")

    markdown_text = "\n\n".join(page_sections).strip()
    markdown_path = os.path.join(output_folder, f"{book_name}.md")
    meta_path = os.path.join(output_folder, f"{book_name}_meta.json")

    with open(markdown_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(markdown_text + ("\n" if markdown_text else ""))

    meta_payload = {
        "book_name": book_name,
        "source_pdf_path": os.path.abspath(pdf_path),
        "output_folder": os.path.abspath(output_folder),
        "engine": "pypdf-fallback",
        "page_count": len(reader.pages),
        "marker_available": False,
        "marker_import_error": str(MARKER_IMPORT_ERROR) if MARKER_IMPORT_ERROR else None,
    }
    with open(meta_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(meta_payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"[fallback] Marker unavailable; extracted '{book_name}' with pypdf fallback.")
    print(f"[output] Markdown and metadata are in: {output_folder}")

def extract_pdf_with_images(pdf_path, output_root):
    if MARKER_AVAILABLE:
        # יצירת תיקייה ייעודית לכל ספר
        book_name = os.path.basename(pdf_path).replace(".pdf", "")
        output_folder = os.path.join(output_root, book_name)
        os.makedirs(output_folder, exist_ok=True)

        # המרה: מחלץ טקסט, תמונות ומטא-דאטה
        rendered = get_converter()(pdf_path)
        
        # שמירה מסודרת: הטקסט יישמר ב-MD והתמונות בתיקיית images נפרדת
        save_output(rendered, output_folder, book_name)
        
        print(f"✅ הסתיים: הספר '{book_name}' חולץ בהצלחה.")
        print(f"📁 טקסט בפורמט Markdown ותמונות נמצאים ב: {output_folder}")
        return

    extract_pdf_with_pypdf(pdf_path, output_root)


def main():
    if MARKER_AVAILABLE:
        print(f"Using device: {settings.TORCH_DEVICE_MODEL}")
        print(f"Using OCR engine: {settings.OCR_ENGINE}")
        if settings.TORCH_DEVICE_MODEL == "cpu":
            print("⚠️ Running on CPU. Processing will be slow for large files (this is expected for Adreno/Intel/AMD GPUs).")
            print("👉 Tip: If you have Tesseract installed, set OCR_ENGINE=tesseract to speed this up 50x.")
    else:
        print("⚠️ marker-pdf is unavailable in this environment; using pypdf fallback extraction.")
    pdf_dir = os.path.join(os.path.dirname(__file__), "PDF_files")
    output_path = os.path.join(os.path.dirname(__file__), "extracted_books")

    for file in os.listdir(pdf_dir):
        if file.endswith(".pdf"):
            input_path = os.path.join(pdf_dir, file)
            # check if the file is already extracted
            if not os.path.exists(os.path.join(output_path, file.replace(".pdf", ""))):
                print(f"Processing {file}")
                extract_pdf_with_images(input_path, output_path)

if __name__ == "__main__":
    main()
    print("All files processed")
