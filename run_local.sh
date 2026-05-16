# REGULA-RH Vaccipha × Umed — MVP local

REGULA-RH est un MVP local de régulation des ressources humaines entre les postes Vaccipha en pharmacies et les missions Umed à domicile.

L'application permet de :

- enregistrer les prestataires Umed : aides-soignants et IDE ;
- gérer les pharmacies Vaccipha ;
- saisir les demandes Umed à domicile ;
- renseigner les disponibilités journalières ;
- générer automatiquement le planning quotidien ;
- calculer les coûts journaliers ;
- gérer les incidents, sanctions, pénalités et restrictions ;
- appliquer un système de points et de niveaux de performance ;
- calculer une paie conditionnelle selon les jours validés, les bonus et les pénalités.

Toutes les données restent locales dans une base SQLite `regula_rh.db`.
Aucune donnée n'est envoyée vers un service externe.

---

## 1. Installation

Dans le dossier du projet :

```bash
pip install -r requirements.txt
streamlit run app.py
```

Au premier lancement, utiliser le bouton **Charger données de démonstration** dans la barre latérale pour créer :

- 20 aides-soignants ;
- 10 IDE ;
- 20 pharmacies ;
- 8 demandes Umed ;
- 4 clusters ;
- des disponibilités pour la date du jour.

---

## 2. Structure des fichiers

```text
regula_rh_mvp/
├── app.py              # Interface Streamlit
├── algorithm.py        # Algorithme de régulation RH
├── database.py         # Base SQLite, tables, paramètres, données démo
├── requirements.txt    # Dépendances Python
└── README.md           # Documentation
```

La base `regula_rh.db` est créée automatiquement au premier lancement.

---

## 3. Catégories d'agents

### Aide-soignant — AS

- Taux journalier : **5 000 FCFA**
- Prime transport : **1 000 FCFA**
- Coût journalier total : **6 000 FCFA**

Missions possibles :

- poste en pharmacie Vaccipha si habilité ;
- surveillance simple ;
- garde à domicile non technique ;
- appui logistique ;
- appui vaccination selon protocole autorisé.

Restriction majeure : un AS ne peut jamais être affecté automatiquement à un acte infirmier technique.

### Infirmier Diplômé d'État — IDE

- Taux journalier : **10 000 FCFA**
- Prime transport : **1 000 FCFA**
- Coût journalier total : **11 000 FCFA**

Missions possibles :

- poste en pharmacie Vaccipha si habilité ;
- vaccination ;
- surveillance longue durée ;
- injection ;
- prélèvement sanguin ;
- pose de perfusion ;
- pansement simple ou complexe ;
- soins infirmiers à domicile ;
- supervision ponctuelle d'un AS.

---

## 4. Logique de l'algorithme

La fonction principale est :

```python
generate_daily_planning(date_str)
```

Elle réalise les étapes suivantes :

1. charge les pharmacies actives ;
2. charge les demandes Umed en attente ;
3. charge les agents disponibles ;
4. identifie les demandes nécessitant obligatoirement un IDE ;
5. bloque les demandes IDE sans prescription ou validation médicale si les paramètres l'exigent ;
6. protège une réserve minimale d'IDE par cluster lorsqu'une mission IDE est prévue ;
7. couvre d'abord les pharmacies Vaccipha ;
8. priorise les AS habilités pour les postes simples en pharmacie afin d'optimiser les coûts ;
9. affecte ensuite les missions Umed par priorité P1, P2, P3, P4 ;
10. exclut automatiquement les agents non éligibles ;
11. calcule un score d'affectation ;
12. génère les alertes ;
13. calcule les coûts journaliers.

---

## 5. Règles d'éligibilité clinique

Le système exclut automatiquement :

- les agents suspendus ;
- les agents à recycler ;
- les AS sur les actes IDE ;
- les agents sans habilitation Vaccipha pour un poste pharmacie ;
- les agents sans habilitation soins à domicile pour une mission à domicile ;
- les IDE sans habilitation actes infirmiers pour une injection, perfusion, prélèvement ou pansement complexe ;
- les agents ayant un incident bloquant confirmé ;
- les agents avec score inférieur à 50 pour les missions P1/P2.

Si une mission IDE est demandée sans prescription médicale ou sans validation médicale, l'application peut bloquer l'affectation selon les paramètres.

---

## 6. Calcul des coûts

### AS

```text
coût AS = 5 000 + 1 000 = 6 000 FCFA / jour
```

### IDE

```text
coût IDE = 10 000 + 1 000 = 11 000 FCFA / jour
```

### Coût journalier total

```text
coût_total = (nombre_AS_mobilisés × 6 000) + (nombre_IDE_mobilisés × 11 000)
```

---

## 7. Gestion des incidents, performance et paie conditionnelle

Le MVP intègre un module d'incidents inspiré de la procédure Umed :

- signalement anonyme ou nominatif ;
- qualification administrative ou médicale ;
- gravité faible, modérée, élevée ou très élevée ;
- statut d'instruction ;
- décision Direction ;
- sanction ;
- pénalité de points ;
- impact paie ;
- remboursement ou pénalité financière si applicable.

Une sanction définitive n'est appliquée qu'après validation par la Direction dans le menu **Traitement des incidents**.

### UMED SCORE RH

Chaque agent dispose :

- d'un score de fiabilité ;
- de transactions de points ;
- d'un niveau : Rouge, Bronze, Argent, Or, Platine ;
- d'un statut opérationnel ;
- de badges dans les futures versions.

### Niveaux

| Niveau | Score | Effet |
|---|---:|---|
| Rouge | < 50 | restriction forte, non éligible P1/P2 |
| Bronze | 50–69 | sous surveillance, pas de bonus |
| Argent | 70–84 | bonus 5% |
| Or | 85–94 | bonus 10% |
| Platine | 95–100 | bonus 15% |

### Paie conditionnelle

```text
paie_base = jours_validés × (taux_journalier + transport)
paie_nette = paie_base + bonus_performance + primes_spécifiques - remboursements - pénalités_financières
```

Le bonus mensuel est supprimé en cas d'incident élevé ou très élevé confirmé dans le mois.

---

## 8. Paramètres modifiables

Le menu **Paramètres** permet de modifier :

- taux journalier AS ;
- taux journalier IDE ;
- prime transport AS ;
- prime transport IDE ;
- réserve minimale IDE par cluster ;
- priorisation des AS en pharmacie ;
- autorisation IDE en pharmacie ;
- blocage si prescription absente ;
- blocage si validation médicale absente.

---

## 9. Limites du MVP

Cette version ne comprend pas encore :

- authentification multi-utilisateur ;
- gestion avancée des rôles et droits ;
- géolocalisation GPS réelle ;
- notifications WhatsApp/SMS ;
- application mobile ;
- API ;
- signature électronique ;
- module paie légal complet ;
- audit de sécurité complet.

Les règles de paie, de sanctions, de suspension et de remboursement doivent être validées juridiquement et intégrées aux contrats, règlements internes et procédures applicables avant usage contraignant.

---

## 10. Évolutions recommandées

1. Authentification et rôles : Direction, Coordinateur, Superviseur, Comptabilité, Directeur Médical.
2. Application mobile agent.
3. Notifications WhatsApp/SMS.
4. Carte de géolocalisation.
5. Signature numérique des missions.
6. Intégration CRM patient.
7. Export comptable.
8. Tableaux de bord avancés par district, cluster et partenaire.
9. Journal d'audit renforcé.
10. Hébergement local sécurisé sur serveur ADES/Umed.
