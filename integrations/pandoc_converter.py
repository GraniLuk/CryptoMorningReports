import asyncio
import importlib
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path, PureWindowsPath
from threading import Lock

from infra.telegram_logging_handler import app_logger


_pypandoc_lock = Lock()
_pypandoc_module = None


def _normalize_custom_dir(custom_dir: str) -> str:
    expanded = os.path.expandvars(str(Path(custom_dir).expanduser()))

    if os.name != "nt":
        windows_candidate = PureWindowsPath(expanded)
        if windows_candidate.drive:
            home_root = os.environ.get("HOME")
            if home_root and windows_candidate.drive.lower() == "d:":
                suffix_parts = windows_candidate.parts[1:]
                return str(Path(home_root, *suffix_parts))
        expanded = expanded.replace("\\", "/")

    return os.path.normpath(expanded)


def _resolve_pandoc_download_dir() -> str:
    custom_dir = os.environ.get("PANDOC_DOWNLOAD_DIR")
    if custom_dir:
        return _normalize_custom_dir(custom_dir)

    script_root = os.environ.get("AZUREWEBJOBSSCRIPTROOT")
    if script_root:
        return str(Path(script_root) / ".pandoc-cache")

    home_dir = os.environ.get("HOME") or str(Path.cwd())
    return str(Path(home_dir) / ".pandoc-cache")


def _ensure_pandoc_available():
    global _pypandoc_module  # noqa: PLW0603
    with _pypandoc_lock:
        if _pypandoc_module is not None:
            return _pypandoc_module

        try:
            pypandoc = importlib.import_module("pypandoc")
        except ImportError as exc:  # pragma: no cover - defensive guard
            msg = "pypandoc is not installed. Please install it via requirements.txt."
            raise RuntimeError(msg) from exc

        # First try to use system-installed pandoc
        try:
            existing_path = pypandoc.get_pandoc_path()
            if existing_path and Path(existing_path).is_file():
                app_logger.info("Using system pandoc at %s", existing_path)
                _pypandoc_module = pypandoc
                return _pypandoc_module
        except OSError:
            pass  # System pandoc not found, will try other methods

        # For local development, try to find pandoc in PATH
        import shutil

        pandoc_in_path = shutil.which("pandoc")
        if pandoc_in_path:
            app_logger.info("Using pandoc from PATH at %s", pandoc_in_path)
            os.environ["PYPANDOC_PANDOC"] = pandoc_in_path
            _pypandoc_module = pypandoc
            return _pypandoc_module

        # Only download if running in Azure (has AZUREWEBJOBSSCRIPTROOT)
        if os.environ.get("AZUREWEBJOBSSCRIPTROOT"):
            app_logger.info("Pandoc binary not found; downloading for Azure environment...")
            target_dir = _resolve_pandoc_download_dir()
            try:
                Path(target_dir).mkdir(parents=True, exist_ok=True)
                pandoc_path = pypandoc.download_pandoc(
                    targetfolder=target_dir, delete_installer=True
                )

                # download_pandoc may return None on some platforms; construct expected path
                if not pandoc_path:
                    pandoc_path = str(Path(target_dir) / "pandoc")

                if not Path(pandoc_path).is_file():
                    msg = f"Pandoc binary not found at expected location: {pandoc_path}"
                    raise FileNotFoundError(msg)

                os.environ["PYPANDOC_PANDOC"] = pandoc_path
                app_logger.info("Pandoc downloaded to %s", pandoc_path)
                _pypandoc_module = pypandoc
                return _pypandoc_module
            except Exception as exc:
                app_logger.exception("Pandoc download failed; target_dir=%s", target_dir)
                msg = (
                    "Failed to download Pandoc automatically. "
                    "Ensure the Function App has outbound internet access and a writable storage location."
                )
                raise RuntimeError(msg) from exc
        else:
            # Local environment but pandoc not found
            msg = (
                "Pandoc not found. For local development, please install pandoc: "
                "https://pandoc.org/installing.html"
            )
            raise RuntimeError(msg)


def _build_metadata_args(metadata: dict[str, str] | None) -> Iterable[str]:
    # Ensure required EPUB metadata fields are present
    defaults = {
        "lang": "en-US",
        "language": "en-US",
    }

    merged = {**defaults, **(metadata or {})}

    args: list[str] = []
    for key, value in merged.items():
        args.extend(["-M", f"{key}={value}"])
    return args


def _convert_markdown_to_epub_sync(
    markdown_text: str, metadata: dict[str, str] | None = None
) -> bytes:
    pypandoc = _ensure_pandoc_available()

    metadata_args = list(_build_metadata_args(metadata))

    # Pandoc requires a physical file for certain conversions on Windows, so write to disk.
    # Use NamedTemporaryFile with delete=False to be compatible with Windows file handles.
    tmp_md_path = None
    tmp_epub_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as tmp_md:
            tmp_md.write(markdown_text)
            tmp_md_path = tmp_md.name

        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp_epub:
            tmp_epub_path = tmp_epub.name

        pypandoc.convert_file(
            tmp_md_path,
            "epub",
            format="md",
            outputfile=tmp_epub_path,
            extra_args=metadata_args,
        )

        with Path(tmp_epub_path).open("rb") as epub_file:
            return epub_file.read()
    except OSError as exc:  # pragma: no cover - depends on system pandoc install
        msg = "Pandoc executable not found. Install Pandoc and ensure it is on the PATH."
        raise RuntimeError(msg) from exc
    finally:
        for path in (tmp_md_path, tmp_epub_path):
            if not path:
                continue
            try:
                Path(path).unlink()
            except OSError:
                app_logger.debug("Failed to remove temp file: %s", path)


def convert_markdown_to_epub(markdown_text: str, metadata: dict[str, str] | None = None) -> bytes:
    return _convert_markdown_to_epub_sync(markdown_text, metadata)


async def convert_markdown_to_epub_async(
    markdown_text: str, metadata: dict[str, str] | None = None
) -> bytes:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _convert_markdown_to_epub_sync, markdown_text, metadata)
