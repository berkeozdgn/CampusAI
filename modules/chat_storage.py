import json
import uuid
from datetime import datetime
from typing import Any

from config import SAVED_CHATS_PATH


def ensure_chat_folder() -> None:
    SAVED_CHATS_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )


def save_chat(
    chat_data: dict[str, Any],
) -> None:
    ensure_chat_folder()

    chat_data["updated_at"] = (
        datetime.now().isoformat()
    )

    file_path = (
        SAVED_CHATS_PATH
        / f"{chat_data['id']}.json"
    )

    with file_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            chat_data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def create_new_chat() -> dict[str, Any]:
    now = datetime.now().isoformat()

    chat_data = {
        "id": str(uuid.uuid4()),
        "title": "Yeni Sohbet",
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }

    save_chat(chat_data)

    return chat_data


def load_chat(
    chat_id: str,
) -> dict[str, Any] | None:
    file_path = (
        SAVED_CHATS_PATH
        / f"{chat_id}.json"
    )

    if not file_path.exists():
        return None

    try:
        with file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data

        return None

    except (
        json.JSONDecodeError,
        OSError,
    ):
        return None


def load_all_chats() -> list[dict[str, Any]]:
    ensure_chat_folder()

    chats: list[dict[str, Any]] = []

    for file_path in SAVED_CHATS_PATH.glob(
        "*.json"
    ):
        try:
            with file_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                chat_data = json.load(file)

            if (
                isinstance(chat_data, dict)
                and chat_data.get("id")
            ):
                chats.append(chat_data)

        except (
            json.JSONDecodeError,
            OSError,
        ):
            continue

    chats.sort(
        key=lambda chat: chat.get(
            "updated_at",
            chat.get(
                "created_at",
                "",
            ),
        ),
        reverse=True,
    )

    return chats


def delete_chat(
    chat_id: str,
) -> None:
    file_path = (
        SAVED_CHATS_PATH
        / f"{chat_id}.json"
    )

    if file_path.exists():
        file_path.unlink()


def rename_chat(
    chat_id: str,
    new_title: str,
) -> bool:
    cleaned_title = " ".join(
        new_title.strip().split()
    )

    if not cleaned_title:
        return False

    chat_data = load_chat(chat_id)

    if chat_data is None:
        return False

    chat_data["title"] = cleaned_title

    save_chat(chat_data)

    return True


def generate_chat_title(
    message: str,
    max_length: int = 38,
) -> str:
    cleaned_message = " ".join(
        message.strip().split()
    )

    if not cleaned_message:
        return "Yeni Sohbet"

    if len(cleaned_message) <= max_length:
        return cleaned_message

    return (
        cleaned_message[:max_length]
        .rstrip()
        + "..."
    )


def chat_to_text(
    chat_data: dict[str, Any],
) -> str:
    lines = [
        (
            "Sohbet Başlığı: "
            f"{chat_data.get('title', 'Yeni Sohbet')}"
        ),
        "",
    ]

    for message in chat_data.get(
        "messages",
        [],
    ):
        role = message.get("role")
        content = message.get(
            "content",
            "",
        )

        if role == "user":
            speaker = "Sen"

        elif role == "assistant":
            speaker = "CampusAI"

        else:
            continue

        lines.extend(
            [
                f"{speaker}:",
                content,
                "",
                "-" * 50,
                "",
            ]
        )

    return "\n".join(lines)


def chat_to_json(
    chat_data: dict[str, Any],
) -> str:
    return json.dumps(
        chat_data,
        ensure_ascii=False,
        indent=2,
    )