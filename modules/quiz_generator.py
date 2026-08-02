def generate_quiz(context):

    prompt = f"""
Aşağıdaki içerikten 5 adet çoktan seçmeli soru oluştur.

{context}
"""

    return prompt