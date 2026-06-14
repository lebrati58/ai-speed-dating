#!/usr/bin/env python3
"""
AI Speed Dating Matcher — version finale optimisée
Soirée célibataires francophones · Tel Aviv
50 appels API au lieu de 625 → résultats en 2-3 min
"""

import json, os, sys, time
import anthropic
import gspread
from google.oauth2.service_account import Credentials

# ─── CONFIG ───────────────────────────────────────────────────────────────────
SHEET_ID          = "1EjAt9vvFgWGKdHdZhQ3mZilDKt_ojn27UNld8Xi2Gcg"
CREDENTIALS_FILE  = "credentials.json"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OUTPUT_FILE       = "results.json"
# ──────────────────────────────────────────────────────────────────────────────

def load_profiles():
    """Charge les profils depuis Google Sheets — noms de colonnes flexibles"""
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds  = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    sheet  = client.open_by_key(SHEET_ID).get_worksheet(0)
    rows   = sheet.get_all_records()

    if rows:
        print(f"Colonnes détectées : {list(rows[0].keys())}\n")

    profiles = []
    for i, row in enumerate(rows):
        nom         = (row.get("Quel est votre prénom ?") or row.get("Ton prénom")  or row.get("Prénom")    or row.get("prénom")    or "").strip()
        nom_famille = (row.get("Quel est votre nom ?")    or row.get("Nom")         or row.get("nom")         or "").strip()
        age    = str(row.get("Quel est votre âge ?")  or row.get("Ton âge")    or row.get("Âge")      or row.get("âge")       or "").strip()
        sexe   = (row.get("Quel est votre sexe ?")    or row.get("Tu es")      or row.get("Sexe")     or row.get("sexe")      or "").strip()
        tel    = str(row.get("Ton numero whatsapp")       or row.get("Téléphone") or row.get("téléphone") or "").strip()
        resume = (row.get("Upload du texte de votre IA") or row.get("Ton résumé IA") or row.get("Résumé IA") or row.get("résumé IA") or "").strip()

        if nom and sexe and resume:
            profiles.append({
                "id": i + 1, "nom": nom, "nom_famille": nom_famille, "age": age,
                "sexe": sexe, "telephone": tel, "resume_ia": resume,
            })
    return profiles


def rank_for_person(client, person, candidates):
    """1 appel API : Claude classe tous les candidats pour une personne"""
    candidates_text = "\n\n".join([
        f"[ID:{c['id']}] {c['nom']}, {c['age']} ans :\n{c['resume_ia']}"
        for c in candidates
    ])
    prompt = f"""Tu es un expert en compatibilité romantique.

PROFIL DE {person['nom'].upper()}, {person['age']} ans :
{person['resume_ia']}

Classe ces {len(candidates)} candidats du plus au moins compatible avec {person['nom']}.

Règle importante : la compatibilité religieuse et culturelle est un facteur primordial. Si les profils indiquent des niveaux de pratique ou des valeurs religieuses/culturelles incompatibles (ex: très religieux vs laïque, modes de vie fondamentalement différents), réduis le score de manière significative (-20 à -40 points). À l'inverse, une compatibilité religieuse et culturelle forte doit booster le score.

Réponds UNIQUEMENT en JSON :
{{
  "classement": [
    {{"id": <id>, "score": <0-100>, "raison": "<une phrase courte>"}},
    ...
  ]
}}
Tous les IDs doivent apparaître exactement une fois.

CANDIDATS :
{candidates_text}"""

    response = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    text  = response.content[0].text.strip()
    start = text.find('{')
    end   = text.rfind('}') + 1
    if start == -1 or end == 0:
        raise ValueError("Pas de JSON trouvé")
    return json.loads(text[start:end])["classement"]


def compute_matches(profiles):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    hommes = [p for p in profiles if p["sexe"].lower() in ("homme","h","m","male","masculin","זכר")]
    femmes = [p for p in profiles if p["sexe"].lower() in ("femme","f","female","féminin","feminin","נקבה")]

    print(f"✓ {len(hommes)} hommes | {len(femmes)} femmes")
    print(f"→ {len(hommes) + len(femmes)} appels API (au lieu de {len(hommes)*len(femmes)})\n")

    scores_h, scores_f = {}, {}

    for h in hommes:
        print(f"  Classement pour {h['nom']}...", end=" ", flush=True)
        try:
            for item in rank_for_person(client, h, femmes):
                scores_h[(h["id"], item["id"])] = {"score": item["score"], "raison": item["raison"]}
            print("✓")
        except Exception as e:
            print(f"ERREUR ({e})")
        time.sleep(0.5)

    for f in femmes:
        print(f"  Classement pour {f['nom']}...", end=" ", flush=True)
        try:
            for item in rank_for_person(client, f, hommes):
                scores_f[(f["id"], item["id"])] = {"score": item["score"], "raison": item["raison"]}
            print("✓")
        except Exception as e:
            print(f"ERREUR ({e})")
        time.sleep(0.5)

    all_scores = []
    for h in hommes:
        for f in femmes:
            h_d = scores_h.get((h["id"], f["id"]), {"score": 50, "raison": ""})
            f_d = scores_f.get((f["id"], h["id"]), {"score": 50, "raison": ""})
            score_avg = round((h_d["score"] + f_d["score"]) / 2)
            all_scores.append({
                "profil_a": h, "profil_b": f,
                "score": score_avg,
                "score_h": h_d["score"], "score_f": f_d["score"],
                "raison": h_d["raison"] or f_d["raison"],
                "mutual": h_d["score"] >= 70 and f_d["score"] >= 70,
            })

    all_scores.sort(key=lambda x: x["score"], reverse=True)
    return all_scores


def build_results(all_scores, profiles):
    top3_per_person = {}
    for entry in all_scores:
        for role in ("profil_a", "profil_b"):
            person = entry[role]
            other  = entry["profil_b"] if role == "profil_a" else entry["profil_a"]
            pid    = person["id"]
            if pid not in top3_per_person:
                top3_per_person[pid] = {"personne": person, "top3": []}
            if len(top3_per_person[pid]["top3"]) < 3:
                top3_per_person[pid]["top3"].append({
                    "match": other, "score": entry["score"],
                    "raison": entry["raison"], "mutual": entry["mutual"]
                })

    best_per_person = [
        {
            "personne":       v["personne"],
            "meilleur_match": v["top3"][0]["match"]  if v["top3"] else None,
            "score":          v["top3"][0]["score"]  if v["top3"] else 0,
            "raison":         v["top3"][0]["raison"] if v["top3"] else "",
            "top3":           v["top3"],
        }
        for v in top3_per_person.values()
    ]

    mutual_matches = [e for e in all_scores if e["mutual"]]
    hommes = [p for p in profiles if p["sexe"].lower() in ("homme","h","m","male","masculin","זכר")]
    femmes = [p for p in profiles if p["sexe"].lower() in ("femme","f","female","féminin","feminin","נקבה")]

    return {
        "top_matchs":      all_scores[:20],
        "best_per_person": best_per_person,
        "mutual_matches":  mutual_matches,
        "total_profils":   len(profiles),
        "stats": {
            "hommes": len(hommes), "femmes": len(femmes),
            "mutuals": len(mutual_matches),
        }
    }


def main():
    if not ANTHROPIC_API_KEY:
        print("❌ Lance : export ANTHROPIC_API_KEY=sk-ant-..."); sys.exit(1)

    print("📋 Chargement des profils depuis Google Sheets...")
    profiles = load_profiles()
    print(f"✓ {len(profiles)} profils chargés\n")

    if len(profiles) < 2:
        print("❌ Pas assez de profils (minimum 2).")
        print("   Vérifie que le Sheet est bien partagé avec :")
        print("   dating-reader@direct-beacon-487015-c0.iam.gserviceaccount.com")
        sys.exit(1)

    print("🤖 Calcul des matchs via Claude...\n")
    all_scores = compute_matches(profiles)
    results    = build_results(all_scores, profiles)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ results.json généré !")
    print(f"   → {results['stats']['hommes']}H × {results['stats']['femmes']}F analysés")
    print(f"   → {results['stats']['mutuals']} mutual match(s) 🔥")
    if all_scores:
        top = all_scores[0]
        print(f"   → 🏆 Top : {top['profil_a']['nom']} × {top['profil_b']['nom']} ({top['score']}%)")
    print(f"\n→ Ouvre display.html dans Chrome 🎉")


if __name__ == "__main__":
    main()
