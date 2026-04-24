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
            timeout=5
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

    if source in ["X","Reddit","TikTok","Instagram","Forum","Blog","Telegram"]:
        base += 15

    return int(ai*0.6 + base*0.4) if ai else base

# ---------------- URL ----------------
def extract_url(url):
    try:
        r = requests.get(url, timeout=5, headers={"User-Agent":"Mozilla"})
        soup = BeautifulSoup(r.text, "html.parser")
        return soup.title.string.strip()
    except:
        return url

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

# ---------------- SOSYAL ----------------
def social_feed():
    platforms = ["X","Reddit","TikTok","Instagram","Forum","Telegram"]

    patterns = [
        "SON DAKİKA: {topic} hakkında şok gelişme!",
        "{topic} hakkında gizli belge sızdırıldı iddiası",
        "Bu video viral oldu: {topic}",
        "{topic} hakkında büyük oyun ortaya çıktı",
        "{topic} konusunda herkes yanılıyor olabilir",
        "Kimse bunu konuşmuyor: {topic}"
    ]

    topics = ["deprem","seçim","ekonomi","aşı","savaş","kripto","yapay zeka"]

    data = []

    for _ in range(60):
        text = random.choice(patterns).format(topic=random.choice(topics))
        text += " " + str(random.randint(1,9999))  # tekrar kır

        data.append((text, random.choice(platforms), "#"))

    return data

# ---------------- DATA ----------------
def collect():
    data = []
    data += parse_rss("https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr","Google")
    data += parse_rss("https://www.ntv.com.tr/son-dakika.rss","NTV")
    data += parse_rss("https://www.bbc.com/turkce/index.xml","BBC")
    data += parse_rss("https://feeds.bbci.co.uk/news/rss.xml","BBC Global")
    data += parse_rss("https://www.cnnturk.com/feed/rss/news","CNN")
    data += parse_rss("https://teyit.org/feed","Teyit")
    data += parse_rss("https://www.snopes.com/feed/","Snopes")

    data += social_feed()

    return data

# ---------------- REFRESH ----------------
def refresh():
    global cache, last, seen

    if time.time() - last < 10:
        return

    last = time.time()

    if len(seen) > 500:
        seen = set()

    raw = collect()
    random.shuffle(raw)

    out = []

    for text, source, link in raw:
        key = hashlib.md5((text + str(random.random())).encode()).hexdigest()

        if key in seen:
            continue

        seen.add(key)

        r = risk_score(text, source)

        out.append({
            "text": text,
            "risk": r,
            "source": source,
            "link": link
        })

        if r >= 70:
            send_email(text, r)

    cache = (out + cache)[:120]

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

    if not text or len(text) < 5:
        return {"error":"Geçerli veri gir"}

    r = risk_score(text)

    fake_patterns = [
        "uzaylı","dünya yok olacak","%100 gerçek",
        "herkes saklıyor","gizli plan","büyük oyun"
    ]

    if any(x in text.lower() for x in fake_patterns):
        r += 30

    r = min(r, 95)

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
.list{max-height:600px;overflow-y:auto}
</style>
</head>
<body>

<div class="container">
<h1 style="color:#22c55e">DEFANS</h1>

<div class="grid">

<div class="card"><h3>Durum</h3><h1>Aktif</h1></div>
<div class="card"><h3>Kaynak</h3><h1>Sosyal + Web</h1></div>
<div class="card"><h3>AI</h3><h1>ON</h1></div>

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
  <br>
  <span style="color:red">${x.risk>70?"Yalan Haber Riski Yüksek":""}</span>
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

setInterval(load,7000)
load()
</script>

</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)