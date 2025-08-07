from flask import Flask, request, jsonify, render_template
import os, json, re, logging
from logging.handlers import RotatingFileHandler
from openai import OpenAI

base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, 'templates')

app = Flask(__name__, template_folder=template_dir)

log_dir = os.path.join(base_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'server.log')
handler = RotatingFileHandler(log_file, maxBytes=10000000, backupCount=5, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

#ADD YOUR API KEY THERE
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "sk-xxxxxxxxxxxxxxxxxxxxxxx"))

def translate_ja_to_en(text_ja):
    prompt = f"以下の日本語を自然な英語に翻訳してください：\n{text_ja}"
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10000
        )
        translated = response.choices[0].message.content.strip()
        return translated
    except Exception as e:
        return f"翻訳エラー: {e}"


def generate_prompt(endpoint, question, options, answer, previous_story=None):
    iwf_japanese = """
【評価基準（IWF: Item-Writing Flaws）】
1. 曖昧または不明確な表現がないこと：設問や選択肢が明確で、読み手に誤解を与えないような言葉で書かれていること。(10)
2. 紛らわしい選択肢（不適切な誤答肢）がないこと：誤答肢も一見正しく見えるように作られており、学習効果を高めるように設計されていること。(10)
3. 「上記のどれでもない」などの選択肢を避けること：「上記のどれでもない」は、正答ではなく消去法の能力を測るにとどまり、避けるべきである。(2)
4. 正解肢が最も長いなどの手がかりがないこと：すべての選択肢の長さと詳細の量が均等であり、正解肢だけが長く目立つようなことがないこと。(2)
5. 問題文に不要な情報が含まれていないこと：解答に関係のない余分な情報が設問文に含まれていないこと。(2)
6. 真偽問題（True/False形式）でないこと：選択肢が単なる真偽判断の羅列（True/False）ではないこと。(2)
7. 選択肢に複合的なヒント（収束手がかり）が含まれていないこと：複数の情報の組み合わせによって答えが推測できるような構造を避けること。(2)
8. 論理的な手がかり（正解と設問文の論理的整合）がないこと：問題文と正解肢が論理的に一致しすぎて、答えが推測できるような構成を避けること。(2)
9. 「すべて正しい」などの選択肢がないこと：「すべて正しい」のような選択肢は、部分的な知識からの推測を許してしまうため避けること。(2)
10. 空欄補充型ではないこと：文中の空欄に当てはまる語を選ばせるタイプの問題（空欄補充）でないこと。(2)
11. "常に、決して、全て"などの絶対表現がないこと：選択肢に「常に」「決して」「すべて」などの絶対的な表現が含まれていないこと。(2)
12. 設問と正解肢の語句が不自然に一致していないこと：設問中の語句が正解肢のみに繰り返されていない、または他の選択肢にも公平に使われていること。((2))
13. 設問文が明確で焦点が定まっていること：選択肢を見なくても何が問われているかが明確で、焦点がずれていないこと。(2)
14. 組み合わせ型選択肢（K型）がないこと：複数の正解肢の組み合わせを選ばせるような問題形式（K型）を避けること。(2)
15. 文法的一貫性があること：すべての選択肢が設問文と文法的に一致し、構成が統一されていること。(2)
16. 順序が論理的・時系列的であること：選択肢の並びが意味的または数値的に自然であること。(2)
17. 「しばしば」「たまに」など曖昧な副詞を避けていること：「よく」「たまに」など解釈に個人差が出る語は使用しないこと。(2)
18. 正解は1つのみであること：選択肢の中で正解は1つに限定されており、複数の正解肢が存在しないこと。(2)
19. 設問文が否定形でないこと：「〜でないのはどれか」「〜しないものを選べ」などの否定文を避けること。(2)
20. 重要かつ明確な内容に基づいていること：設問は学習目標に関連した核心的な内容を扱い、単なる記憶ではなく理解や応用を評価するよう設計されていること。(2)
21. 各選択肢が重複していないこと：選択肢同士が意味的にかぶらず、明確に区別できるようになっていること。(2)
22. 正答の位置が偏っていないこと：選択肢の正解が常にAやDなど特定の位置に偏らないよう、配置が分散されていること。(2)
23. テスト項目間に内容の依存性がないこと：設問同士が連動せず、それぞれ独立に解答できるようになっていること。(2)
24. 選択肢が文法的・意味的に設問と一致していること：選択肢が設問文と文法的に対応し、読みやすさが確保されていること。(2)
25. 選択肢の順番が自然であること：数値や時間、論理の順序に従って選択肢が並べられていること。(2)
"""


    if endpoint == 'improve':
        return (
        f"まず、IWFの基準に照らして評価し、10点満点スコア（例：スコア：X/10）を提示してください。\n"
        f"そのうえで、この問題に関しての知識の分析や、どの点を改善するとさらに良くなるかを丁寧に説明してください。\n"
        f"また、問題が取り扱っている知識内容や、学習者が理解すべき重要な概念・考え方についても、分かりやすく解説してください。\n"
        f"※ 直接的な修正案や模範解答は提示しないでください。\n\n"
        f"問題：{question}\n"
        f"選択肢：\n" + "\n".join([f"- {option}" for option in options]) +
        f"\n正解：{answer}\n\n{iwf_japanese}"
        )

    elif endpoint == 'validate':
        return (
        f"次の選択式クイズ問題について、以下の観点で妥当性を確認してください。\n\n"
        f"【確認すべきポイント】\n"
        f"1. 正解が実際に正しいかどうか（誤答ではないか）\n"
        f"2. 選択肢の中に他にも正解とみなせるものがないか（唯一の正解か）\n"
        f"3. 問題文の表現が明確で曖昧さがないか\n"
        f"4. 学習者の知識を適切に測れる内容か\n"
        f"※ 模範解答や問題の書き換え案は提示しないでください。\n"
        f"※ 簡潔かつ論理的に説明してください。\n\n"
        f"問題：{question}\n"
        f"選択肢：\n" + "\n".join([f"- {option}" for option in options]) +
        f"\n正解：{answer}\n"
        )



    elif endpoint == 'enhance':
        return (
        f"次の選択式クイズ問題について、学習者の思考をより深く促すために、難易度を高める工夫を提案してください。\n"
        f"まず、IWFの基準に照らして問題の質と現在の難易度を10点満点で評価し（例：スコア：X/10）、\n\n"
        f"次に、以下の観点に沿って具体的な難易度を高める余地がどこにあるかを分析してください。（ただし具体的な修正内容や模範解答は提示しないでください）：\n"
        f"・問題文の構成（語彙や論理展開を複雑にする）\n"
        f"・選択肢の設計（紛らわしい誤答肢を加える、正解にたどり着くには複数の知識が必要など）\n"
        f"・問題が測定する知識レベル（記憶レベルから理解・応用へ）\n\n"
        f"また、問題が取り扱っている知識の背景や、学習者が理解すべき核心的な考え方についても簡潔に解説してください。\n\n"
        f"問題：{question}\n"
        f"選択肢：\n" + "\n".join([f"- {option}" for option in options]) +
        f"\n正解：{answer}\n\n{iwf_japanese}"
        )


    elif endpoint == 'story':
        return (
            "次の条件に従い、以下の情報に基づく物語とタスクを含むJSONオブジェクトを生成してください。\n"
            "【条件】\n"
            "0.物語は一人称視点で書き、「わたしは〜」「〜した」といった語り口調を使うこと。"
            "1. 物語は300文字以内にまとめること。\n"
            "2. 物語は童話・奇幻のテイストを持ち、必ず主人公を'わたし'とすること。\n"
            "3. 物語は前のストーリーと連続性を持ち、次の展開へ繋がる流れを持つこと。\n"
            "4. 物語の末尾には、読者が続きを知りたくなるような悬念（解決すべき困難や問題）を必ず含め、その困難に対して物語の内容に沿った具体的かつ創意工夫に富んだ解決策を、タスクの 'description' に記載すること。\n"
            "・必ず有効なJSON形式で出力すること。余計なテキストは一切含めないこと。\n"
            "・キー 'story' に生成された物語の文章を、キー 'task' には 'description'（タスクの説明）と 'type'（タスクの種類：'improve', 'enhance', 'validate' のいずれか）を含むオブジェクトを記載すること。\n\n"
            "【情報】\n"
            "前のストーリー:\n" + (previous_story if previous_story else "") + "\n"
            "クイズ問題:\n" + question + "\n\n"
            "出力例:\n"
            '{"story": "ここに300文字以内の童話風の物語が入ります。物語の末尾には、解決すべき困難が示されます。", "task": {"description": "物語の流れに沿い、例えば〇〇することで困難を解決する", "type": "improve"}}'
        )
    elif endpoint == 'beginning':
        return (
            "以下の条件に従い、'わたし'を主人公とする物語と、それに関連したタスクを含むJSONオブジェクトを生成してください。\n"
            "【条件】\n"
            "0.物語は一人称視点で書き、「わたしは〜」「〜した」といった語り口調を使うこと。"
            "1. 物語は300文字以内。\n"
            "2. 物語は童話風・奇幻のテイストを持ち、やさしく、楽しく、子供にもわかりやすい言葉で書いてください。\n"
            "3. 物語には当日のテーマ ヒープソート を自然に導入してください。\n"
            "4. 物語の最後には、読者が先を知りたくなるような悬念（解決すべき問題）を提示し、物語に沿った形でその問題の解決策をタスクの 'description' に記載すること。\n"
            "5. 有効なJSON形式で出力し、余計な文字を含めないこと。\n\n"
            "出力形式：\n"
            '{"story": "ここに300文字以内の童話風の物語が入ります", "task": {"description": "ここに物語と関連した具体的な行動を", "type": "enhance"}}'
        )

def generate_suggestion(option, context):
    prompt = (
    f"次の選択肢について、誤解しやすい点や関連知識を簡潔に説明してください。\n"
    f"※ 絶対に正解を示さないでください。\n"
    f"※ 出力は20文字前後の簡潔な説明文にしてください。\n\n"
    f"問題文：{context}\n選択肢：{option}\n\n出力："
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000
        )
        suggestion = response.choices[0].message.content.strip()
    except Exception as e:
        suggestion = f"サジェスチョンの生成中にエラーが発生しました: {e}"
    return suggestion

def generate_response_with_retries(endpoint, question, options, answer, previous_story=None, attempt=0):
    prompt = generate_prompt(endpoint, question, options, answer, previous_story)
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000
        )
        generated_text = response.choices[0].message.content.strip()
        print(f"試行 {attempt + 1} 回目, 生成結果: {generated_text}")
        return generated_text
    except Exception as e:
        print(f"エラー: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/improve', methods=['POST'])
def improve():
    app.logger.info("POST /improve リクエスト受信")
    data = request.json
    question = data.get('question')
    options = data.get('options')
    answer = data.get('answer')
    app.logger.info("入力内容: 問題=%s | 正解=%s | 選択肢=%s", question, answer, options)
    improvement_text = generate_response_with_retries('improve', question, options, answer)
    if improvement_text is None:
        return jsonify({"error": "複数回試行後、適切な内容の生成に失敗しました。"}), 400
    suggestions = []
    for option in options:
        suggestion = generate_suggestion(option, question)
        suggestions.append(suggestion)
    app.logger.info("生成内容: %s", improvement_text[:5000])
    app.logger.info("提案一覧: %s", suggestions)

    return jsonify({"text": improvement_text, "suggestions": suggestions})

@app.route('/validate', methods=['POST'])
def validate():
    app.logger.info("POST /validate リクエスト受信")
    data = request.json
    question = data.get('question')
    options = data.get('options')
    answer = data.get('answer')
    app.logger.info("入力: validate 問題=%s, 正解=%s, 選択肢=%s", question, answer, options)
    validation_text = generate_response_with_retries('validate', question, options, answer)
    if validation_text is None:
        return jsonify({"error": "複数回試行後、適切な内容の生成に失敗しました。"}), 400
    app.logger.info("出力: %s", validation_text[:5000])
    return jsonify({"text": validation_text})

@app.route('/enhance', methods=['POST'])
def enhance():
    app.logger.info("POST /enhance リクエスト受信")
    data = request.json
    question = data.get('question')
    options = data.get('options')
    answer = data.get('answer')
    app.logger.info("入力内容: 問題=%s | 正解=%s | 選択肢=%s", question, answer, options)
    enhanced_text = generate_response_with_retries('enhance', question, options, answer)
    if enhanced_text is None:
        return jsonify({"error": "複数回試行後、適切な内容の生成に失敗しました。"}), 400
    suggestions = []
    for option in options:
        suggestion = generate_suggestion(option, question)
        suggestions.append(suggestion)
    app.logger.info("生成内容: %s", enhanced_text[:5000])
    app.logger.info("提案一覧: %s", suggestions)
    return jsonify({"text": enhanced_text, "suggestions": suggestions})

@app.route('/generate-story', methods=['POST'])
def generate_story():
    app.logger.info("POST /generate_story リクエスト受信")
    data = request.json
    question = data.get('question')
    previous_story = data.get('previous_story', '')
    endpoint = 'beginning' if not previous_story.strip() else 'story'
    generated_text = generate_response_with_retries(endpoint, question, [], None, previous_story=previous_story)
    if generated_text is None:
        return jsonify({"error": "複数回試行後、適切なストーリーの生成に失敗しました。"}), 400
    try:
        parsed = json.loads(generated_text)
        story_part = parsed.get("story", "").strip()
        task_obj = parsed.get("task", {})
        if isinstance(task_obj, dict):
            task_description = task_obj.get("description", "").strip()
            task_type = task_obj.get("type", "").strip()
        else:
            task_description = str(task_obj).strip()
            task_type = None
        if not task_description:
            task_description = "生成されたタスクはありません。"
            task_type = None
        allowed_types = ['improve', 'enhance', 'validate']
        if task_type not in allowed_types:
            task_type = 'improve'
        app.logger.info("生成されたストーリー: %s", story_part[:20000])
        app.logger.info("出力タスク: %s | タイプ: %s", task_description, task_type)

    except Exception as e:
        print("JSON解析エラー:", e)
        story_part = generated_text.strip()
        task_description = "生成されたタスクはありません。"
        task_type = None
    print(f"生成されたストーリー: {story_part}")
    print(f"生成されたタスク: {task_description} (タスクタイプ: {task_type})")
    story_part_en = translate_ja_to_en(story_part)
    image_prompt = f"generate a cute, dreamly,fairy tale styled,Picture book style painting with strong connection of the following story, should not including any word or sentence\n\n{story_part_en}"
    try:
        image_response = client.images.generate(
            prompt=image_prompt,
            size="256x256",
            n=1
        )
        image_url = image_response.data[0].url
        print(f"生成された画像のURL: {image_url}")
    except Exception as e:
        print(f"画像生成中のエラー: {e}")
        image_url = None
    return jsonify({"story": story_part, "task": task_description, "task_type": task_type, "image_url": image_url})

@app.route('/generate-ending', methods=['POST'])
def generate_ending():
    app.logger.info("POST /generate_ending リクエスト受信")
    previous_story = request.json.get('previous_story')
    prompt = (
        "次の条件に従って、以下の情報に基づき、物語の結末を含むJSONオブジェクトを生成してください。\n"
        "【条件】\n"
        "・必ず有効なJSON形式で出力すること。余計な文字や解説は一切出力しないこと。\n"
        "・キー 'ending' に、生成された結末の文章を入れること。\n\n"
        f"前のストーリー：{previous_story}\n"
        "結末はできるだけ短い文章で生成してください。（2文以内推奨）"
    )
    ending_text = None
    attempt = 0
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000
    )
    ending_text = response.choices[0].message.content.strip()
    print(f"試行 {attempt + 1} 回目, 生成された結末: {ending_text}")
    attempt += 1

    
    if ending_text.startswith("{"):
        try:
            parsed_ending = json.loads(ending_text)
            if "ending" in parsed_ending:
                ending_text = parsed_ending["ending"]
        except Exception as e:
            print("JSON解析エラー（結末）:", e)
    ending_text_en = translate_ja_to_en(ending_text)
    image_prompt = f"generate a cute, dreamly,fairy tale styled, Picture book style painting with strong connection of the following story, should not including any word or sentence\n\n{ending_text_en}"
    try:
        image_response = client.images.generate(
            prompt=image_prompt,
            size="256x256",
            n=1
        )
        image_url = image_response.data[0].url
        print(f"生成された画像のURL: {image_url}")
        app.logger.info("生成された結末: %s", ending_text[:20000])

    except Exception as e:
        print(f"画像生成中のエラー: {e}")
        image_url = None
    return jsonify({"ending": ending_text, "image_url": image_url})

if __name__ == '__main__':
    app.run(debug=True)
