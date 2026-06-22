📘 ComplyKE 🇰🇪

AI-assisted compliance guidance system for Kenyan SMEs delivered via USSD & SMS — designed for feature phones and low-connectivity environments.

Built for the Africa’s Talking Women in Tech Hackathon 2026.

📌 Problem Statement

Most small businesses in Kenya operate without access to legal or compliance expertise. As a result, many only become aware of regulatory obligations after receiving fines or penalties.

ComplyKE addresses this gap by providing instant, simplified compliance guidance through USSD and SMS, requiring no smartphone or internet access.

💡 Solution

ComplyKE allows SMEs to:

Dial a USSD code
Answer a few simple business-related questions
Receive instant SMS guidance on:
Compliance obligations
Risk level (Low / Medium / High)
Recommended actions

All accessible on 2G networks and feature phones.

⚙️ System Flow
USSD Input
   ↓
Business Profiling (type, size, data usage)
   ↓
Rules-Based Compliance Engine
   ↓
Risk Scoring Engine
   ↓
Response Formatter
   ↓
SMS Delivery (Africa’s Talking API)
🧪 USSD Flow (MVP)
User dials *384*GRC#

→ Select Language (English / Swahili)
→ Select Business Type
→ Number of Employees
→ Data Collection (Yes / No)

→ SMS Response Generated
🏢 Supported Business Types (MVP Scope)
Online Shop / E-Commerce
Freelancer / Self-Employed
Retail Store
Food Vendor
Mobile Money Agent

⚠️ MVP scope — designed for hackathon demonstration. Expandable to more industries.

🧠 Key Features
USSD-based interaction (no internet required)
SMS-based compliance guidance
Rule-based compliance engine (deterministic logic)
Risk scoring system (Low / Medium / High)
Optional AI layer for explanation simplification

AI is used only for formatting explanations, not for compliance decisions.

🛠️ Tech Stack
Layer	Technology
Backend	Python + Flask
USSD & SMS	Africa’s Talking API
Compliance Engine	JSON-based rules system
AI Layer (optional)	Claude API
🚀 Quick Start
git clone https://github.com/Toritish/ComplyKE.git
cd ComplyKE
pip install -r requirements.txt
cp .env.example .env
python app.py
🔐 Environment Variables
AT_USERNAME=sandbox
AT_API_KEY=your_africastalking_api_key
CLAUDE_API_KEY=your_claude_api_key   # optional
🧪 Testing (No API Mode)
curl -X POST http://localhost:5000/ussd \
  -d "sessionId=test1" \
  -d "phoneNumber=+254700000001" \
  -d "networkCode=63902" \
  -d "serviceCode=*384*1#" \
  -d "text=1*1*1*1*2*2"
📜 License

MIT © 2026 ComplyKE
