from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.generativeai import GenerativeModel, configure
import traceback

# Load environment variables
load_dotenv()

# Debug: Show if key is loaded (remove quotes in .env if you see quotes here!)
print("🔑 API KEY preview:", os.getenv("GEMINI_API_KEY")[:10] + "..." if os.getenv("GEMINI_API_KEY") else "MISSING")

# Configure Gemini API
configure(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)
model = GenerativeModel("gemini-2.0-flash")
print("✅ Using model:", model.model_name)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get("message", "").strip()
        tone = data.get("tone", "auto")  # 'auto', 'formal', or 'informal'

        if not user_message:
            return jsonify({"error": "Message cannot be empty"}), 400

        # === NEW: MULTILINGUAL PROMPT ===
        if tone == "formal":
            system_prompt = """
You are Prolet, a professional letter-writing assistant.

Respond in the **same language** as the user's request.

Write a complete formal business letter using this exact structure:

[Your Full Name]
[Your Address]
[City, State ZIP Code]

[Date]

[Recipient Full Name]
[Recipient Title]
[Company/Organization Name]
[Recipient Address]

Dear [Mr./Ms./Mx. Last Name],

[Professional, respectful tone. Clear purpose. 2–3 short paragraphs.]

Respectfully yours,

[Your Full Name]
[Your Title (optional)]

Use realistic example names/addresses. Never use placeholders.
"""
        elif tone == "informal":
            system_prompt = """
You are Prolet, a friendly letter-writing assistant.

Respond in the **same language** as the user's request.

Write a complete informal letter using this structure:

Hi [First Name],

[Start with a warm opener, e.g., "Hope you're doing well!"]

[Body: Warm, conversational tone. Use contractions ("I'm", "you're"). Be kind and personal.]

Thanks so much,  
[Your First Name]

Use realistic names. Never use placeholders like [Name].
"""
        else:  # auto
            system_prompt = """
You are Prolet, a letter-writing assistant.

Respond in the **same language** as the user's request.

Automatically decide if the letter should be formal or informal based on the request.

- For job, business, official matters → use FORMAL structure.
- For friends, family, casual notes → use INFORMAL structure.

FORMAL structure:
[Your Full Name]
[Your Address]
[City, State ZIP Code]

[Date]

[Recipient Full Name]
[Recipient Title]
[Company/Organization Name]
[Recipient Address]

Dear [Mr./Ms./Mx. Last Name],

[Professional tone. 2–3 paragraphs.]

Respectfully yours,

[Your Full Name]

INFORMAL structure:
Hi [First Name],

[Warm opener]

[Conversational body]

Thanks so much,  
[Your First Name]

Use realistic names/addresses. Never use placeholders.
"""

        prompt = system_prompt.strip() + f"\n\nUser request: \"{user_message}\"\n\nDraft the letter below:"

        response = model.generate_content(prompt)
        reply = response.text.strip()

        return jsonify({"reply": reply})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Sorry, I'm having trouble right now."}), 500

@app.route('/api/send-email', methods=['POST'])
def send_email():
    try:
        data = request.json
        letter = data.get("letter", "").strip()
        recipient = data.get("to", "").strip()

        if not letter or not recipient:
            return jsonify({"error": "Letter and recipient email are required"}), 400

        sender_email = os.getenv("MAIL_USERNAME")
        sender_password = os.getenv("MAIL_APP_PASSWORD")

        if not sender_email or not sender_password:
            return jsonify({"error": "Email not configured. Check .env file."}), 500

        # Validate email format
        import re
        if not re.match(r"[^@]+@[^@]+\.[^@]+", recipient):
            return jsonify({"error": "Invalid email address"}), 400

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Subject'] = "Your Prolet Letter"
        msg.attach(MIMEText(letter, 'plain'))

        print(f"📧 Sending email to: {recipient}")
        print(f"📧 From: {sender_email}")

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)

        return jsonify({"success": "Email sent successfully!"})

    except Exception as e:
        # ✅ LOG THE EXACT ERROR
        print("❌ Email error:", str(e))
        return jsonify({"error": f"Email failed: {str(e)}"}), 500
@app.route('/api/analyze-letter', methods=['POST'])
def analyze_letter():
    try:
        data = request.json
        letter = data.get("letter", "").strip()

        if not letter:
            return jsonify({"error": "Please provide a letter to analyze."}), 400

        # ✅ IMPROVED PROMPT — More specific and force structured output
        prompt = f"""
You are Prolet, a professional letter-editing AI assistant.

Analyze the following letter and provide 3–5 actionable suggestions to improve:
- Tone (make it more formal/casual as needed)
- Clarity (remove ambiguity, improve flow)
- Professionalism (fix grammar, word choice, structure)

Letter:
{letter}

Respond ONLY with bullet points. Do NOT add any other text.

Example:
- Use “Dear [Manager’s Name]” instead of “Hi” for a formal tone.
- Break long sentences into shorter ones for clarity.
- Replace “I’m writing to say I quit” with “I am writing to formally resign...”

Suggestions:
"""

        response = model.generate_content(prompt)
        reply = response.text.strip()

        # ✅ Fallback if Gemini returns empty or generic
        if not reply or "Suggestions:" in reply or len(reply) < 10:
            reply = """
- The letter is well-written but could be more formal. Consider using “Dear [Name]” instead of “Hi”.
- Add a closing line like “Sincerely,” for professionalism.
- Shorten long paragraphs for better readability.
"""

        return jsonify({"reply": reply})

    except Exception as e:
        print("🔤 Error in analyze-letter:", str(e))
        return jsonify({"error": "Failed to analyze letter. Please try again."}), 500
   
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)