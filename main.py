from flask import Flask, request, jsonify
import requests, time, random, os
from bs4 import BeautifulSoup
from urllib.parse import urlparse

app = Flask(__name__)

# ---------- AI ----------
def ai_score(text):
    try:
        key = os.getenv("HF_API_KEY")
        if not key:
            return None

        r = requests.post(
            "https://api-inference.huggingface.co/models/facebook/bart-large-mnli",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "inputs": text,
                "parameters": {"candidate_labels": ["fake news","true news"]}
            },
            timeout=5
        )

        data = r.json()
        if isinstance(data, list):
            return int(data[0]["scores"][0] * 100)
    except:
        return None

# ---------- BASE ----------
def base_score(t):
    t = t.lower()
    s = 30
    if "şok" in t: s+=20
    if "iddia" in t: s+=20
    if "gizli" in t: s+=15
    return min(95, s)

def risk_score(text):
    ai = ai_score(text)
    base = base_score(text)
    return int(ai*0.6+base*0.4) if ai else base

# ---------- URL ----------
def extract_url(url):
    try:
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.text,"html.parser")
        return soup.title.string
    except:
        return None

# ---------- MEDIA ----------
def extract_media(url):
    name = urlparse(url).path.split("/")[-1]
    return name.replace("-", " ")

# ---------- FAKE SOCIAL ----------
def social():
    topics = ["deprem","ekonomi","seçim"]
    return [f"{random.choice(topics)} hakkında şok iddia"]*10

# ---------- API ----------
@app.route("/api/analyze", methods=["POST"])
def analyze():
    t = request.json.get("text")

    if t.startswith("http"):
        if any(x in t for x in [".jpg",".png",".mp4"]):
            t = extract_media(t)
        else:
            t = extract_url(t)

    if not t or len(t)<20:
        return {"error":"Geçerli haber gir"}

    r = risk_score(t)
    return {"risk": r}

# ---------- UI ----------
@app.route("/")
def home():
    return """
<html>
<head>
<title>DEFANS</title>
<style>
body{background:#0f172a;color:white;font-family:Arial}
.container{max-width:1100px;margin:auto;padding:20px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
.card{background:#1e293b;padding:20px;border-radius:16px}
.big{grid-column:span 2}
button{background:#22c55e;padding:10px;border:none}
input{padding:10px;width:70%}
</style>
</head>
<body>

<div class="container">
<h1 style="color:#22c55e">DEFANS</h1>

<div class="grid">
<div class="card"><h3>AI Risk</h3><h1 id="r">-</h1></div>
<div class="card"><h3>Kaynak</h3><h1>Sosyal + Web</h1></div>
<div class="card"><h3>Durum</h3><h1>Aktif</h1></div>

<div class="card big">
<input id="txt" placeholder="URL / haber / görsel">
<button onclick="go()">Analiz</button>
<h2 id="res"></h2>
</div>

<div class="card big" id="list"></div>

</div>
</div>

<script>
async function go(){
 let t=document.getElementById("txt").value

 let r=await fetch("/api/analyze",{
  method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({text:t})
 })

 let j=await r.json()
 res.innerText=j.error || "Risk: %"+j.risk
}
</script>

</body>
</html>
"""

# ---------- RUN ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)