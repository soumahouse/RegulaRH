"""Planning algorithm for REGULA-RH Vaccipha x Umed."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from database import bool_setting, execute, get_settings, query_df

IDE_ACTS = {
    "injection",
    "prélèvement sanguin",
    "prelevement sanguin",
    "pose de perfusion",
    "perfusion",
    "pansement complexe",
    "vaccination à domicile",
    "vaccination a domicile",
}

PRIORITY_RANK = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}


def _alert(date_str: str, level: str, kind: str, message: str) -> None:
    execute(
        "INSERT INTO alertes(date, niveau, type_alerte, message) VALUES (?, ?, ?, ?)",
        (date_str, level, kind, message),
    )


def _to_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"oui", "yes", "true", "1"}


def _as_list(text: Any) -> list[int]:
    if text is None or pd.isna(text):
        return []
    out = []
    for part in str(text).replace(";", ",").split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out


def _active_agents(date_str: str) -> pd.DataFrame:
    agents = query_df(
        """
        SELECT a.*, COALESCE(d.statut_disponibilite, 'disponible') AS disponibilite
        FROM agents a
        LEFT JOIN disponibilites d ON d.agent_id = a.id_agent AND d.date = ?
        WHERE a.statut NOT IN ('suspendu', 'à recycler')
        """,
        (date_str,),
    )
    if agents.empty:
        return agents
    allowed = {"disponible", "astreinte", "réserve chaude", "reserve chaude", "réserve tiède", "reserve tiede", "réserve froide", "reserve froide"}
    return agents[agents["disponibilite"].str.lower().isin(allowed)].copy()


def _recent_confirmed_incidents(agent_id: int, days_label: str = "") -> pd.DataFrame:
    # MVP: use all confirmed or sanctioned incidents; future version may filter by date window.
    return query_df(
        """
        SELECT * FROM incidents
        WHERE agent_id=? AND statut_traitement IN ('confirmé', 'sanction appliquée', 'clôturé')
        """,
        (agent_id,),
    )


def _has_blocking_incident(agent_id: int, mission: pd.Series) -> tuple[bool, str]:
    incidents = _recent_confirmed_incidents(agent_id)
    if incidents.empty:
        # Also block clinical sensitive missions if there is an elevated incident under investigation.
        in_progress = query_df(
            """
            SELECT * FROM incidents
            WHERE agent_id=? AND statut_traitement IN ('signalé','en cours d’instruction','demande d’explication envoyée')
              AND gravite IN ('élevé','très élevé')
            """,
            (agent_id,),
        )
        if not in_progress.empty and _to_bool(mission.get("acte_infirmier", "non")):
            return True, "Incident élevé/très élevé en cours d'instruction sur mission clinique sensible"
        return False, ""

    for _, inc in incidents.iterrows():
        t = str(inc.get("type_incident", "")).lower()
        g = str(inc.get("gravite", "")).lower()
        if "erreur clinique" in t or "plainte majeure" in t or "protocole" in t:
            return True, "Incident médical bloquant confirmé"
        if "mauvaise gestion des déchets" in t and _to_bool(mission.get("acte_infirmier", "non")):
            return True, "Formation DASRI requise avant mission clinique"
        if "non-préparation" in t and _to_bool(mission.get("acte_infirmier", "non")):
            return True, "Restriction mission autonome après incident sac d'intervention"
        if g == "très élevé":
            return True, "Incident très élevé confirmé"
    return False, ""


def _mission_requires_ide(mission: pd.Series) -> bool:
    required = str(mission.get("categorie_agent_requise", "")).upper() == "IDE"
    acte = str(mission.get("acte_requis", "")).strip().lower()
    type_mission = str(mission.get("type_mission", "")).strip().lower()
    acte_infirmier = _to_bool(mission.get("acte_infirmier", "non"))
    return required or acte_infirmier or acte in IDE_ACTS or type_mission in IDE_ACTS


def _blocked_by_missing_medical_validation(mission: pd.Series, settings: dict[str, str]) -> tuple[bool, str]:
    if bool_setting(settings, "bloquer_acte_IDE_si_prescription_absente", True):
        if _to_bool(mission.get("prescription_medicale_requise", "non")) and not _to_bool(mission.get("prescription_medicale_disponible", "non")):
            return True, "Prescription médicale manquante"
    if bool_setting(settings, "bloquer_acte_IDE_si_validation_medecin_absente", True):
        if _to_bool(mission.get("validation_medecin_requise", "non")) and not _to_bool(mission.get("validation_medecin_obtenue", "non")):
            return True, "Validation médicale requise"
    return False, ""


def _eligible_for_pharmacy(agent: pd.Series) -> bool:
    if str(agent.get("habilitation_vaccipha", "non")).lower() != "oui":
        return False
    if str(agent.get("statut", "")).lower() in {"suspendu", "à recycler"}:
        return False
    return True


def _eligible_for_mission(agent: pd.Series, mission: pd.Series) -> tuple[bool, str]:
    if str(agent.get("statut", "")).lower() in {"suspendu", "à recycler"}:
        return False, "Agent suspendu ou à recycler"
    if str(agent.get("categorie_agent", "")).upper() == "AS" and _mission_requires_ide(mission):
        return False, "Acte infirmier réservé à IDE"
    if _mission_requires_ide(mission):
        if str(agent.get("categorie_agent", "")).upper() != "IDE":
            return False, "IDE requis"
        if str(agent.get("habilitation_actes_infirmiers", "non")).lower() != "oui":
            return False, "Habilitation actes infirmiers manquante"
        if str(agent.get("habilitation_soins_domicile", "non")).lower() != "oui":
            return False, "Habilitation soins à domicile manquante"
    else:
        # Non-technical home care still needs home-care authorization.
        if "domicile" in str(mission.get("type_mission", "")).lower() and str(agent.get("habilitation_soins_domicile", "non")).lower() != "oui":
            return False, "Habilitation soins à domicile manquante"
    blocked, reason = _has_blocking_incident(int(agent.id_agent), mission)
    if blocked:
        return False, reason
    if int(agent.get("score_fiabilite", 80) or 80) < 50 and str(mission.get("priorite", "")).upper() in {"P1", "P2"}:
        return False, "Score faible non éligible P1/P2"
    return True, ""


def _level_bonus(score: int) -> tuple[str, int]:
    if score < 50:
        return "Rouge", -999
    if score < 70:
        return "Bronze", -10
    if score < 85:
        return "Argent", 2
    if score < 95:
        return "Or", 5
    return "Platine", 10


def _score_pharmacy(agent: pd.Series, pharmacy: pd.Series, settings: dict[str, str], remaining_ide_by_cluster: dict[str, int], reserve_ide_by_cluster: dict[str, int]) -> float:
    score = 0.0
    agent_id = int(agent.id_agent)
    if agent_id == int(pharmacy.get("agent_titulaire") or -1):
        score += 40
    else:
        score += 20
    if str(agent.get("cluster_principal", "")) == str(pharmacy.get("cluster", "")):
        score += 15
    if str(agent.get("categorie_agent", "")).upper() == "AS":
        score += 15 if bool_setting(settings, "prioriser_AS_pour_pharmacie", True) else 0
    elif str(agent.get("categorie_agent", "")).upper() == "IDE":
        if not bool_setting(settings, "autoriser_IDE_sur_poste_pharmacie", True):
            return -999
        cluster = str(agent.get("cluster_principal", ""))
        if remaining_ide_by_cluster.get(cluster, 0) <= reserve_ide_by_cluster.get(cluster, 0):
            score -= 30
        score -= 5
    score += min(15, int(agent.get("score_fiabilite", 80) or 80) / 100 * 15)
    _, lb = _level_bonus(int(agent.get("score_fiabilite", 80) or 80))
    score += max(lb, -20)
    # Authorized back-up bonus.
    if agent_id in _as_list(pharmacy.get("backups_autorises")):
        score += 10
    return score


def _score_mission(agent: pd.Series, mission: pd.Series, already_used: set[int]) -> float:
    if int(agent.id_agent) in already_used:
        return -999
    ok, _ = _eligible_for_mission(agent, mission)
    if not ok:
        return -999
    score = 0.0
    requires_ide = _mission_requires_ide(mission)
    cat = str(agent.get("categorie_agent", "")).upper()
    score += 25  # competence baseline after eligibility
    if requires_ide and cat == "IDE":
        score += 20
    elif not requires_ide and cat == "AS":
        score += 10  # economic adequacy
    elif not requires_ide and cat == "IDE":
        score -= 5
    if str(agent.get("cluster_principal", "")) == str(mission.get("cluster", "")):
        score += 10
    score += 10  # availability baseline
    score += min(10, int(agent.get("score_fiabilite", 80) or 80) / 100 * 10)
    _, lb = _level_bonus(int(agent.get("score_fiabilite", 80) or 80))
    score += max(lb, -20)
    # Economic efficiency: lower cost for simple missions.
    if not requires_ide and cat == "AS":
        score += 5
    if requires_ide and str(mission.get("priorite", "")).upper() in {"P1", "P2"} and cat == "IDE":
        score += 10
    return score


def _add_planning(date_str: str, agent: pd.Series, affectation_type: str, affectation_id: int | None, label: str, cluster: str, priority: str | None, score: float, observations: str = "") -> None:
    execute(
        """
        INSERT INTO planning(date, agent_id, categorie_agent, profession, affectation_type, affectation_id,
                             affectation_label, cluster, priorite_mission, cout_journalier, score_affectation, observations)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            date_str,
            int(agent.id_agent),
            str(agent.get("categorie_agent", "")),
            str(agent.get("profession", "")),
            affectation_type,
            affectation_id,
            label,
            cluster,
            priority,
            int(agent.get("cout_journalier_total", 0) or 0),
            float(score),
            observations,
        ),
    )


def _mark_agent_used(used: set[int], agent: pd.Series, remaining_ide_by_cluster: dict[str, int]) -> None:
    used.add(int(agent.id_agent))
    if str(agent.get("categorie_agent", "")).upper() == "IDE":
        cluster = str(agent.get("cluster_principal", ""))
        remaining_ide_by_cluster[cluster] = max(0, remaining_ide_by_cluster.get(cluster, 0) - 1)


def generate_daily_planning(date_str: str) -> dict[str, Any]:
    """Generate daily planning and cost summary for selected ISO date."""
    settings = get_settings()

    # Reset generated artifacts for the day.
    execute("DELETE FROM planning WHERE date=?", (date_str,))
    execute("DELETE FROM alertes WHERE date=?", (date_str,))
    execute("DELETE FROM couts_journaliers WHERE date=?", (date_str,))

    pharmacies = query_df("SELECT * FROM pharmacies WHERE statut='active'")
    demandes = query_df(
        """
        SELECT * FROM demandes_umed
        WHERE date_demande<=? AND statut IN ('en attente','affectée')
        ORDER BY CASE priorite WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 WHEN 'P3' THEN 3 ELSE 4 END, id_demande
        """,
        (date_str,),
    )
    agents = _active_agents(date_str)
    used: set[int] = set()

    if agents.empty:
        _alert(date_str, "critique", "Aucun agent", "Aucun agent disponible pour la date sélectionnée.")
        return {"status": "no_agents"}

    # Compute IDE demand and reserve by cluster.
    ide_required_clusters: dict[str, int] = {}
    blocked_demands = set()
    for _, m in demandes.iterrows():
        blocked, reason = _blocked_by_missing_medical_validation(m, settings)
        if blocked:
            blocked_demands.add(int(m.id_demande))
            _alert(date_str, "critique", reason, f"Demande Umed #{int(m.id_demande)} bloquée : {reason}.")
            continue
        if _mission_requires_ide(m):
            cl = str(m.get("cluster", ""))
            ide_required_clusters[cl] = ide_required_clusters.get(cl, 0) + 1

    reserve_min = int(settings.get("reserve_minimale_IDE_par_cluster", "1") or 1)
    reserve_ide_by_cluster = {cluster: reserve_min for cluster in ide_required_clusters.keys()}
    remaining_ide_by_cluster = {}
    for _, a in agents[agents["categorie_agent"].str.upper() == "IDE"].iterrows():
        cl = str(a.get("cluster_principal", ""))
        remaining_ide_by_cluster[cl] = remaining_ide_by_cluster.get(cl, 0) + 1

    # Step 1: cover pharmacies.
    for _, pharmacy in pharmacies.iterrows():
        candidates = agents[~agents["id_agent"].isin(list(used))].copy()
        candidates = candidates[candidates.apply(_eligible_for_pharmacy, axis=1)]
        if candidates.empty:
            _alert(date_str, "critique", "Pharmacie non couverte", f"{pharmacy.nom_pharmacie} non couverte : aucun agent habilité disponible.")
            continue
        candidates["_score"] = candidates.apply(
            lambda a: _score_pharmacy(a, pharmacy, settings, remaining_ide_by_cluster, reserve_ide_by_cluster),
            axis=1,
        )
        candidates = candidates[candidates["_score"] > -100]
        if candidates.empty:
            _alert(date_str, "critique", "Réserve IDE non respectée", f"{pharmacy.nom_pharmacie} non couverte : uniquement IDE protégés par réserve.")
            continue
        chosen = candidates.sort_values("_score", ascending=False).iloc[0]
        _add_planning(
            date_str,
            chosen,
            "pharmacie",
            int(pharmacy.id_pharmacie),
            str(pharmacy.nom_pharmacie),
            str(pharmacy.cluster),
            None,
            float(chosen["_score"]),
        )
        _mark_agent_used(used, chosen, remaining_ide_by_cluster)

    # Step 2: Umed missions by priority and IDE requirement.
    if not demandes.empty:
        demandes = demandes.copy()
        demandes["_rank"] = demandes["priorite"].map(PRIORITY_RANK).fillna(9)
        demandes["_ide_required"] = demandes.apply(_mission_requires_ide, axis=1)
        demandes = demandes.sort_values(["_rank", "_ide_required"], ascending=[True, False])

    for _, mission in demandes.iterrows():
        if int(mission.id_demande) in blocked_demands:
            continue
        candidates = agents[~agents["id_agent"].isin(list(used))].copy()
        if not candidates.empty:
            candidates["_score"] = candidates.apply(lambda a: _score_mission(a, mission, used), axis=1)
            candidates = candidates[candidates["_score"] > -100]
        if candidates.empty:
            # Try permutation: redploy IDE from pharmacy if an AS/backup can cover the pharmacy.
            if _mission_requires_ide(mission) and str(mission.get("priorite", "")).upper() in {"P1", "P2"}:
                _alert(date_str, "critique", "IDE indisponible", f"Aucun IDE libre pour demande Umed #{int(mission.id_demande)}. Permutation manuelle possible si back-up pharmacie disponible.")
            else:
                _alert(date_str, "élevé", "Mission non affectée", f"Aucun agent éligible pour demande Umed #{int(mission.id_demande)}.")
            continue
        chosen = candidates.sort_values("_score", ascending=False).iloc[0]
        _add_planning(
            date_str,
            chosen,
            "mission Umed",
            int(mission.id_demande),
            str(mission.type_mission),
            str(mission.cluster),
            str(mission.priorite),
            float(chosen["_score"]),
            observations=str(mission.get("acte_requis", "")),
        )
        _mark_agent_used(used, chosen, remaining_ide_by_cluster)
        execute("UPDATE demandes_umed SET statut='affectée', agent_affecte=? WHERE id_demande=?", (int(chosen.id_agent), int(mission.id_demande)))

    _compute_daily_cost(date_str)
    return {"status": "ok", "agents_used": len(used)}


def _compute_daily_cost(date_str: str) -> None:
    df = query_df("SELECT * FROM planning WHERE date=?", (date_str,))
    if df.empty:
        execute(
            "INSERT INTO couts_journaliers(date) VALUES (?)",
            (date_str,),
        )
        return
    as_df = df[df["categorie_agent"].str.upper() == "AS"]
    ide_df = df[df["categorie_agent"].str.upper() == "IDE"]
    n_as = len(as_df)
    n_ide = len(ide_df)
    total_as = int(as_df["cout_journalier"].sum()) if n_as else 0
    total_ide = int(ide_df["cout_journalier"].sum()) if n_ide else 0
    # split transport/taux according to categories.
    total_taux_as = n_as * 5000
    total_transport_as = n_as * 1000
    total_taux_ide = n_ide * 10000
    total_transport_ide = n_ide * 1000
    covered_pharmacies = int((df["affectation_type"] == "pharmacie").sum())
    missions = int((df["affectation_type"] == "mission Umed").sum())
    total = total_as + total_ide
    avg = total / len(df) if len(df) else 0
    execute(
        """
        INSERT INTO couts_journaliers(date, nombre_as_mobilises, nombre_ide_mobilises,
                                      total_taux_journalier_as, total_transport_as,
                                      total_taux_journalier_ide, total_transport_ide,
                                      cout_total, nombre_pharmacies_couvertes, nombre_missions_umed,
                                      cout_moyen_par_affectation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (date_str, n_as, n_ide, total_taux_as, total_transport_as, total_taux_ide, total_transport_ide, total, covered_pharmacies, missions, avg),
    )


if __name__ == "__main__":
    from database import init_db, load_demo_data
    from datetime import date

    init_db()
    load_demo_data()
    print(generate_daily_planning(date.today().isoformat()))
