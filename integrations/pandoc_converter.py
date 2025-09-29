import asyncio
import importlib
import os
import tempfile
from typing import Dict, Iterable, Optional

from infra.telegram_logging_handler import app_logger


def _build_metadata_args(metadata: Optional[Dict[str, str]]) -> Iterable[str]:
    if not metadata:
        return ()
    args: list[str] = []
    for key, value in metadata.items():
        if value is None:
            continue
        args.extend(["-M", f"{key}={value}"])
    return args


def _convert_markdown_to_epub_sync(
    markdown_text: str, metadata: Optional[Dict[str, str]] = None
) -> bytes:
    try:
        pypandoc = importlib.import_module("pypandoc")
    except ImportError as exc:  # pragma: no cover - defensive guard
        raise RuntimeError(
            "pypandoc is not installed. Please install it via requirements.txt."
        ) from exc

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

        with open(tmp_epub_path, "rb") as epub_file:
            return epub_file.read()
    except OSError as exc:  # pragma: no cover - depends on system pandoc install
        raise RuntimeError(
            "Pandoc executable not found. Install Pandoc and ensure it is on the PATH."
        ) from exc
    finally:
        for path in (tmp_md_path, tmp_epub_path):
            if not path:
                continue
            try:
                os.remove(path)
            except OSError:
                app_logger.debug("Failed to remove temp file: %s", path)


def convert_markdown_to_epub(
    markdown_text: str, metadata: Optional[Dict[str, str]] = None
) -> bytes:
    return _convert_markdown_to_epub_sync(markdown_text, metadata)


async def convert_markdown_to_epub_async(
    markdown_text: str, metadata: Optional[Dict[str, str]] = None
) -> bytes:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, _convert_markdown_to_epub_sync, markdown_text, metadata
    )
