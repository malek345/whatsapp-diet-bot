import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

user_sessions = {}

# المفاتيح الجديدة من البيئة
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
MAKE_WEBHOOK_URL = os.environ.get("MAKE_WEBHOOK_URL")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

def ask_ai(system_prompt, user_message):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-versatile",  # نموذج قوي وسريع جداً ومجاني
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": 300
    }
    try:
        response = requests.post(GROQ_URL, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error calling AI: {e}")
    return "عذراً يا فندم، واجهت مشكلة صغيرة. ممكن تبعت رسالتك تاني؟"

@app.route("/webhook", methods=["POST"])
def webhook():
    from_number = request.values.get("From")
    user_msg = request.values.get("Body", "").strip()
    
    resp = MessagingResponse()
    
    if from_number not in user_sessions:
        user_sessions[from_number] = {"step": "welcome"}
        welcome_prompt = "أنت مساعد عيادة تغذية ذكي تتحدث بالعامية المصرية الفخمة والودية جداً. رحب بالعميل واطلب منه بكل ذوق يعرفنا باسمه الكريم للبدء."
        reply = ask_ai(welcome_prompt, user_msg)
        user_sessions[from_number]["step"] = "get_name"
        resp.message(reply)
        return str(resp)
        
    state = user_sessions[from_number]
    step = state.get("step")
    
    if step == "get_name":
        state["name"] = user_msg
        state["step"] = "get_age"
        reply = ask_ai("العميل كتب اسمه. اطلب منه السن بالعامية المصرية وبطريقة لبقة.", user_msg)
        
    elif step == "get_age":
        state["age"] = user_msg
        state["step"] = "get_height"
        reply = ask_ai("العميل كتب سنه. اطلب منه الطول بالسنتيمتر بالعامية المصرية.", user_msg)
        
    elif step == "get_height":
        state["height"] = user_msg
        state["step"] = "get_weight"
        reply = ask_ai("العميل كتب طوله. اطلب منه الوزن الحالي بالكيلوجرام بالعامية المصرية.", user_msg)
        
    elif step == "get_weight":
        state["weight"] = user_msg
        state["step"] = "get_goal"
        reply = ask_ai("العميل كتب وزنه. اسأله عن هدفه (تخسيس، زيادة عضلات، تثبيت وزن) بالعامية المصرية.", user_msg)
        
    elif step == "get_goal":
        state["goal"] = user_msg
        state["step"] = "get_health"
        reply = ask_ai("العميل كتب هدفه. اسأله لو بيعاني من أي مشاكل صحية أو أمراض مزمنة أو إصابات (واكتب له إنه لو مفيش يكتب 'لا يوجد') بالعامية المصرية.", user_msg)
        
    elif step == "get_health":
        state["health"] = user_msg
        state["step"] = "get_inbody"
        reply = ask_ai("العميل كتب حالته الصحية. اسأله: لو عمل تحليل InBody قريب يكتب نسبة الدهون ونسبة العضلات، ولو مش عارفهم يكتب كلمة 'تخطي'.", user_msg)
        
    elif step == "get_inbody":
        if "تخطي" in user_msg or "لا" in user_msg:
            state["fat"] = "غير معروف"
            state["muscle"] = "غير معروف"
        else:
            state["fat"] = user_msg
            state["muscle"] = "مدمجة"
            
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
            
        reply = ask_ai("العميل أكمل كافة البيانات وتم حفظها في النظام بنجاح. صغ له رسالة ختامية فخمة ومبهجة بالعامية المصرية تخبره أن بياناته أصبحت عند الدكتور وجاري تجهيز ملفه.", "")
        del user_sessions[from_number]
        
    resp.message(reply)
    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
