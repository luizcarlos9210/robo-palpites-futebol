import os
import requests
import json
from datetime import datetime
import urllib.parse

# ====================== CONFIGURAÇÕES ======================
API_KEY = os.environ.get("API_KEY", "ccd774d8bf2a4d7188fafc7a9de0ee3c")
WHATSAPP_NUMBERS = os.environ.get("WHATSAPP_NUMBERS", "").split(",")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

LIGAS = {
    "Premier League": "39",
    "La Liga": "140",
    "Eredivisie": "88",
    "Primeira Liga": "94"
}

TIMES_FILTRAR = ["PSV", "Ajax", "AZ Alkmaar", "Sporting CP", "Benfica"]

# ====================== FUNÇÕES ======================
def buscar_jogos(data_str):
    todos = []
    for nome_liga, lid in LIGAS.items():
        params = {"league": lid, "season": "2026", "date": data_str}
        try:
            r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params=params, timeout=30)
            if r.status_code != 200:
                continue
            dados = r.json()
            for p in dados.get("response", []):
                casa = p["teams"]["home"]["name"]
                fora = p["teams"]["away"]["name"]
                inclui = any(t in casa or t in fora for t in TIMES_FILTRAR) or nome_liga in ["Premier League", "La Liga"]
                if inclui:
                    todos.append({
                        "liga": nome_liga,
                        "casa": casa,
                        "fora": fora,
                        "data": p["fixture"]["date"].split("T")[0],
                        "hora": p["fixture"]["date"].split("T")[1][:5],
                        "estadio": p["fixture"]["venue"].get("name", "A definir"),
                        "id_casa": p["teams"]["home"]["id"],
                        "id_fora": p["teams"]["away"]["id"]
                    })
        except Exception as e:
            print(f"Erro {nome_liga}: {e}")
    return todos

def buscar_ultimos(time_id, lim=5):
    try:
        r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"team": time_id, "last": lim}, timeout=30)
        if r.status_code != 200:
            return []
        res = []
        for p in r.json().get("response", []):
            eh_casa = p["teams"]["home"]["id"] == time_id
            gf = p["score"]["fulltime"]["home"] or 0
            ga = p["score"]["fulltime"]["away"] or 0
            res.append({"f": gf if eh_casa else ga, "c": ga if eh_casa else gf})
        return res
    except:
        return []

def calcular(jogo):
    c = buscar_ultimos(jogo["id_casa"])
    f = buscar_ultimos(jogo["id_fora"])
    if not c or not f:
        return {"pc":33.33,"pe":33.34,"pf":33.33,"p":"🤝 Dados insuficientes"}
    
    mgc = sum(x["f"] for x in c)/len(c)
    mgf = sum(x["f"] for x in f)/len(f)
    msc = sum(x["c"] for x in c)/len(c)
    msf = sum(x["c"] for x in f)/len(f)
    tc = sum(1 for x in c if x["f"]>x["c"])/len(c)*100
    tf = sum(1 for x in f if x["f"]>x["c"])/len(f)*100
    
    pc = round(tc*0.5 + (mgc/max(msf,0.3))*12, 2)
    pf = round(tf*0.5 + (mgf/max(msc,0.3))*12, 2)
    pe = round(100 - pc - pf, 2)
    t = pc+pf+pe
    pc, pf, pe = round(pc/t*100,2), round(pf/t*100,2), round(100-round(pc/t*100,2)-round(pf/t*100,2),2)
    
    if pc > pf and pc > pe:
        pal = f"✅ VITÓRIA — {jogo['casa']}"
    elif pf > pc and pf > pe:
        pal = f"✅ VITÓRIA — {jogo['fora']}"
    else:
        pal = "🤝 POSSÍVEL EMPATE"
    return {"pc":pc,"pe":pe,"pf":pf,"p":pal,"mgc":round(mgc,2),"mgf":round(mgf,2)}

def gerar_mensagem(j, d):
    return f"""⚽ PALPITE — {j['liga']}
📅 {j['data']} às {j['hora']}
🏟️ {j['estadio']}

{j['casa']} 🆚 {j['fora']}

📊 PROBABILIDADES:
🏠 {j['casa']}: {d['pc']}%
✈️ {j['fora']}: {d['pf']}%
🤝 Empate: {d['pe']}%

🎯 PALPITE: {d['p']}

⚠️ Dados: API-Football | Sem garantia de resultado
🤖 Robô GitHub Actions
"""

def enviar_whatsapp_msg(msg, numero):
    link = f"https://api.whatsapp.com/send?phone={numero.replace('+','')}&text={urllib.parse.quote(msg)}"
    print(f"📱 Para {numero}: {link}")
    return link

# ====================== EXECUÇÃO ======================
hoje = datetime.now().strftime("%Y-%m-%d")
print(f"🔍 Buscando jogos — {hoje}\n")
jogos = buscar_jogos(hoje)

if not jogos:
    print("Nenhum jogo encontrado hoje.")
else:
    print(f"⚽ {len(jogos)} jogos encontrados!\n")
    for idx, j in enumerate(jogos, 1):
        d = calcular(j)
        msg = gerar_mensagem(j, d)
        print(f"--- JOGO {idx} ---")
        print(msg)
        for num in WHATSAPP_NUMBERS:
            if num.strip():
                enviar_whatsapp_msg(msg, num.strip())
        print()
