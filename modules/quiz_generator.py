import json
import re
from typing import Any


def generate_quiz_prompt(
    context: str,
    question_count: int,
    difficulty: str,
) -> str:
    """
    Yapay zekânın yalnızca geçerli JSON formatında
    quiz üretmesini isteyen promptu hazırlar.
    """

    return f"""
Aşağıdaki ders içeriğine dayanarak Türkçe bir quiz oluştur.

DERS İÇERİĞİ:
{context}

KURALLAR:
- Toplam soru sayısı: {question_count}
- Zorluk seviyesi: {difficulty}
- Her soru 4 seçenekli olsun.
- Seçenekler A, B, C ve D olarak verilsin.
- Her sorunun yalnızca bir doğru cevabı olsun.
- Sorular sadece verilen ders içeriğine dayansın.
- Bilgi uydurma.
- Açıklamalar kısa ve öğretici olsun.
- Çıktının tamamı yalnızca geçerli JSON olsun.
- JSON dışında hiçbir açıklama, başlık veya kod bloğu yazma.

Aşağıdaki JSON yapısını aynen kullan:

{{
  "title": "Quiz başlığı",
  "questions": [
    {{
      "question": "Soru metni",
      "options": {{
        "A": "Birinci seçenek",
        "B": "İkinci seçenek",
        "C": "Üçüncü seçenek",
        "D": "Dördüncü seçenek"
      }},
      "correct_answer": "A",
      "explanation": "Doğru cevabın kısa açıklaması"
    }}
  ]
}}
"""


def clean_json_response(response_text: str) -> str:
    """
    Modelin JSON'u kod bloğu içinde döndürmesi durumunda
    ```json ve ``` işaretlerini temizler.
    """

    cleaned_text = response_text.strip()

    cleaned_text = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned_text,
        flags=re.IGNORECASE,
    )

    cleaned_text = re.sub(
        r"\s*```$",
        "",
        cleaned_text,
    )

    return cleaned_text.strip()


def parse_quiz_response(
    response_text: str,
) -> dict[str, Any]:
    """
    Yapay zekâ cevabını Python sözlüğüne dönüştürür
    ve temel kontrolleri yapar.
    """

    cleaned_text = clean_json_response(response_text)

    try:
        quiz_data = json.loads(cleaned_text)
    except json.JSONDecodeError as error:
        raise ValueError(
            "Yapay zekâ geçerli bir quiz formatı üretmedi."
        ) from error

    if not isinstance(quiz_data, dict):
        raise ValueError(
            "Quiz verisi sözlük biçiminde olmalıdır."
        )

    questions = quiz_data.get("questions")

    if not isinstance(questions, list) or not questions:
        raise ValueError(
            "Quiz içinde geçerli soru bulunamadı."
        )

    valid_questions = []

    for index, question_data in enumerate(
        questions,
        start=1,
    ):
        if not isinstance(question_data, dict):
            continue

        question = str(
            question_data.get("question", "")
        ).strip()

        options = question_data.get("options")
        correct_answer = str(
            question_data.get(
                "correct_answer",
                "",
            )
        ).strip().upper()

        explanation = str(
            question_data.get(
                "explanation",
                "",
            )
        ).strip()

        if not question:
            continue

        if not isinstance(options, dict):
            continue

        normalized_options = {
            key: str(options.get(key, "")).strip()
            for key in ["A", "B", "C", "D"]
        }

        if not all(normalized_options.values()):
            continue

        if correct_answer not in {
            "A",
            "B",
            "C",
            "D",
        }:
            continue

        valid_questions.append(
            {
                "id": index,
                "question": question,
                "options": normalized_options,
                "correct_answer": correct_answer,
                "explanation": (
                    explanation
                    or "Bu soru için açıklama bulunmuyor."
                ),
            }
        )

    if not valid_questions:
        raise ValueError(
            "Yapay zekâdan gelen sorular geçerli değil."
        )

    return {
        "title": str(
            quiz_data.get(
                "title",
                "CampusAI Quiz",
            )
        ).strip(),
        "questions": valid_questions,
    }


def calculate_quiz_result(
    quiz_data: dict[str, Any],
    user_answers: dict[int, str],
) -> dict[str, Any]:
    """
    Kullanıcının cevaplarını kontrol eder ve sonucu hesaplar.
    """

    questions = quiz_data.get("questions", [])

    correct_count = 0
    unanswered_count = 0
    results = []

    for question in questions:
        question_id = question["id"]
        user_answer = user_answers.get(
            question_id,
            "",
        )

        correct_answer = question[
            "correct_answer"
        ]

        if not user_answer:
            unanswered_count += 1

        is_correct = (
            user_answer == correct_answer
        )

        if is_correct:
            correct_count += 1

        results.append(
            {
                "question_id": question_id,
                "question": question["question"],
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "explanation": question[
                    "explanation"
                ],
            }
        )

    total_questions = len(questions)

    success_percentage = (
        round(
            correct_count
            / total_questions
            * 100
        )
        if total_questions
        else 0
    )

    return {
        "correct_count": correct_count,
        "wrong_count": (
            total_questions
            - correct_count
            - unanswered_count
        ),
        "unanswered_count": unanswered_count,
        "total_questions": total_questions,
        "success_percentage": success_percentage,
        "results": results,
    }