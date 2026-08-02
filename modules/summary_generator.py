def generate_summary(context):

    prompt = f"""
Aşağıdaki konuyu kısa ve anlaşılır şekilde özetle.

{context}
"""

    return prompt