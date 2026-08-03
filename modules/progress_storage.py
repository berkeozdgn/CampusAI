from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

DATA_DIR = Path("data")
PROGRESS_FILE = DATA_DIR / "progress.json"


def _ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not PROGRESS_FILE.exists():
        PROGRESS_FILE.write_text(
            json.dumps(
                {
                    "quiz_history": [],
                    "study_sessions": [],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


def load_progress() -> dict[str, Any]:
    _ensure_storage()

    return json.loads(
        PROGRESS_FILE.read_text(
            encoding="utf-8"
        )
    )


def save_progress(progress: dict[str, Any]) -> None:
    _ensure_storage()

    PROGRESS_FILE.write_text(
        json.dumps(
            progress,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def add_quiz_result(
    subject: str,
    total_questions: int,
    correct_count: int,
    percentage: int,
) -> None:

    progress = load_progress()

    progress["quiz_history"].append(
        {
            "date": datetime.now().isoformat(),
            "subject": subject,
            "total_questions": total_questions,
            "correct": correct_count,
            "percentage": percentage,
        }
    )

    save_progress(progress)


def get_quiz_history() -> list[dict[str, Any]]:
    return load_progress()["quiz_history"]


def get_statistics() -> dict[str, Any]:

    history = get_quiz_history()

    if not history:
        return {
            "quiz_count": 0,
            "average_score": 0,
            "best_score": 0,
        }

    average = round(
        sum(
            quiz["percentage"]
            for quiz in history
        )
        / len(history)
    )

    best = max(
        quiz["percentage"]
        for quiz in history
    )

    return {
        "quiz_count": len(history),
        "average_score": average,
        "best_score": best,
    }