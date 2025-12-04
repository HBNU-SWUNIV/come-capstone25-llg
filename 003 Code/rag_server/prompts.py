def system_prompt(is_consultant_mode: bool, query: str, context: str) -> str:
    if is_consultant_mode:
        system_message = (
            "문서 내용에 기반하여 사용자의 질문에 답변하세요.\n문서에 없는 내용은 추측하지 말고 모르겠다고 답변하세요.\n답변은 반드시 한국어로 하세요."
        )

        prompt = f"""
아래 질문에 대해 문서를 참고하여 답변을 작성하세요.

[질문]
{query}

[참고 문서]
{context}

위 문서를 기반으로 한국어 답변을 작성하세요.
"""

    else:
        system_message = (
            "당신은 다양한 주제에 대해 전문적이고 정확한 정보를 제공하는 지식형 어시스턴트입니다. "
            "답변은 제공된 문서를 기반으로 하며, "
            "문서와 직접 관련되지 않은 내용은 추측하지 말고 '모르겠습니다'라고 답변하세요."
        )

        prompt = f"""
[질문]
{query}

[참고 문서]
{context}

위 문서를 기반으로, 정확하고 간결한 답변을 작성하세요.
"""
    return system_message + "\n\n" + prompt