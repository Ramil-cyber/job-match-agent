"""Reusable Streamlit controls for pasted and uploaded document text."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import streamlit as st

from job_match_agent.document_extraction import (
    MAX_UPLOAD_SIZE_MB,
    DocumentExtractionError,
    extract_document,
)

PASTE_METHOD = "Paste text"
UPLOAD_METHOD = "Upload file"


@dataclass(frozen=True)
class DocumentInputValue:
    """Current text and extraction state for one interface input."""

    text: str
    error: str | None = None


def _character_caption(text: str, max_characters: int) -> str:
    """Build a consistent, readable character counter."""

    return f"{len(text):,} / {max_characters:,} characters"


def _clear_upload_cache(key_prefix: str) -> None:
    """Remove extracted upload content when the upload control is not in use."""

    for suffix in (
        "uploaded_file",
        "upload_fingerprint",
        "uploaded_text",
        "upload_error",
        "upload_format",
    ):
        st.session_state.pop(f"{key_prefix}_{suffix}", None)


def render_document_input(
    label: str,
    *,
    key_prefix: str,
    max_characters: int,
    paste_placeholder: str,
) -> DocumentInputValue:
    """Render paste/upload choices and return validated, editable text."""

    method = st.radio(
        f"{label} input method",
        (PASTE_METHOD, UPLOAD_METHOD),
        horizontal=True,
        captions=(
            "Type or paste editable text.",
            f"PDF, DOCX, or TXT · {MAX_UPLOAD_SIZE_MB} MB maximum.",
        ),
        key=f"{key_prefix}_method",
        width="stretch",
    )

    if method == PASTE_METHOD:
        _clear_upload_cache(key_prefix)
        text = st.text_area(
            label,
            height=250,
            max_chars=max_characters,
            placeholder=paste_placeholder,
            key=f"{key_prefix}_pasted_text",
        )
        st.caption(_character_caption(text, max_characters))
        return DocumentInputValue(text=text)

    uploaded_file = st.file_uploader(
        f"Upload {label.lower()}",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=False,
        max_upload_size=MAX_UPLOAD_SIZE_MB,
        help=(
            f"One PDF, DOCX, or UTF-8 TXT file, up to {MAX_UPLOAD_SIZE_MB} MB. "
            "Scanned PDFs and legacy .doc files are not supported."
        ),
        key=f"{key_prefix}_uploaded_file",
    )

    if uploaded_file is None:
        for suffix in (
            "upload_fingerprint",
            "uploaded_text",
            "upload_error",
            "upload_format",
        ):
            st.session_state.pop(f"{key_prefix}_{suffix}", None)
        st.caption(
            f"The file is processed in memory and is not saved by the app. "
            f"Extracted text is limited to {max_characters:,} characters."
        )
        return DocumentInputValue(text="")

    data = uploaded_file.getvalue()
    fingerprint = hashlib.sha256(
        uploaded_file.name.encode("utf-8", errors="replace") + b"\x00" + data
    ).hexdigest()
    fingerprint_key = f"{key_prefix}_upload_fingerprint"
    text_key = f"{key_prefix}_uploaded_text"
    error_key = f"{key_prefix}_upload_error"
    format_key = f"{key_prefix}_upload_format"

    if st.session_state.get(fingerprint_key) != fingerprint:
        st.session_state[fingerprint_key] = fingerprint
        st.session_state[text_key] = ""
        st.session_state[error_key] = None
        st.session_state[format_key] = None

        try:
            extracted = extract_document(
                data,
                uploaded_file.name,
                max_characters=max_characters,
            )
        except DocumentExtractionError as error:
            st.session_state[error_key] = str(error)
        else:
            st.session_state[text_key] = extracted.text
            st.session_state[format_key] = extracted.format_name

    extraction_error = st.session_state.get(error_key)
    if extraction_error:
        st.error(str(extraction_error))
        return DocumentInputValue(text="", error=str(extraction_error))

    format_name = st.session_state.get(format_key, "document")
    st.success(f"{format_name} text extracted. Review it before analyzing.")
    text = st.text_area(
        f"Extracted {label.lower()} text (editable)",
        height=250,
        max_chars=max_characters,
        key=text_key,
    )
    st.caption(_character_caption(text, max_characters))
    return DocumentInputValue(text=text)
