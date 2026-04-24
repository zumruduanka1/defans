from flask import Flask, request, jsonify
import requests, time, random, os, smtplib, hashlib
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

app = Flask(__name__)

cache = []
seen = set()
last = 0

# ---------------- EMAIL ----------------
def send_email(text, risk):
    try:
        user = os.getenv("tubitaktest0@gmail.com")
        pw = os.getenv("umdyxtmpeljhodhy")
        to = os.getenv("rumeyysauslu@gmail.com")

        if not user or not pw or not to:
            return

        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls()
        s.login(user, pw)

        msg = f"Subject: DEFANS ALERT\n\n{text}\nRisk: %{risk}"
        s.sendmail(user, to, msg)
        s.quit()
    except:
        pass

# ---------------- AI ----------------
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
            timeout=6
        )

        data = r.json()
        if isinstance(data, list):
            return int(data[0]["scores"][0] * 100)
    except:
        return None

# ---------------- RISK ----------------
def base_score(text):
    t = text.lower()
    s = 30

    if "şok" in t or "ifşa" in t: s += 25
    if "iddia" in t: s += 20
    if "gizli" in t: s += 15
    if "kanıtlandı" in t: s += 15
    if "sızdırıldı" in t: s += 10
    if "uzman" in t or "rapor" in t: s -= 15

    return max(5, min(95, s))

def risk_score(text, source=None):
    ai = ai_score(text)
    base = base_score(text)

    # sosyal medya boost
    if source in ["X","Reddit","TikTok","Instagram","Forum","Blog"]:
        base += 15

    return int(ai*0.6 + base*0.4) if ai else base

# ---------------- FILTER ----------------
def is_news(text):
    if not text:
        return False
    t = text.lower()
    keywords = ["haber","iddia","son dakika","gündem","şok","ifşa"]
    return len(t) > 30 and any(k in t for k in keywords)

# ---------------- URL ----------------
def extract_url(url):
    try:
        r = requests.get(url, timeout=5, headers={"User-Agent":"Mozilla"})
        soup = BeautifulSoup(r.text, "html.parser")
        return soup.title.string.strip()
    except:
        return None

# ---------------- MEDIA ----------------
def extract_media(url):
    name = urlparse(url).path.split("/")[-1]
    return name.replace("-", " ").replace("_", " ")

# ---------------- RSS ----------------
def parse_rss(url, source):
    data = []
    try:
        r = requests.get(url, timeout=5)
        root = ET.fromstring(r.content)

        for i in root.findall(".//item")[:10]:
            title = i.find("title").text
            link = i.find("link").text
            data.append((title, source, link))
    except:
        pass
    return data

# ---------------- SOSYAL GERÇEKÇİ ----------------
def social_realistic_feed():
    platforms = ["X","Reddit","TikTok","Instagram","Forum","Blog","Telegram"]

    patterns = [
        "SON DAKİKA: {topic} hakkında şok gelişme!",
        "{topic} hakkında gizli belge sızdırıldı iddiası",
        "Bu video hızla yayılıyor: {topic}",
        "{topic} hakkında gerçekler saklanıyor mu?",
        "{topic} konusunda büyük oyun ortaya çıktı",
        "Kimse bunu konuşmuyor: {topic}",
        "{topic} hakkında kanıtlandığı iddia edilen bilgi"
    ]

    topics = ["deprem","seçim","ekonomi","aşı","savaş","yapay zeka","kripto","gıda krizi"]

    data = []
    for _ in range(40):
        topic = random.choice(topics)
        text = random.choice(patterns).format(topic=topic)

        data.append((text, random.choice(platforms), "#"))

    return data

# ---------------- DATA ----------------
def collect():
    data = []
    data += parse_rss("https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr","Google")
    data += parse_rss("https://www.ntv.com.tr/son-dakika.rss","NTV")
    data += parse_rss("https://www.bbc.com/turkce/index.xml","BBC")
    data += parse_rss("https://www.trthaber.com/manset_articles.rss","TRT")
    data += parse_rss("https://www.hurriyet.com.tr/rss/gundem","Hürriyet")
    data += parse_rss("https://teyit.org/feed","Teyit")
    data += parse_rss("https://www.snopes.com/feed/","Snopes")

    data += social_realistic_feed()

    return data

# ---------------- REFRESH ----------------
def refresh():
    global cache, last

    if time.time() - last < 20:
        return

    last = time.time()
    raw = collect()

    out = []

    for text, source, link in raw:
        key = hashlib.md5(text.encode()).hexdigest()
        if key in seen:
            continue

        seen.add(key)

        if not is_news(text):
            continue

        r = risk_score(text, source)

        if r >= 50:
            out.append({
                "text": text,
                "risk": r,
                "source": source,
                "link": link
            })

        if r >= 70:
            send_email(text, r)

    cache = out[:40]

# ---------------- API ----------------
@app.route("/api/news")
def news():
    refresh()
    return {"data": cache}

@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    text = data.get("text")

    if text.startswith("http"):
        if any(x in text for x in [".jpg",".png",".jpeg",".mp4",".webm"]):
            text = extract_media(text)
        else:
            text = extract_url(text)

    if not text or not is_news(text):
        return {"error":"Geçerli haber gir"}

    r = risk_score(text)

    if r >= 70:
        send_email(text, r)

    return {"risk": r}

# ---------------- UI ----------------
@app.route("/")
def home():
    return """
<html>
<head>
<title>DEFANS</title>
<style>
body{background:#0f172a;color:white;font-family:Arial}
.container{max-width:1200px;margin:auto;padding:20px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
.card{background:#1e293b;padding:20px;border-radius:16px}
.big{grid-column:span 3}
button{background:#22c55e;padding:10px;border:none}
input{padding:10px;width:70%}
.list{max-height:400px;overflow:auto}
</style>
</head>
<body>

<div class="container">
<h1 style="color:#22c55e">DEFANS</h1>

<div class="grid">

<div class="card">
<h3>Durum</h3>
<h1>Aktif</h1>
</div>

<div class="card">
<h3>Kaynak</h3>
<h1>Sosyal + Web</h1>
</div>

<div class="card">
<h3>AI</h3>
<h1>ON</h1>
</div>

<div class="card big">
<input id="txt" placeholder="URL / haber / görsel / video">
<button onclick="go()">Analiz</button>
<h2 id="res"></h2>
</div>

<div class="card big list" id="list"></div>

</div>
</div>

<script>
async function load(){
 let r=await fetch("/api/news")
 let j=await r.json()

 let html=""
 j.data.forEach(x=>{
  html+=`<div style='padding:10px;border-bottom:1px solid #333'>
  <a href='${x.link}' target='_blank'>${x.text}</a>
  <br>
  <span style="color:#22c55e">Risk: %${x.risk}</span> |
  <span style="color:#aaa">${x.source}</span>
  </div>`
 })

 document.getElementById("list").innerHTML=html
}

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

setInterval(load,20000)
load()
</script>

</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)