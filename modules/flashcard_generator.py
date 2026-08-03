import json
import re
from typing import Any


def generate_flashcard_prompt(
    context: str,
    card_count: int,
    difficulty: str,
) -> str:
    """
    Yapay zekâdan yalnızca geçerli JSON formatında
    flashcard üretmesini isteyen promptu hazırlar.
    """

    return f"""
Aşağıdaki ders içeriğine dayanarak Türkçe çalışma kartları oluştur.

DERS İÇERİĞİ:
{context}

KURALLAR:
- Toplam kart sayısı: {card_count}
- Zorluk seviyesi: {difficulty}
- Kartların ön yüzünde kısa bir soru veya kavram olsun.
- Arka yüzünde açık, doğru ve kısa bir açıklama olsun.
- Kartlar yalnızca verilen ders içeriğine dayansın.
- Bilgi uydurma.
- Aynı veya çok benzer kartlar oluşturma.
- Çıktının tamamı yalnızca geçerli JSON olsun.
- JSON dışında başlık, açıklama veya kod bloğu yazma.

Aşağıdaki JSON yapısını aynen kullan:

{{
  "title": "Flashcard setinin başlığı",
  "cards": [
    {{
      "front": "Kartın ön yüzü",
      "back": "Kartın arka yüzündeki açıklama"
    }}
  ]
}}
"""


def clean_json_response(response_text: str) -> str:
    """
    Model cevabındaki ```json ve ``` işaretlerini temizler.
    """

    cleaned_text = response_text.strip()

    cleaned_text = re.sub(
        r"^```(?:json)?\\s*",
        "",
        cleaned_text,
        flags=re.IGNORECASE,
    )

    cleaned_text = re.sub(
        r"\\s*```$",
        "",
        cleaned_text,
    )

    return cleaned_text.strip()


def parse_flashcard_response(
    response_text: str,
) -> dict[str, Any]:
    """
    Yapay zekâ cevabını doğrular ve kullanılabilir
    flashcard verisine dönüştürür.
    """

    cleaned_text = clean_json_response(response_text)

    try:
        flashcard_data = json.loads(cleaned_text)

    except json.JSONDecodeError as error:
        raise ValueError(
            "Yapay zekâ geçerli bir flashcard formatı üretmedi."
        ) from error

    if not isinstance(flashcard_data, dict):
        raise ValueError(
            "Flashcard verisi sözlük biçiminde olmalıdır."
        )

    cards = flashcard_data.get("cards")

    if not isinstance(cards, list) or not cards:
        raise ValueError(
            "Geçerli flashcard bulunamadı."
        )

    valid_cards = []

    for index, card in enumerate(cards, start=1):
        if not isinstance(card, dict):
            continue

        front = str(
            card.get("front", "")
        ).strip()

        back = str(
            card.get("back", "")
        ).strip()

        if not front or not back:
            continue

        valid_cards.append(
            {
                "id": index,
                "front": front,
                "back": back,
            }
        )

    if not valid_cards:
        raise ValueError(
            "Yapay zekâdan gelen kartlar geçerli değil."
        )

    return {
        "title": str(
            flashcard_data.get(
                "title",
                "CampusAI Flashcards",
            )
        ).strip(),
        "cards": valid_cards,
    }