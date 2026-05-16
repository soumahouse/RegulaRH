"""Local SQLite database helpers for REGULA-RH Vaccipha x Umed.

All data are stored locally in regula_rh.db. No external API or cloud service is used.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime
from typing import Any, Iterable

import pandas as pd

DB_NAME = os.environ.get("REGULA_RH_DB", "regula_rh.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def execute(sql: str, params: Iterable[Any] | dict[str, Any] = ()) -> None:
    with get_connection() as conn:
        conn.execute(sql, params)
        conn.commit()


def executemany(sql: str, rows: list[Iterable[Any]]) -> None:
    with get_connection() as conn:
        conn.executemany(sql, rows)
        conn.commit()


def query_df(sql: str, params: Iterable[Any] | dict[str, Any] = ()) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def query_one(sql: str, params: Iterable[Any] | dict[str, Any] = ()) -> sqlite3.Row | None:
    with get_connection() as conn:
        cur = conn.execute(sql, params)
        return cur.fetchone()


def init_db() -> None:
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS parametres (
                cle TEXT PRIMARY KEY,
                valeur TEXT NOT NULL,
                description TEXT
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS agents (
                id_agent INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                prenom TEXT,
                telephone TEXT,
                profession TEXT,
                categorie_agent TEXT DEFAULT 'AS',
                competences TEXT,
                actes_autorises TEXT,
                niveau_competence_clinique TEXT DEFAULT 'basique',
                cluster_principal TEXT,
                commune_residence TEXT,
                pharmacie_principale INTEGER,
                statut TEXT DEFAULT 'actif',
                score_fiabilite INTEGER DEFAULT 80,
                nombre_jours_travailles_mois INTEGER DEFAULT 0,
                taux_journalier INTEGER DEFAULT 5000,
                prime_transport INTEGER DEFAULT 1000,
                cout_journalier_total INTEGER DEFAULT 6000,
                habilitation_vaccipha TEXT DEFAULT 'oui',
                habilitation_soins_domicile TEXT DEFAULT 'non',
                habilitation_actes_infirmiers TEXT DEFAULT 'non',
                numero_ordre_ou_autorisation TEXT,
                date_validation_competence TEXT,
                date_expiration_habilitation TEXT,
                observations TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pharmacies (
                id_pharmacie INTEGER PRIMARY KEY AUTOINCREMENT,
                nom_pharmacie TEXT NOT NULL,
                commune TEXT,
                quartier TEXT,
                cluster TEXT,
                niveau_activite TEXT DEFAULT 'moyen',
                couverture_minimale INTEGER DEFAULT 1,
                agent_titulaire INTEGER,
                backups_autorises TEXT,
                statut TEXT DEFAULT 'active',
                observations TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS demandes_umed (
                id_demande INTEGER PRIMARY KEY AUTOINCREMENT,
                date_demande TEXT NOT NULL,
                type_mission TEXT NOT NULL,
                priorite TEXT DEFAULT 'P3',
                commune TEXT,
                quartier TEXT,
                cluster TEXT,
                duree_estimee TEXT DEFAULT 'journée',
                competence_requise TEXT,
                categorie_agent_requise TEXT DEFAULT 'indifférent',
                acte_requis TEXT,
                niveau_technicite TEXT DEFAULT 'faible',
                acte_infirmier TEXT DEFAULT 'non',
                prescription_medicale_requise TEXT DEFAULT 'non',
                prescription_medicale_disponible TEXT DEFAULT 'oui',
                validation_medecin_requise TEXT DEFAULT 'non',
                validation_medecin_obtenue TEXT DEFAULT 'oui',
                heure_limite_prise_en_charge TEXT,
                statut TEXT DEFAULT 'en attente',
                agent_affecte INTEGER,
                observations TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS disponibilites (
                id_disponibilite INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                agent_id INTEGER NOT NULL,
                statut_disponibilite TEXT DEFAULT 'disponible',
                commentaire TEXT,
                UNIQUE(date, agent_id)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS planning (
                id_planning INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                agent_id INTEGER NOT NULL,
                categorie_agent TEXT,
                profession TEXT,
                affectation_type TEXT NOT NULL,
                affectation_id INTEGER,
                affectation_label TEXT,
                cluster TEXT,
                priorite_mission TEXT,
                cout_journalier INTEGER DEFAULT 0,
                statut TEXT DEFAULT 'planifié',
                score_affectation REAL DEFAULT 0,
                observations TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS couts_journaliers (
                id_cout INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                nombre_as_mobilises INTEGER DEFAULT 0,
                nombre_ide_mobilises INTEGER DEFAULT 0,
                total_taux_journalier_as INTEGER DEFAULT 0,
                total_transport_as INTEGER DEFAULT 0,
                total_taux_journalier_ide INTEGER DEFAULT 0,
                total_transport_ide INTEGER DEFAULT 0,
                cout_total INTEGER DEFAULT 0,
                nombre_pharmacies_couvertes INTEGER DEFAULT 0,
                nombre_missions_umed INTEGER DEFAULT 0,
                cout_moyen_par_affectation REAL DEFAULT 0
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS alertes (
                id_alerte INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                niveau TEXT DEFAULT 'info',
                type_alerte TEXT,
                message TEXT,
                statut TEXT DEFAULT 'ouverte',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                id_incident INTEGER PRIMARY KEY AUTOINCREMENT,
                date_signalement TEXT NOT NULL,
                anonyme TEXT DEFAULT 'oui',
                declarant TEXT,
                agent_id INTEGER,
                equipe_id TEXT,
                categorie TEXT,
                type_incident TEXT,
                gravite TEXT,
                description TEXT,
                preuves TEXT,
                statut_traitement TEXT DEFAULT 'signalé',
                decision_direction TEXT,
                sanction TEXT,
                penalite_points INTEGER DEFAULT 0,
                impact_paie TEXT,
                montant_remboursement INTEGER DEFAULT 0,
                montant_penalite INTEGER DEFAULT 0,
                responsabilite_collective TEXT DEFAULT 'non',
                date_cloture TEXT,
                observations TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS incident_actions (
                id_action INTEGER PRIMARY KEY AUTOINCREMENT,
                id_incident INTEGER NOT NULL,
                date_action TEXT DEFAULT CURRENT_TIMESTAMP,
                type_action TEXT,
                auteur TEXT,
                commentaire TEXT,
                statut_avant TEXT,
                statut_apres TEXT
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_scores (
                id_score INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                mois INTEGER NOT NULL,
                annee INTEGER NOT NULL,
                score_initial INTEGER DEFAULT 80,
                points_positifs INTEGER DEFAULT 0,
                points_negatifs INTEGER DEFAULT 0,
                score_final INTEGER DEFAULT 80,
                niveau TEXT DEFAULT 'Argent',
                bonus_percent REAL DEFAULT 0.05,
                statut_operationnel TEXT DEFAULT 'actif',
                UNIQUE(agent_id, mois, annee)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS point_transactions (
                id_transaction INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                source TEXT,
                description TEXT,
                points INTEGER DEFAULT 0,
                type_transaction TEXT,
                id_incident INTEGER,
                id_mission INTEGER
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS badges (
                id_badge INTEGER PRIMARY KEY AUTOINCREMENT,
                nom_badge TEXT UNIQUE NOT NULL,
                description TEXT,
                condition_attribution TEXT,
                points_bonus INTEGER DEFAULT 0
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_badges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                id_badge INTEGER NOT NULL,
                date_attribution TEXT NOT NULL,
                actif TEXT DEFAULT 'oui',
                UNIQUE(agent_id, id_badge)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS payroll (
                id_payroll INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                mois INTEGER NOT NULL,
                annee INTEGER NOT NULL,
                jours_planifies INTEGER DEFAULT 0,
                jours_realises INTEGER DEFAULT 0,
                jours_valides INTEGER DEFAULT 0,
                jours_suspendus INTEGER DEFAULT 0,
                total_taux_journalier INTEGER DEFAULT 0,
                total_transport INTEGER DEFAULT 0,
                paie_base INTEGER DEFAULT 0,
                bonus_performance INTEGER DEFAULT 0,
                primes_specifiques INTEGER DEFAULT 0,
                remboursements INTEGER DEFAULT 0,
                penalites_financieres INTEGER DEFAULT 0,
                paie_nette INTEGER DEFAULT 0,
                statut_paie TEXT DEFAULT 'brouillon',
                observations TEXT,
                UNIQUE(agent_id, mois, annee)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS payroll_items (
                id_item INTEGER PRIMARY KEY AUTOINCREMENT,
                id_payroll INTEGER NOT NULL,
                date TEXT,
                type_item TEXT,
                libelle TEXT,
                montant INTEGER DEFAULT 0,
                reference TEXT
            )
            """
        )

        conn.commit()
    seed_defaults()


def seed_defaults() -> None:
    defaults = {
        "taux_journalier_AS": ("5000", "Taux journalier aide-soignant"),
        "taux_journalier_IDE": ("10000", "Taux journalier IDE"),
        "prime_transport_AS": ("1000", "Prime transport aide-soignant"),
        "prime_transport_IDE": ("1000", "Prime transport IDE"),
        "seuil_score_faible": ("50", "Seuil rouge"),
        "reserve_minimale_IDE_par_cluster": ("1", "Réserve IDE minimale si mission IDE prévue"),
        "prioriser_AS_pour_pharmacie": ("oui", "Prioriser AS habilité pour postes pharmacie simples"),
        "autoriser_IDE_sur_poste_pharmacie": ("oui", "Autoriser IDE sur poste pharmacie"),
        "bloquer_acte_IDE_si_prescription_absente": ("oui", "Bloquer actes IDE si prescription absente"),
        "bloquer_acte_IDE_si_validation_medecin_absente": ("oui", "Bloquer actes IDE si validation médicale absente"),
    }
    with get_connection() as conn:
        for key, (value, desc) in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO parametres(cle, valeur, description) VALUES (?, ?, ?)",
                (key, value, desc),
            )
        badges = [
            ("Ponctualité", "10 missions consécutives sans retard", "10 missions ponctuelles", 10),
            ("Zéro Incident", "Aucun incident confirmé dans le mois", "0 incident", 20),
            ("Back-up Fiable", "Au moins 5 remplacements réussis", "5 backups réussis", 10),
            ("Qualité Patient", "Satisfaction moyenne ≥ 4,5/5", "Score satisfaction", 10),
            ("Stock Safe", "Zéro erreur de stock sur 30 jours", "0 incident stock", 5),
            ("DASRI Safe", "Zéro incident déchets sur 30 jours", "0 incident déchets", 5),
            ("Urgence Ready", "Au moins 5 missions P1/P2 acceptées", "5 missions urgentes", 10),
            ("Mentor", "Agent Platine pouvant accompagner les nouveaux", "Platine + validation", 15),
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO badges(nom_badge, description, condition_attribution, points_bonus) VALUES (?, ?, ?, ?)",
            badges,
        )
        conn.commit()


def get_settings() -> dict[str, str]:
    df = query_df("SELECT cle, valeur FROM parametres")
    return dict(zip(df["cle"], df["valeur"])) if not df.empty else {}


def set_setting(key: str, value: str) -> None:
    execute("UPDATE parametres SET valeur=? WHERE cle=?", (value, key))


def bool_setting(settings: dict[str, str], key: str, default: bool = False) -> bool:
    value = settings.get(key, "oui" if default else "non")
    return str(value).lower() in {"oui", "yes", "true", "1"}


def load_demo_data() -> None:
    """Populate demo data only if core tables are empty."""
    init_db()
    count = query_one("SELECT COUNT(*) AS n FROM agents")
    if count and count["n"] > 0:
        return

    clusters = ["Cocody", "Plateau", "Marcory", "Yopougon"]
    communes = ["Cocody", "Plateau", "Marcory", "Yopougon", "Abobo", "Koumassi"]

    # Agents: 20 AS + 10 IDE
    for i in range(1, 21):
        cluster = clusters[(i - 1) % len(clusters)]
        execute(
            """
            INSERT INTO agents(nom, prenom, telephone, profession, categorie_agent, competences,
                               actes_autorises, niveau_competence_clinique, cluster_principal,
                               commune_residence, statut, score_fiabilite, taux_journalier,
                               prime_transport, cout_journalier_total, habilitation_vaccipha,
                               habilitation_soins_domicile, habilitation_actes_infirmiers, observations)
            VALUES (?, ?, ?, ?, 'AS', ?, ?, 'basique', ?, ?, 'actif', ?, 5000, 1000, 6000, 'oui', 'oui', 'non', ?)
            """,
            (
                f"AS{i:02d}",
                "Umed",
                f"070000{i:02d}",
                "aide-soignant",
                "vaccination, surveillance simple, garde à domicile, saisie numérique",
                "surveillance simple, garde non technique, appui vaccination",
                cluster,
                communes[(i - 1) % len(communes)],
                70 + (i % 25),
                "Donnée de démonstration",
            ),
        )

    for i in range(1, 11):
        cluster = clusters[(i - 1) % len(clusters)]
        execute(
            """
            INSERT INTO agents(nom, prenom, telephone, profession, categorie_agent, competences,
                               actes_autorises, niveau_competence_clinique, cluster_principal,
                               commune_residence, statut, score_fiabilite, taux_journalier,
                               prime_transport, cout_journalier_total, habilitation_vaccipha,
                               habilitation_soins_domicile, habilitation_actes_infirmiers, numero_ordre_ou_autorisation, observations)
            VALUES (?, ?, ?, ?, 'IDE', ?, ?, 'technique', ?, ?, 'actif', ?, 10000, 1000, 11000, 'oui', 'oui', 'oui', ?, ?)
            """,
            (
                f"IDE{i:02d}",
                "Umed",
                f"075000{i:02d}",
                "infirmier IDE",
                "vaccination, soins infirmiers, surveillance longue durée, injection, prélèvement, perfusion, pansement",
                "injection, prélèvement sanguin, pose de perfusion, pansements, vaccination, surveillance longue durée",
                cluster,
                communes[i % len(communes)],
                75 + (i % 20),
                f"IDE-DEMO-{i:03d}",
                "Donnée de démonstration",
            ),
        )

    # Pharmacies: 20
    for i in range(1, 21):
        cluster = clusters[(i - 1) % len(clusters)]
        titulaire = i  # first 20 agents are AS
        backups = ",".join(str(x) for x in range(1, 31) if (x - 1) % len(clusters) == (i - 1) % len(clusters) and x != titulaire)[:60]
        execute(
            """
            INSERT INTO pharmacies(nom_pharmacie, commune, quartier, cluster, niveau_activite,
                                   couverture_minimale, agent_titulaire, backups_autorises, statut, observations)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, 'active', ?)
            """,
            (
                f"Pharmacie Démo {i:02d}",
                cluster,
                f"Quartier {i}",
                cluster,
                ["faible", "moyen", "fort"][i % 3],
                titulaire,
                backups,
                "Donnée de démonstration",
            ),
        )

    today = date.today().isoformat()
    for agent_id in range(1, 31):
        statut = "disponible"
        if agent_id in (7, 14):
            statut = "astreinte"
        execute(
            "INSERT OR IGNORE INTO disponibilites(date, agent_id, statut_disponibilite) VALUES (?, ?, ?)",
            (today, agent_id, statut),
        )

    demandes = [
        (today, "Injection", "P1", "Cocody", "Angré", "Cocody", "demi-journée", "injection", "IDE", "injection", "moyen", "oui", "oui", "oui", "oui", "oui"),
        (today, "Prélèvement sanguin", "P2", "Plateau", "Centre", "Plateau", "demi-journée", "prélèvement", "IDE", "prélèvement sanguin", "moyen", "oui", "oui", "oui", "non", "oui"),
        (today, "Pose de perfusion", "P1", "Marcory", "Zone 4", "Marcory", "journée", "perfusion", "IDE", "pose de perfusion", "élevé", "oui", "oui", "oui", "oui", "oui"),
        (today, "Pansement complexe", "P2", "Yopougon", "Niangon", "Yopougon", "journée", "pansement", "IDE", "pansement complexe", "élevé", "oui", "oui", "oui", "non", "oui"),
        (today, "Surveillance longue durée", "P1", "Cocody", "Riviera", "Cocody", "garde 12h", "surveillance", "IDE", "surveillance longue durée", "élevé", "non", "non", "oui", "oui", "oui"),
        (today, "Surveillance simple", "P3", "Marcory", "Résidentiel", "Marcory", "journée", "surveillance", "AS", "surveillance simple", "faible", "non", "non", "oui", "non", "oui"),
        (today, "Garde à domicile non technique", "P3", "Yopougon", "Selmer", "Yopougon", "garde 12h", "garde", "AS", "garde non technique", "faible", "non", "non", "oui", "non", "oui"),
        (today, "Vaccination à domicile", "P4", "Plateau", "Indénié", "Plateau", "demi-journée", "vaccination", "IDE", "vaccination à domicile", "moyen", "oui", "oui", "oui", "oui", "oui"),
    ]
    for row in demandes:
        execute(
            """
            INSERT INTO demandes_umed(date_demande, type_mission, priorite, commune, quartier, cluster, duree_estimee,
                                      competence_requise, categorie_agent_requise, acte_requis, niveau_technicite,
                                      acte_infirmier, prescription_medicale_requise, prescription_medicale_disponible,
                                      validation_medecin_requise, validation_medecin_obtenue)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )


def level_from_score(score: int) -> tuple[str, float, str]:
    if score < 50:
        return "Rouge", 0.0, "restriction forte"
    if score < 70:
        return "Bronze", 0.0, "sous surveillance"
    if score < 85:
        return "Argent", 0.05, "actif"
    if score < 95:
        return "Or", 0.10, "prioritaire"
    return "Platine", 0.15, "réserve chaude"


def recompute_agent_scores(month: int, year: int) -> None:
    agents = query_df("SELECT id_agent, score_fiabilite FROM agents")
    for _, agent in agents.iterrows():
        positives = query_one(
            "SELECT COALESCE(SUM(points),0) AS s FROM point_transactions WHERE agent_id=? AND type_transaction='bonus' AND substr(date,1,7)=?",
            (int(agent.id_agent), f"{year:04d}-{month:02d}"),
        )["s"]
        negatives = query_one(
            "SELECT COALESCE(SUM(ABS(points)),0) AS s FROM point_transactions WHERE agent_id=? AND type_transaction='malus' AND substr(date,1,7)=?",
            (int(agent.id_agent), f"{year:04d}-{month:02d}"),
        )["s"]
        score_initial = int(agent.score_fiabilite or 80)
        score_final = max(0, min(100, score_initial + int(positives) - int(negatives)))
        niveau, bonus_percent, statut = level_from_score(score_final)
        execute(
            """
            INSERT INTO agent_scores(agent_id, mois, annee, score_initial, points_positifs, points_negatifs,
                                     score_final, niveau, bonus_percent, statut_operationnel)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_id, mois, annee) DO UPDATE SET
                score_initial=excluded.score_initial,
                points_positifs=excluded.points_positifs,
                points_negatifs=excluded.points_negatifs,
                score_final=excluded.score_final,
                niveau=excluded.niveau,
                bonus_percent=excluded.bonus_percent,
                statut_operationnel=excluded.statut_operationnel
            """,
            (int(agent.id_agent), month, year, score_initial, int(positives), int(negatives), score_final, niveau, bonus_percent, statut),
        )


def sanction_matrix(type_incident: str) -> dict[str, Any]:
    t = (type_incident or "").lower()
    rows = [
        ("retard de moins", "faible", "Avertissement oral", -5, "Perte bonus ponctualité du jour"),
        ("retard de plus", "modéré", "Avertissement écrit + rappel des obligations contractuelles", -15, "Perte bonus qualité du jour"),
        ("retard récurrent", "élevé", "Suspension de 3 jours de permanence", -40, "Jours de suspension non payés"),
        ("annulation récurrente", "très élevé", "Suspension d’un mois de permanence, voire résiliation", -100, "Suspension affectations rémunérées"),
        ("annulation", "élevé", "Suspension de 3 jours de permanence", -40, "Mission annulée non payée"),
        ("absence non justifiée récurrente", "très élevé", "Suspension d’un mois de permanence, voire résiliation", -100, "Suspension affectations rémunérées"),
        ("absence non justifiée", "élevé", "Suspension de 3 jours de permanence", -50, "Journée non payée + perte bonus mensuel"),
        ("vice de procédure", "très élevé", "Suspension d’un mois de permanence, voire résiliation", -100, "Gel bonus mensuel"),
        ("discourtoisie récurrente", "très élevé", "Suspension d’un mois de permanence, voire résiliation", -100, "Suspension affectations"),
        ("discourtoisie", "modéré", "Avertissement écrit + rappel du manuel interne", -15, "Perte éventuelle bonus comportement"),
        ("non-préparation récurrente", "très élevé", "Suspension d’un mois de permanence, voire résiliation", -100, "Suspension affectations"),
        ("non-préparation", "élevé", "Suspension de 3 jours de permanence", -40, "Perte bonus qualité/logistique"),
        ("mauvaise utilisation ou gestion récurrente du stock", "très élevé", "Suspension d’un mois de permanence, voire résiliation", -100, "Suspension + remboursement si applicable"),
        ("mauvaise utilisation ou gestion du stock", "élevé", "Remboursement selon modalités comptables", -40, "Remboursement validé"),
        ("mauvaise gestion récurrente des déchets", "très élevé", "Suspension d’un mois de permanence, voire résiliation", -100, "Suspension affectations"),
        ("mauvaise gestion des déchets", "élevé", "Suspension de 3 jours + formation", -40, "Jours de suspension non payés"),
        ("encaissements non déclarés", "très élevé", "Remboursement + pénalité 10% + suspension d’un mois, voire résiliation", -100, "Remboursement + pénalité 10%"),
        ("plainte mineure", "modéré", "Avertissement écrit + entretien Directeur Médical", -20, "Perte bonus satisfaction si confirmé"),
        ("erreur clinique ou erreur mineure répétée", "élevé", "Recyclage obligatoire avant reprise", -60, "Suspension missions jusqu’à formation validée"),
        ("erreur clinique grave", "très élevé", "Suspension d’un mois de permanence, voire résiliation", -100, "Suspension affectations"),
        ("plainte majeure", "très élevé", "Suspension d’un mois de permanence, voire résiliation", -100, "Suspension affectations"),
        ("protocole de soins sans", "très élevé", "Suspension d’un mois de permanence, voire résiliation", -100, "Gel bonus + suspension affectations"),
    ]
    for needle, gravite, sanction, points, impact in rows:
        if needle in t:
            return {"gravite": gravite, "sanction": sanction, "penalite_points": points, "impact_paie": impact}
    return {"gravite": "modéré", "sanction": "À décider par la Direction", "penalite_points": -10, "impact_paie": "À définir"}


if __name__ == "__main__":
    init_db()
    print(f"Database initialized: {DB_NAME}")
