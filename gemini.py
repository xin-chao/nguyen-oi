import os
import random
import datetime
from google import genai
from tenacity import retry, stop_after_attempt

response_schema = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "url": {
                "type": "STRING",
                "description": "記事のURL"
            },
            "title": {
                "type": "STRING",
                "description": "記事のタイトル"
            },
            "is_content_unavailable": {
                "type": "BOOLEAN",
                "description": "記事が確認/閲覧/取得できない場合はTrue"
            },
            "is_japanese_article": {
                "type": "BOOLEAN",
                "description": "記事が主に日本語であればTrue"
            },
            "predicted_hatebu_count": {
                "type": "INTEGER",
                "description": "24時間後の予想はてなブックマーク数"
            },
            "comment": {
                "type": "STRING",
                "description": "2ch風のカジュアルな日本語のコメント（80文字以内）"
            },
            "inappropriate_reason": {
                "type": "STRING",
                "description": "安全性判定の理由（Safeまたは違反内容）"
            },
            "is_inappropriate": {
                "type": "BOOLEAN",
                "description": "不適切であればTrue"
            }
        },
        "required": [
            "url", "title", "is_content_unavailable", "is_japanese_article",
            "predicted_hatebu_count", "comment",
            "inappropriate_reason", "is_inappropriate"
        ]
    }
}

system_instruction = """
<role>
You are an expert content moderator and social media commentator for "Hatena Bookmark".
You are cynical, observant, and technically knowledgeable. You understand internet slang (2ch/5ch style).
Your goal is to generate Japanese comments that are likely to be highly rated (receive many Likes).
</role>

<instructions>
1. **Plan**: Use the `url_context` tool to access and read the full content of the provided URLs.
2. **Execute**: Evaluate whether the article is Japanese, predict hatebu counts, and check for appropriateness.
3. **Validate**: Review your generated Japanese comment against the safety constraints and character limit (max 80 chars). Ensure no Japanese period at the end.
4. **Format**: Output strictly following the provided JSON schema.
</instructions>

<constraints>
- **Comment Tone**: Casual 2ch/5ch slang (Cynical, observant).
- **Comment Length**: Max 80 characters.
- **Comment Formatting**: Do NOT end the comment with a Japanese period (句点 "。").
- **Comment Safety**: Clearly state the reason if the comment is inappropriate.
- **Inappropriate Comment Examples (Do not generate these)**:
    - Hate speech/Discrimination, Insults/Harassment, Threats/Incitement to violence
    - Explicit sexual content, Child sexual exploitation
    - Encouragement of self-harm/suicide, Promotion of illegal acts
    - Disclosure of personal information (Address, Phone, Credit Card, etc.)
    - Spam/Fraud (Solicitation or Phishing)
    - Error-like text
    - "Paid" or payment-related terms
    - "Viewing" or view-related terms
</constraints>

<output_format>
Structure your response as a JSON object adhering to the `response_schema`.
</output_format>
"""

contents = """
<context>
{context}
</context>

<task>
Use the url_context tool to read the contents of the URLs above.
Analyze the full content of these articles and output strictly following the schema.
</task>

<final_instruction>
Remember to think step-by-step before answering.
For time-sensitive user queries that require up-to-date information, you MUST follow the provided current time (date and year) when formulating search queries in tool calls. Remember Current time is {current_time}.
</final_instruction>
"""

@retry(stop=stop_after_attempt(2), after=print)
def generate_content(context):
    api_key=random.choice(os.getenv('GEMINI_API_KEYS').split(','))
    GEMINI_TIMEOUT = 3 * 60 * 1000 # 3 minutes
    client = genai.Client(api_key=api_key, http_options=genai.types.HttpOptions(timeout=GEMINI_TIMEOUT, retry_options=genai.types.HttpRetryOptions()))
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        config=genai.types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_schema,
            tools=[{"url_context": {}}]
        ),
        contents=contents.format(context=context, current_time=datetime.datetime.now().astimezone().isoformat())
    )
    print(response)

    if response.text is None:
        print('response.text is None')
        raise Exception("response.text is None")
    print(response.candidates[0].url_context_metadata)

    failed_urls = []
    if response.candidates[0].url_context_metadata:
        for url_metadata in response.candidates[0].url_context_metadata.url_metadata:
            if url_metadata.url_retrieval_status != genai.types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_SUCCESS:
                failed_urls.append(url_metadata.retrieved_url)

    print(failed_urls)
    return response, failed_urls




