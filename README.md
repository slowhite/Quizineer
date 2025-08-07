# Quizineer: AI Quiz Improvement Tool

This is a GPT-4-powered web app to help K-12 students improve their self-generated multiple-choice questions.

## Features
- Improve: Get detailed feedback on your quiz
- Validate: Score your quiz using educational rubrics
- Enhance: Make your question harder or deeper
- amification layer with storyline & feedback

## Tech Stack
- Flask (Python)
- JavaScript / HTML / CSS
- GPT-4 API (via OpenAI)

## How to Run
1. Add your OpenAI API key to server.py:
#ADD YOUR API KEY THERE
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "sk-xxxxxxxxxxxxxxxxxxxxxxx"))
2. Run the app:
```bash
python server.py
3. Open the app in your browser:
http://127.0.0.1:5000/

※ このコードには実際のAPIキーは含まれていません。動作させるには、ご自身のOpenAIキーを記入してください。
