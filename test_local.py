#!/usr/bin/env python3
"""SpeedAite — Test local 20 profils, sans Google Sheets"""

import json, time, sys, os
import anthropic

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OUTPUT_FILE = "results.json"

CRITERES = {
    "Religion & cacherout"        : 35,
    "Valeurs & vision de la vie"  : 25,
    "Personnalité & caractère"    : 20,
    "Style de vie & passions"     : 12,
    "Projet de vie & famille"     : 8,
}
SEUIL_MUTUAL = 70
TOP_N = 20

PROFILES = [
  {"id":1,"nom":"Léa","nom_famille":"Cohen","age":"27","sexe":"Féminin","telephone":"0501234567",
   "resume_ia":"Léa valorise l'authenticité et la curiosité intellectuelle. Traditionaliste (masortit), elle garde une cacherout souple à la maison et aime le dîner du vendredi soir en famille, sans être stricte sur le Chabbat. Passionnée d'archéologie levantine, elle fait des fouilles bénévoles et de la randonnée. En relation, attentive et loyale, elle a besoin d'indépendance. Elle cherche quelqu'un d'ouvert spirituellement, sans rigidité religieuse."},
  {"id":2,"nom":"David","nom_famille":"Mizrahi","age":"31","sexe":"Masculin","telephone":"0529876543",
   "resume_ia":"David est laïc (hiloni) et ne pratique pas, même s'il respecte les fêtes en famille par tradition. Entrepreneur tech, il valorise l'humour et l'énergie positive. Il cherche une partenaire spontanée, peu importe son niveau de religiosité tant qu'elle respecte son mode de vie libre. Hiking, cuisine créative, voyages. Généreux et taquin en couple, son optimisme contagieux le distingue."},
  {"id":3,"nom":"Sarah","nom_famille":"Touati","age":"24","sexe":"Féminin","telephone":"0541122334",
   "resume_ia":"Sarah est complètement laïque, voire agnostique, et ne garde aucune cacherout. Elle place la liberté et la créativité au-dessus de tout. Photographe freelance, globe-trotteuse, elle vit entre cafés branchés et soirées électro. Passionnée et directe, elle cherche une connexion authentique sans pression religieuse ni engagement précoce."},
  {"id":4,"nom":"Yoni","nom_famille":"Edery","age":"35","sexe":"Masculin","telephone":"0556677889",
   "resume_ia":"Yoni est traditionaliste : il garde la cacherout chez lui et va à la synagogue pour les grandes fêtes, sans être strict sur Chabbat. Comptable, divorcé depuis deux ans, il valorise la stabilité et la famille. Coinche et foot le samedi. Fiable et chaleureux, il cherche une partenaire qui partage des valeurs traditionnelles sans être rigide."},
  {"id":5,"nom":"Noa","nom_famille":"Bensimon","age":"29","sexe":"Féminin","telephone":"0533445566",
   "resume_ia":"Noa est laïque au quotidien mais respecte Yom Kippour et le Seder de Pessah par attachement familial. Financière ambitieuse, sportive (marathon, crossfit), elle cherche un partenaire confiant non intimidé par sa réussite. Franche, parfois trop directe. Peu importe la pratique religieuse de l'autre, tant qu'il y a du respect mutuel."},
  {"id":6,"nom":"Eytan","nom_famille":"Azoulay","age":"26","sexe":"Masculin","telephone":"0544556677",
   "resume_ia":"Eytan est laïc et sort souvent le vendredi soir en boîte, sans aucune pratique religieuse. DJ amateur, il valorise la légèreté et le fun avant tout. Créatif et attachant mais hésitant face à l'engagement. Il préfère une partenaire tout aussi décontractée sur le plan religieux."},
  {"id":7,"nom":"Tamar","nom_famille":"Suissa","age":"33","sexe":"Féminin","telephone":"0555667788",
   "resume_ia":"Tamar est datiya (religieuse pratiquante) : cacherout stricte, Chabbat intégralement respecté, étude de la Torah le vendredi soir. Psychologue, elle valorise la profondeur émotionnelle et la spiritualité juive. Patiente mais exigeante sur l'authenticité, elle cherche impérativement un partenaire pratiquant ou prêt à se rapprocher de la tradition."},
  {"id":8,"nom":"Raphaël","nom_famille":"Ohana","age":"38","sexe":"Masculin","telephone":"0566778899",
   "resume_ia":"Raphaël est traditionaliste moderne, cacherout respectée à la maison, fêtes célébrées en famille élargie. Architecte, père de deux enfants, il valorise la transmission et la famille recomposée. Calme et posé, il cherche une partenaire mature partageant un attachement similaire à la tradition juive sans extrémisme."},
  {"id":9,"nom":"Shirel","nom_famille":"Hadad","age":"22","sexe":"Féminin","telephone":"0577889900",
   "resume_ia":"Shirel est laïque, sans aucune pratique religieuse, étudiante en art à Florentine. Elle valorise la spontanéité et l'aventure, peint et fréquente les galeries underground. Passionnée mais volage, elle cherche surtout à explorer sans contrainte, y compris sur le plan religieux."},
  {"id":10,"nom":"Yossef","nom_famille":"Knafo","age":"41","sexe":"Masculin","telephone":"0588990011",
   "resume_ia":"Yossef est traditionaliste : cacherout à la maison, synagogue le vendredi soir occasionnellement. Plombier indépendant, divorcé, il valorise la loyauté et la simplicité après un divorce difficile. Protecteur mais parfois jaloux, il cherche une femme sincère partageant un attachement traditionnel similaire."},
  {"id":11,"nom":"Maya","nom_famille":"Dahan","age":"30","sexe":"Féminin","telephone":"0599001122",
   "resume_ia":"Maya est laïque mais respecte Yom Kippour et certaines fêtes par culture plus que par foi. Avocate, passionnée de cuisine fusion franco-israélienne, elle valorise l'équilibre vie pro/perso. Réfléchie, elle prend son temps avant de s'engager et privilégie la compatibilité de valeurs à la pratique religieuse stricte."},
  {"id":12,"nom":"Ilan","nom_famille":"Partouche","age":"27","sexe":"Masculin","telephone":"0501112233",
   "resume_ia":"Ilan est laïc et voyage souvent le Chabbat sans aucun scrupule religieux. Guide de trek freelance, globe-trotteur, il valorise l'aventure et la liberté. Passionné mais redoute la routine, il cherche une partenaire curieuse et tout aussi peu attachée à la pratique religieuse."},
  {"id":13,"nom":"Adi","nom_famille":"Chocron","age":"36","sexe":"Féminin","telephone":"0512223344",
   "resume_ia":"Adi est traditionaliste avec une cacherout stricte qu'elle exige aussi chez son futur partenaire. Infirmière, dévouée et empathique, elle valorise la stabilité émotionnelle après des relations compliquées. Elle cherche un engagement sérieux avec quelqu'un respectant au minimum les codes traditionnels juifs."},
  {"id":14,"nom":"Doron","nom_famille":"Amar","age":"45","sexe":"Masculin","telephone":"0523334455",
   "resume_ia":"Doron est traditionaliste, fréquente surtout les restaurants cashers par habitude commerciale (il en possède deux). Restaurateur expérimenté, généreux et charismatique, il valorise la maturité. Il cherche une femme posée, peu importe son niveau de pratique tant qu'elle apprécie la convivialité des repas en famille."},
  {"id":15,"nom":"Leeor","nom_famille":"Malka","age":"25","sexe":"Féminin","telephone":"0534445566",
   "resume_ia":"Leeor est laïque, influenceuse lifestyle sans aucune pratique religieuse particulière. Elle valorise l'authenticité loin des faux-semblants des applis classiques. Intense et spontanée, parfois instable, elle cherche une connexion réelle sans considération religieuse précise."},
  {"id":16,"nom":"Avi","nom_famille":"Cohen","age":"29","sexe":"Masculin","telephone":"0545556677",
   "resume_ia":"Avi est laïc et plutôt sceptique envers la religion, féru de débats politiques et philosophiques. Doctorant en sciences politiques, il valorise l'intellect et la culture. Attentif mais cérébral, il cherche une partenaire qui aime échanger, peu importe sa religiosité, mais ouverte au débat sur le sujet."},
  {"id":17,"nom":"Romi","nom_famille":"Bouhadana","age":"31","sexe":"Féminin","telephone":"0556667788",
   "resume_ia":"Romi se définit comme spirituelle mais non religieuse au sens orthodoxe : elle garde une cacherout flexible et privilégie une spiritualité personnelle (méditation, conscience) à la pratique institutionnelle. Coach de vie, elle valorise le développement personnel. Elle cherche un partenaire émotionnellement disponible, religieux ou non."},
  {"id":18,"nom":"Gabriel","nom_famille":"Nahmias","age":"33","sexe":"Masculin","telephone":"0567778899",
   "resume_ia":"Gabriel est traditionaliste léger : cacherout respectée par habitude familiale, sans grande conviction. Développeur web, passionné de coinche compétitive, il valorise l'humour et la complicité. Fidèle et drôle, il cherche une partenaire avec qui rire, sans exigence religieuse particulière."},
  {"id":19,"nom":"Yael","nom_famille":"Levy","age":"39","sexe":"Féminin","telephone":"0578889900",
   "resume_ia":"Yael est datiya leumi (religieuse-nationale) : cacherout stricte, Chabbat observé, synagogue régulière. Sage-femme investie, elle valorise la sincérité et un projet de vie commun rapide. Directe sur ses attentes, elle exige impérativement un partenaire pratiquant pour fonder une famille religieuse cohérente."},
  {"id":20,"nom":"Michael","nom_famille":"Abergel","age":"24","sexe":"Masculin","telephone":"0589990011",
   "resume_ia":"Michael est laïc, étudiant en cinéma, sans pratique religieuse. Il valorise la liberté et le moment présent, ne cherchant rien de précis pour l'instant. Créatif et insouciant, peu prévisible, il est ouvert à rencontrer des profils de tous niveaux de pratique religieuse."},
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
    prompt = f"""Tu es un expert en compatibilité romantique pour une soirée speed dating en Israël.

PROFIL DE {person['nom'].upper()} {person['nom_famille'].upper()}, {person['age']} ans :
{person['resume_ia']}

Classe ces {len(candidates)} candidats du plus au moins compatible avec {person['nom']}.

GRILLE DE NOTATION (total = 100 points) :
{criteria_text}

Important : la compatibilité religieuse est le critère le plus lourd. Une incompatibilité forte (ex: datiya vs laïc, ou cacherout stricte vs aucune pratique) doit fortement réduire le score, même si d'autres critères s'accordent bien.

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
        model="claude-sonnet-4-6", max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.content[0].text.strip()
    start = text.find('{'); end = text.rfind('}') + 1
    return json.loads(text[start:end])["classement"]

def main():
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    hommes = [p for p in PROFILES if p["sexe"].lower() in ("masculin","homme","m","male")]
    femmes = [p for p in PROFILES if p["sexe"].lower() in ("féminin","feminin","femme","f","female")]
    print(f"✓ {len(hommes)} hommes | {len(femmes)} femmes → {len(hommes)+len(femmes)} appels API\n")

    scores_h, scores_f = {}, {}

    for h in hommes:
        print(f"  {h['nom']}...", end=" ", flush=True)
        for item in rank_for_person(client, h, femmes):
            scores_h[(h["id"], item["id"])] = {"score": item["score"], "raison": item["raison"]}
        print("✓"); time.sleep(0.5)

    for f in femmes:
        print(f"  {f['nom']}...", end=" ", flush=True)
        for item in rank_for_person(client, f, hommes):
            scores_f[(f["id"], item["id"])] = {"score": item["score"], "raison": item["raison"]}
        print("✓"); time.sleep(0.5)

    all_scores = []
    for h in hommes:
        for f in femmes:
            h_d = scores_h.get((h["id"], f["id"]), {"score": 50, "raison": ""})
            f_d = scores_f.get((f["id"], h["id"]), {"score": 50, "raison": ""})
            score_avg = round((h_d["score"] + f_d["score"]) / 2)
            all_scores.append({
                "profil_a": h, "profil_b": f, "score": score_avg,
                "score_h": h_d["score"], "score_f": f_d["score"],
                "raison": h_d["raison"] or f_d["raison"],
                "mutual": h_d["score"] >= SEUIL_MUTUAL and f_d["score"] >= SEUIL_MUTUAL,
            })
    all_scores.sort(key=lambda x: x["score"], reverse=True)

    top3_per_person = {}
    for entry in all_scores:
        for role in ("profil_a","profil_b"):
            person = entry[role]; other = entry["profil_b"] if role=="profil_a" else entry["profil_a"]
            pid = person["id"]
            if pid not in top3_per_person:
                top3_per_person[pid] = {"personne": person, "top3": []}
            if len(top3_per_person[pid]["top3"]) < 3:
                top3_per_person[pid]["top3"].append({"match": other, "score": entry["score"], "raison": entry["raison"], "mutual": entry["mutual"]})

    best_per_person = [{"personne": v["personne"], "meilleur_match": v["top3"][0]["match"] if v["top3"] else None,
        "score": v["top3"][0]["score"] if v["top3"] else 0, "raison": v["top3"][0]["raison"] if v["top3"] else "",
        "top3": v["top3"]} for v in top3_per_person.values()]

    mutual_matches = [e for e in all_scores if e["mutual"]]
    results = {
        "top_matchs": all_scores[:TOP_N], "best_per_person": best_per_person,
        "mutual_matches": mutual_matches, "total_profils": len(PROFILES),
        "stats": {"hommes": len(hommes), "femmes": len(femmes), "mutuals": len(mutual_matches)}
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Done ! {len(hommes)}H × {len(femmes)}F → {len(mutual_matches)} mutual(s) 🔥")
    if all_scores:
        top = all_scores[0]
        print(f"🏆 {top['profil_a']['nom']} × {top['profil_b']['nom']} ({top['score']}%)")
    print("\nTop 5 :")
    for i, m in enumerate(all_scores[:5]):
        tag = " ♥ MUTUAL" if m["mutual"] else ""
        print(f"  {i+1}. {m['profil_a']['nom']} × {m['profil_b']['nom']} — {m['score']}%{tag}")

if __name__ == "__main__":
    main()
