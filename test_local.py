#!/usr/bin/env python3
"""Test local — sans Google Sheets, profils hardcodés"""

import json, time, sys
import anthropic

# ─── Clé API ───────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OUTPUT_FILE = "results.json"

# ─── CONFIG matching ───────────────────────────────────────────────
CRITERES = {
    "Valeurs & vision de la vie"  : 30,
    "Religion & culture"          : 25,
    "Personnalité & caractère"    : 20,
    "Style de vie & passions"     : 15,
    "Projet de vie & famille"     : 10,
}
SEUIL_MUTUAL = 70
TOP_N = 20

# ─── Profils de test ───────────────────────────────────────────────
PROFILES = [
    {
        "id": 1, "nom": "Léa", "nom_famille": "Cohen",
        "age": "27", "sexe": "Féminin", "telephone": "0501234567",
        "resume_ia": "Léa valorise l'authenticité et la curiosité intellectuelle avant tout. Elle recherche un partenaire avec qui partager des discussions profondes et construire une relation basée sur la confiance mutuelle. Passionnée d'archéologie levantine, elle consacre ses weekends à des fouilles bénévoles et à la randonnée dans le désert du Néguev. Son style de vie mêle spiritualité, yoga et cuisine méditerranéenne faite maison. En relation, elle est attentive et loyale, mais a besoin d'indépendance et d'espace pour ses projets personnels. Ce qui la rend unique, c'est sa capacité à voir la beauté dans les vieilles pierres comme dans les gens."
    },
    {
        "id": 2, "nom": "David", "nom_famille": "Mizrahi",
        "age": "31", "sexe": "Masculin", "telephone": "0529876543",
        "resume_ia": "David est un entrepreneur tech ambitieux qui valorise l'humour et l'énergie positive dans une relation. Il cherche une partenaire spontanée, prête à voyager et à sortir de sa zone de confort. Son quotidien alterne entre le développement de sa startup, le hiking en Galilée et la cuisine israélienne créative qu'il partage volontiers avec ses amis. En couple, il est généreux et protecteur, mais reste taquin et ne se prend jamais trop au sérieux. Ce qui le distingue, c'est son énergie contagieuse et son optimisme à toute épreuve."
    },
    {
        "id": 3, "nom": "Sarah", "nom_famille": "Touati",
        "age": "24", "sexe": "Féminin", "telephone": "0541122334",
        "resume_ia": "Sarah place la liberté et la créativité au cœur de ses valeurs. Elle n'est pas pressée de s'engager et recherche avant tout une connexion authentique, sans étiquette imposée trop vite. Photographe freelance, elle a déjà parcouru douze pays et adore documenter les marchés et la street art de Tel Aviv. Son mode de vie est flexible et improvisé, entre cafés branchés et soirées électro. En relation, elle est passionnée et directe, mais a besoin qu'on respecte son rythme. Ce qui la rend unique, c'est son regard artistique sur le monde et son franc-parler."
    },
    {
        "id": 4, "nom": "Yoni", "nom_famille": "Edery",
        "age": "35", "sexe": "Masculin", "telephone": "0556677889",
        "resume_ia": "Yoni valorise la stabilité et la famille, deux piliers qu'il a appris à apprécier après son divorce il y a deux ans. Il cherche une relation sérieuse, construite sur le long terme, avec quelqu'un de mature et bienveillant. Comptable de profession, il consacre son temps libre à la coinche entre amis et au football le samedi. Son style de vie est posé, routinier mais chaleureux, centré sur les repas en famille élargie. En relation, il est fiable et attentionné, à l'écoute des besoins de l'autre. Ce qui le rend unique, c'est sa loyauté sans faille et son sens de l'humour discret mais mordant."
    },
]

def build_criteria_text():
    total = sum(CRITERES.values())
    return "\n".join([f"  - {c} : {round(p/total*100)}%" for c, p in CRITERES.items()])

def rank_for_person(client, person, candidates):
    criteria_text = build_criteria_text()
    candidates_text = "\n\n".join([
        f"[ID:{c['id']}] {c['nom']} {c['nom_famille']}, {c['age']} ans :\n{c['resume_ia']}"
        for c in candidates
    ])
    prompt = f"""Tu es un expert en compatibilité romantique.

PROFIL DE {person['nom'].upper()} {person['nom_famille'].upper()}, {person['age']} ans :
{person['resume_ia']}

Classe ces {len(candidates)} candidats du plus au moins compatible avec {person['nom']}.

GRILLE DE NOTATION (total = 100 points) :
{criteria_text}

Réponds UNIQUEMENT en JSON :
{{
  "classement": [
    {{"id": <id>, "score": <0-100>, "raison": "<une phrase courte en français>"}},
    ...
  ]
}}

CANDIDATS :
{candidates_text}"""

    response = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.content[0].text.strip()
    start = text.find('{')
    end = text.rfind('}') + 1
    return json.loads(text[start:end])["classement"]

def main():
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    hommes = [p for p in PROFILES if p["sexe"].lower() in ("masculin","homme","m","male")]
    femmes = [p for p in PROFILES if p["sexe"].lower() in ("féminin","feminin","femme","f","female")]

    print(f"✓ {len(hommes)} hommes | {len(femmes)} femmes\n")

    scores_h, scores_f = {}, {}

    for h in hommes:
        print(f"  Classement pour {h['nom']}...", end=" ", flush=True)
        for item in rank_for_person(client, h, femmes):
            scores_h[(h["id"], item["id"])] = {"score": item["score"], "raison": item["raison"]}
        print("✓")
        time.sleep(0.5)

    for f in femmes:
        print(f"  Classement pour {f['nom']}...", end=" ", flush=True)
        for item in rank_for_person(client, f, hommes):
            scores_f[(f["id"], item["id"])] = {"score": item["score"], "raison": item["raison"]}
        print("✓")
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
                "mutual": h_d["score"] >= SEUIL_MUTUAL and f_d["score"] >= SEUIL_MUTUAL,
            })

    all_scores.sort(key=lambda x: x["score"], reverse=True)

    # Top3 par personne
    top3_per_person = {}
    for entry in all_scores:
        for role in ("profil_a", "profil_b"):
            person = entry[role]
            other  = entry["profil_b"] if role == "profil_a" else entry["profil_a"]
            pid = person["id"]
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

    results = {
        "top_matchs":      all_scores[:TOP_N],
        "best_per_person": best_per_person,
        "mutual_matches":  mutual_matches,
        "total_profils":   len(PROFILES),
        "stats": {
            "hommes": len(hommes), "femmes": len(femmes),
            "mutuals": len(mutual_matches),
        }
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ results.json généré !")
    print(f"   → {results['stats']['hommes']}H × {results['stats']['femmes']}F")
    print(f"   → {results['stats']['mutuals']} mutual(s) 🔥")
    if all_scores:
        top = all_scores[0]
        print(f"   → 🏆 {top['profil_a']['nom']} × {top['profil_b']['nom']} ({top['score']}%)")

if __name__ == "__main__":
    main()
