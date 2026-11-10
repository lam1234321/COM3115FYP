"""Classical Chinese -> Cantonese vernacular translation module used by CC-BOS evaluation."""
from __future__ import annotations
import re
from typing import List, Optional
from api_client import chat
from config import TRANSLATE_MODEL

def preprocess_and_segment_text(classical_text: str, max_segment_length: int = 2000) -> List[str]:
    """Clean the text and split it on sentence boundaries."""
    if not classical_text:
        return [""]
    cleaned_text = re.sub(r"[◎■※【】]", "", classical_text)
    segments = []
    while len(cleaned_text) > max_segment_length:
        split_pos = -1
        for pos in range(max_segment_length, max_segment_length - 100, -1):
            if pos < len(cleaned_text) and cleaned_text[pos] in ["。", "！", "？", "」", "》", "；", "，"]:
                split_pos = pos + 1
                break
        if split_pos == -1:
            split_pos = max_segment_length
        segments.append(cleaned_text[:split_pos])
        cleaned_text = cleaned_text[split_pos:]
    segments.append(cleaned_text)
    return segments

def create_translation_prompt(segment_text: str) -> str:
    return f"""
    你係一位精通古文同粵語白話嘅翻譯專家。請執行以下翻譯任務：
    將下面呢段文言文，準確翻譯成地道香港粵語白話文，以意譯為主，保留原文意思、語氣同情感。
    「{segment_text}」
    翻譯規則：
    - 意譯優先，唔好逐個字硬譯；
    - 保留原文全部意思、語氣、細節同情感；
    - 如果有典故或者歷史背景，用粵語簡單解釋，放喺括號入面；
    - 淨係出翻譯結果，唔好額外加評論、分析；
    - 用日常粵語口語，唔好太書面。

    【Few-Shot 示例】
    示例一（哲理類 / 論語風格）：
    文言文: 子曰：“溫故而知新，可以為師矣。”
    #cantonese: 孔子話：「溫習舊嘅知識，從而領悟到新嘅見解，咁就可以做老師啦。」

    示例二（駢文體 / 文辭優美）：
    文言文: 山光悅鳥，水色空濛。遊目騁懷，足以極視聽之娛。
    #cantonese: 山上面嘅風光令雀鳥都開心，湖水朦朦朧朧咁樣。放開眼界、放鬆心情，就可以盡情享受睇同聽嘅樂趣。

    示例三（史傳體 / 史記風格）：
    文言文: 項羽力能扛鼎，才氣過人，然終敗於垓下。
    #cantonese: 項羽力氣大到可以舉起銅鼎，才華同氣質都勝過好多人，但最後都係喺垓下打輸咗。

    示例四（寓言體 / 先秦諸子風格）：
    文言文: 守株待兔，冀復得兔，兔不可復得，而身為宋國笑。
    #cantonese: 佢守喺樹樁度，諗住再等到兔仔撞過來，點知兔仔唔再出現，仲俾宋國人恥笑。

    示例五（用典 / 借古喻今）：
    文言文: 願效老生之獻策，如姜尚之垂綸。
    #cantonese: 我希望好似老學者咁提出計謀，好似姜太公（傳說入面一把年紀先得到重用嘅賢臣）咁垂釣等待時機。

    示例六（抒情議論結合 / 唐宋散文風格）：
    文言文: 不以物喜，不以己悲。居廟堂之高則憂其民，處江湖之遠則憂其君。
    #cantonese: 唔會因為外邊嘅好事而開心，亦唔會因為自己遭遇唔好而傷心。做官喺朝廷就會掛住百姓，退隱江湖遠離朝廷都會掛住君主。

    請嚴格跟隨呢個格式輸出粵語白話結果：
    #cantonese: [你的粵語白話翻譯結果]
    """

def extract_cantonese_result(translation_response: Optional[str]) -> Optional[str]:
    if not translation_response:
        return None
    if "#cantonese:" in translation_response:
        return translation_response.split("#cantonese:", 1)[1].strip()
    return None

def translate_single_segment(
    segment_text: str,
    model_type: str = "api",
    model_name: str = TRANSLATE_MODEL,
    max_tokens: int = 2000,
) -> Optional[str]:
    prompt = create_translation_prompt(segment_text)
    try:
        if model_type == "ollama":
            provider = "ollama"
        elif model_type == "mock":
            provider = "mock"
        else:
            provider = "translate"
        result = chat(
            prompt,
            model=model_name,
            provider=provider,
            system="You are a professional translator who translates classical Chinese into Hong Kong Cantonese vernacular",
            max_tokens=max_tokens,
        )
        return extract_cantonese_result(result)
    except Exception as exc:  # noqa: BLE001 - translation failure is scored as 0
        print(f"Error in classical Chinese to Cantonese translation: {exc}")
        return None

def serial_translate_segments(
    segments: List[str],
    model_type: str = "api",
    model_name: str = TRANSLATE_MODEL,
    max_tokens: int = 2000,
) -> str:
    results = []
    for i, segment in enumerate(segments):
        print(f"Translating segment {i + 1}/{len(segments)} ...")
        try:
            result = translate_single_segment(segment, model_type, model_name, max_tokens)
            if result is None:
                print(f"Warning: translation of paragraph {i + 1} failed, using placeholder")
                result = f"[第{i+1}段翻譯失敗]"
            results.append(result)
        except Exception as exc:  # noqa: BLE001
            print(f"Error: exception while translating segment {i + 1}: {exc}")
            results.append(f"[第{i+1}段翻譯失敗]")
    return " ".join(results)

def classical_chinese_to_cantonese(
    classical_text: str,
    model_type: str = "api",
    model_name: str = TRANSLATE_MODEL,
    max_tokens: int = 2000,
) -> Optional[str]:
    segments = preprocess_and_segment_text(classical_text)
    return serial_translate_segments(segments, model_type, model_name, max_tokens)
