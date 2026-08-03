from pathlib import Path
from typing import Any

import streamlit as st

from modules.dashboard import render_dashboard


def show_dashboard_page(
    active_subject: str,
    model_name: str,
    chats: list[dict[str, Any]],
) -> str | None:
    """
    Dashboard ekranını gösterir.

    Dönen değerler:
    - new_chat
    - open_chat
    - summary
    - quiz
    - planner
    - None
    """

    return render_dashboard(
        active_subject=active_subject,
        model_name=model_name,
        chats=chats,
        pdf_root=Path("data/pdfs"),
    )