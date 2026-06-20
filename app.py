import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# تخزين مؤقت لحالة المستخدمين في الذاكرة (Memory Session)
user_sessions = {}

# قراءة المتغيرات من بيئة التشغيل (Render)
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
MAKE_WEBHOOK_URL = os.environ.get("MAKE_WEBHOOK_URL")

CLAUDE_URL = "https://api.anthropic.com/v1/messages"

def ask_claude(system_prompt, user_message):
    """دالة للتحدث مع Claude API بالعامية المصرية وبثبات"""
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    data = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 300,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}]
    }
    try:
        response = requests.post(CLAUDE_URL, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()['content'][0]['text']
    except Exception as e:
        print(f"Error calling Claude: {e}")
    return "عذراً يا فندم، واجهت مشكلة صغيرة. ممكن تبعت رسالتك تاني؟"

@app.route("/webhook", methods=["POST"])
def webhook():
    from_number = request.values.get("From")
    user_msg = request.values.get("Body", "").strip()
    
    resp = MessagingResponse()
    
    # لو المستخدم جديد، نبدأ معاه المحادثة والأسئلة
    if from_number not in user_sessions:
        user_sessions[from_number] = {"step": "welcome"}
        welcome_prompt = "أنت مساعد عيادة تغذية ذكي تتحدث بالعامية المصرية الفخمة والودية جداً. رحب بالعميل واطلب منه بكل ذوق يعرفنا باسمه الكريم للبدء."
        reply = ask_claude(welcome_prompt, user_msg)
        user_sessions[from_number]["step"] = "get_name"
        resp.message(reply)
        return str(resp)
        
    state = user_sessions[from_number]
    step = state.get("step")
    
    # مرحلة تجميع البيانات خطوة بخطوة
    if step == "get_name":
        state["name"] = user_msg
        state["step"] = "get_age"
        reply = ask_claude("العميل كتب اسمه. اطلب منه السن بالعامية المصرية وبطريقة لبقة.", user_msg)
        
    elif step == "get_age":
        state["age"] = user_msg
        state["step"] = "get_height"
        reply = ask_claude("العميل كتب سنه. اطلب منه الطول بالسنتيمتر بالعامية المصرية.", user_msg)
        
    elif step == "get_height":
        state["height"] = user_msg
        state["step"] = "get_weight"
        reply = ask_claude("العميل كتب طوله. اطلب منه الوزن الحالي بالكيلوجرام بالعامية المصرية.", user_msg)
        
    elif step == "get_weight":
        state["weight"] = user_msg
        state["step"] = "get_goal"
        reply = ask_claude("العميل كتب وزنه. اسأله عن هدفه (تخسيس، زيادة عضلات، تثبيت وزن) بالعامية المصرية.", user_msg)
        
    elif step == "get_goal":
        state["goal"] = user_msg
        state["step"] = "get_health"
        reply = ask_claude("العميل كتب هدفه. اسأله لو بيعاني من أي مشاكل صحية أو أمراض مزمنة أو إصابات (واكتب له إنه لو مفيش يكتب 'لا يوجد') بالعامية المصرية.", user_msg)
        
    elif step == "get_health":
        state["health"] = user_msg
        state["step"] = "get_inbody"
        reply = ask_claude("العميل كتب حالته الصحية. اسأله 'السؤال الاختياري الصايع' بالعامية المصرية: لو عمل تحليل InBody قريب يكتب نسبة الدهون ونسبة العضلات، ولو مش عارفهم يكتب كلمة 'تخطي'.", user_msg)
        
    elif step == "get_inbody":
        # معالجة الـ InBody الفخم والاختياري
        if "تخطي" in user_msg or "لا" in user_msg:
            state["fat"] = "غير معروف"
            state["muscle"] = "غير معروف"
        else:
            state["fat"] = user_msg
            state["muscle"] = "مدمجة مع الدهون"
            
        # إرسال البيانات فوراً لـ Make.com ليرميها في الـ Google Sheet
        payload = {
            "name": state.get("name"),
            "age": state.get("age"),
            "height": state.get("height"),
            "weight": state.get("weight"),
            "goal": state.get("goal"),
            "health": state.get("health"),
            "fat": state.get("fat"),
            "muscle": state.get("muscle")
        }
        
        try:
            requests.post(MAKE_WEBHOOK_URL, json=payload)
        except Exception as e:
            print(f"Error sending to Make Webhook: {e}")
            
        # إنهاء الجلسة وإرسال التلخيص الفخم
        reply = ask_claude("العميل أكمل كافة البيانات وتم حفظها في النظام بنجاح. صغ له رسالة ختامية فخمة ومبهجة بالعامية المصرية تخبره أن بياناته أصبحت عند الدكتور وجاري تجهيز ملفه.", "")
        del user_sessions[from_number] # مسح الجلسة لتبدأ من جديد المرة القادمة
        
    resp.message(reply)
    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
