#!/usr/bin/env python3
"""
AI Speed Dating Matcher — version optimisée
50 appels API au lieu de 625 → résultats en 2-3 min au lieu de 20+
"""

import json
import os
import sys
import time
import anthropic
import gspread
from google.oauth2.service_account import Credentials

# ─── CONFIG ───────────────────────────────────────────────────────────────────
SHEET_ID         = "REMPLACE_PAR_TON_SHEET_ID"
SHEET_TAB        = "Réponses au formulaire 1"
CREDENTIALS_FILE = "credentials.json"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OUTPUT_FILE      = "results.json"
# ──────────────────────────────────────────────────────────────────────────────

def load_profiles_from_sheet():
    """Charge les profils depuis Google Sheets"""
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds  = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    sheet  = client.open_by_key(SHEET_ID).worksheet(SHEET_TAB)
    rows   = sheet.get_all_records()

    profiles = []
    for i, row in enumerate(rows):
        profiles.append({
            "id":        i + 1,
            "nom":       row.get("Prénom", "").strip(),
            "age":       str(row.get("Âge", "")).strip(),
            "sexe":      row.get("Sexe", "").strip(),
            "telephone": row.get("Téléphone", "").strip(),
            "resume_ia": row.get("Résumé IA", "").strip(),
        })
    return profiles


def rank_for_person(client, person, candidates):
    """
    1 seul appel API : Claude classe TOUS les candidats pour une personne.
    Retourne une liste [{id, score, raison}, ...]
    """
    candidates_text = "\n\n".join([
        f"[ID:{c['id']}] {c['nom']}, {c['age']} ans :\n{c['resume_ia']}"
        for c in candidates
    ])

    prompt = f"""Tu es un expert en compatibilité romantique.

PROFIL DE {person['nom'].upper()}, {person['age']} ans :
{person['resume_ia']}

Voici {len(candidates)} candidats potentiels. Classe-les du plus au moins compatible avec {person['nom']}.

Réponds UNIQUEMENT en JSON valide, ce format exact :
{{
  "classement": [
    {{"id": <id_candidat>, "score": <entier 0-100>, "raison": "<une phrase courte>"}},
    ...
  ]
}}

Règles :
- Tous les IDs doivent apparaître exactement une fois
- Score 80-100 = très compatible, 50-79 = compatible, 0-49 = peu compatible
- La raison doit être spécifique aux deux profils

CANDIDATS :
{candidates_text}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.content[0].text.strip()
    start = text.find('{')
    end   = text.rfind('}') + 1
    if start == -1 or end == 0:
        raise ValueError("Pas de JSON trouvé")
    data = json.loads(text[start:end])
    return data["classement"]


def compute_matches(profiles):
    """
    Calcule tous les scores homme/femme.
    VERSION OPTIMISÉE : 1 appel par personne (50 appels) au lieu de 1 par paire (625 appels).
    Score final = moyenne du score lui→elle et elle→lui.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    hommes = [p for p in profiles if p["sexe"].lower() in ("homme", "h", "m", "male")]
    femmes = [p for p in profiles if p["sexe"].lower() in ("femme", "f", "female")]

    print(f"✓ {len(hommes)} hommes | {len(femmes)} femmes")
    print(f"→ {len(hommes) + len(femmes)} appels API (au lieu de {len(hommes) * len(femmes)})\n")

    # Scores hommes → femmes
    scores_h = {}  # {(homme_id, femme_id): {"score": x, "raison": y}}
    for h in hommes:
        print(f"  Classement pour {h['nom']}...", end=" ", flush=True)
        try:
            classement = rank_for_person(client, h, femmes)
            for item in classement:
                scores_h[(h["id"], item["id"])] = {
                    "score":  item["score"],
                    "raison": item["raison"],
                }
            print("✓")
        except Exception as e:
            print(f"ERREUR ({e})")
        time.sleep(0.5)

    # Scores femmes → hommes
    scores_f = {}  # {(femme_id, homme_id): {"score": x, "raison": y}}
    for f in femmes:
        print(f"  Classement pour {f['nom']}...", end=" ", flush=True)
        try:
            classement = rank_for_person(client, f, hommes)
            for item in classement:
                scores_f[(f["id"], item["id"])] = {
                    "score":  item["score"],
                    "raison": item["raison"],
                }
            print("✓")
        except Exception as e:
            print(f"ERREUR ({e})")
        time.sleep(0.5)

    # Combiner : score final = moyenne des deux directions
    all_scores = []
    for h in hommes:
        for f in femmes:
            h_data = scores_h.get((h["id"], f["id"]), {"score": 50, "raison": ""})
            f_data = scores_f.get((f["id"], h["id"]), {"score": 50, "raison": ""})

            score_h   = h_data["score"]
            score_f   = f_data["score"]
            score_avg = round((score_h + score_f) / 2)

            # Mutual match : les deux se donnent ≥ 70
            is_mutual = score_h >= 70 and score_f >= 70

            all_scores.append({
                "profil_a": h,
                "profil_b": f,
                "score":    score_avg,
                "score_h":  score_h,   # score du point de vue de l'homme
                "score_f":  score_f,   # score du point de vue de la femme
                "raison":   h_data["raison"] or f_data["raison"],
                "mutual":   is_mutual,
            })

    all_scores.sort(key=lambda x: x["score"], reverse=True)
    return all_scores


def build_results(all_scores, profiles):
    """Construit la structure finale pour l'affichage"""

    # Top 20 matchs globaux
    top_matchs = all_scores[:20]

    # Top 3 par personne (pas juste le meilleur)
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
                    "match":   other,
                    "score":   entry["score"],
                    "raison":  entry["raison"],
                    "mutual":  entry["mutual"],
                })

    # Compatibilité avec best_per_person (rétrocompatibilité avec l'ancien HTML)
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

    # Mutual matches (les deux se veulent mutuellement)
    mutual_matches = [e for e in all_scores if e["mutual"]]

    return {
        "top_matchs":      top_matchs,
        "best_per_person": best_per_person,
        "mutual_matches":  mutual_matches,
        "total_profils":   len(profiles),
        "stats": {
            "hommes":   len([p for p in profiles if p["sexe"].lower() in ("homme","h","m","male")]),
            "femmes":   len([p for p in profiles if p["sexe"].lower() in ("femme","f","female")]),
            "mutuals":  len(mutual_matches),
        }
    }


def main():
    if not ANTHROPIC_API_KEY:
        print("❌ ANTHROPIC_API_KEY manquant. Lance : export ANTHROPIC_API_KEY=sk-...")
        sys.exit(1)

    print("📋 Chargement des profils depuis Google Sheets...")
    profiles = load_profiles_from_sheet()
    print(f"✓ {len(profiles)} profils chargés\n")

    if len(profiles) < 2:
        print("❌ Pas assez de profils (minimum 2)")
        sys.exit(1)

    print("🤖 Calcul des matchs via Claude...\n")
    all_scores = compute_matches(profiles)

    results = build_results(all_scores, profiles)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Résultats sauvegardés dans {OUTPUT_FILE}")
    print(f"   → {results['stats']['hommes']} hommes × {results['stats']['femmes']} femmes")
    print(f"   → {results['stats']['mutuals']} mutual matches 🔥")
    if all_scores:
        top = all_scores[0]
        print(f"   → Top match : {top['profil_a']['nom']} × {top['profil_b']['nom']} ({top['score']}/100)")
    print("\nOuvre maintenant display.html dans ton navigateur 🎉")


if __name__ == "__main__":
    main()
