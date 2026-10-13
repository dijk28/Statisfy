import streamlit as st
import requests
import pandas as pd
import numpy as np
from scipy.stats import poisson
import time

# Pagina configuratie
st.set_page_config(
    page_title="Statisfy - Betting Assistant",
    page_icon="⚽",
    layout="wide"
)

# Custom CSS voor native app look & mobiele optimalisatie
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        /* Extra mobiele optimalisaties */
        @media (max-width: 768px) {
            .block-container {
                padding-top: 0.5rem;
                padding-left: 0.5rem;
                padding-right: 0.5rem;
            }
            h1 { font-size: 1.5rem !important; }
            h2 { font-size: 1.3rem !important; }
            h3 { font-size: 1.1rem !important; }
        }
    </style>
""", unsafe_allow_html=True)

# --- STATISFY LOGO ---
logo_html = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 150" width="100%" height="100%">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#2ECC71;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#3498DB;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="500" height="150" rx="20" fill="#0E1117"/>
  <g transform="translate(30, 25)">
    <circle cx="50" cy="50" r="45" fill="none" stroke="url(#grad)" stroke-width="5" opacity="0.25"/>
    <rect x="30" y="55" width="10" height="20" rx="3" fill="#2ECC71"/>
    <rect x="45" y="35" width="10" height="40" rx="3" fill="#3498DB"/>
    <rect x="60" y="20" width="10" height="55" rx="3" fill="#2ECC71"/>
    <polyline points="35,50 50,30 65,15" fill="none" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="65" cy="15" r="4" fill="#FFFFFF"/>
  </g>
  <text x="145" y="92" font-family="system-ui, -apple-system, sans-serif" font-size="52" font-weight="800" fill="#FFFFFF">Stat<tspan fill="#2ECC71">isfy</tspan></text>
  <text x="148" y="118" font-family="system-ui, -apple-system, sans-serif" font-size="13" font-weight="500" fill="#8892B0" letter-spacing="2.5">DATA-DRIVEN BETTING</text>
</svg>
"""
st.markdown(logo_html, unsafe_allow_html=True)
st.markdown("---")

# --- ZIJBALK VOOR API KEY & COMPETITIE SELECTIE ---
st.sidebar.header("⚙️ Instellingen")
api_key_input = st.sidebar.text_input("Football-Data.org API Key", type="password", value="ccd41811b56d4cf6bb944d2a5d5286f7")

LEAGUES = {
    "Premier League": "PL",
    "Championship": "ELC",
    "Eredivisie": "DED",
    "Bundesliga 1": "BL1",
    "Bundesliga 2": "BL2",
    "La Liga": "PD",
    "Serie A": "SA",
    "Swiss Super League": "SSL",
    "Champions League": "CL",
    "Europa League": "EL"
}

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Selecteer Competitie")
selected_league_name = st.sidebar.selectbox("Kies competitie", list(LEAGUES.keys()))
league_code = LEAGUES[selected_league_name]

if not api_key_input:
    st.warning("⚠️ Voer je API-key in via de zijbalk aan de linkerkant om de analyse te starten.")
else:
    BASE_URL = "https://api.football-data.org/v4/"

    # Gecachte API-functie om binnen de gratis limiet (10 req/min) te blijven
    @st.cache_data(ttl=86400, show_spinner=False)
    def get_api_data_cached(endpoint, api_key):
        url = f"{BASE_URL}{endpoint}"
        resp_headers = {"X-Auth-Token": api_key}
        response = requests.get(url, headers=resp_headers)
        time.sleep(0.5)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            return "RATE_LIMIT"
        return None

    if st.sidebar.button("🚀 Start Analyse"):
        # Duidelijke laad-indicator met spinner
        with st.spinner(f"🔄 Bezig met berekenen en ophalen van data voor {selected_league_name}... Even geduld aub."):
            master_shortlist = []
            evaluation_results = []
            league_top_players = {}

            # 1. Spelerstatistieken ophalen voor de gekozen competitie
            scorers_data = get_api_data_cached(f"competitions/{league_code}/scorers?limit=3", api_key_input)
            if scorers_data == "RATE_LIMIT":
                st.error("⚠️ Te veel verzoeken naar de API tegelijk. Wacht even een minuutje en probeer opnieuw.")
                st.stop()
            
            if scorers_data and isinstance(scorers_data, dict) and "scorers" in scorers_data and scorers_data["scorers"]:
                top_p = []
                for scorer in scorers_data["scorers"]:
                    top_p.append({
                        "Speler": scorer["player"]["name"],
                        "Team": scorer["team"]["name"],
                        "Goals": scorer.get("goals", 0),
                        "Assists": scorer.get("assists", 0)
                    })
                league_top_players[selected_league_name] = top_p

            # 2. Wedstrijddata ophalen voor de gekozen competitie
            match_data = get_api_data_cached(f"competitions/{league_code}/matches", api_key_input)
            if match_data == "RATE_LIMIT":
                st.error("⚠️ Te veel verzoeken naar de API tegelijk. Wacht even een minuutje en probeer opnieuw.")
                st.stop()
            
            if not match_data or not isinstance(match_data, dict) or "matches" not in match_data:
                st.error(f"⚠️ Kon geen wedstrijddata ophalen voor {selected_league_name}.")
            else:
                matches = match_data["matches"]
                finished_matches = [m for m in matches if m["status"] == "FINISHED"]
                scheduled = [m for m in matches if m["status"] in ["SCHEDULED", "TIMED"]]
                
                if finished_matches:
                    finished_sorted = sorted(finished_matches, key=lambda x: x["utcDate"])

                    season_stats = {}
                    team_match_history = {}

                    # Eerst alle gespeelde wedstrijden verwerken voor statistieken & evaluatie
                    for idx, m in enumerate(finished_sorted):
                        home = m["homeTeam"]["name"]
                        away = m["awayTeam"]["name"]
                        date = m["utcDate"][:10]
                        ft = m["score"]["fullTime"]
                        hg, ag = ft["home"], ft["away"]
                        if hg is None or ag is None: continue

                        h_stat = season_stats.get(home)
                        a_stat = season_stats.get(away)
                        min_games = 1 if league_code in ["CL", "EL"] else 3

                        # Als teams genoeg data hebben, kunnen we achteraf evalueren of het model gelijk had
                        if h_stat and a_stat and h_stat["played"] >= min_games and a_stat["played"] >= min_games:
                            season_lam_h = max(0.5, ((h_stat["gf"] / h_stat["played"]) + (h_stat["ga"] / h_stat["played"])) / 2)
                            season_lam_a = max(0.5, ((a_stat["gf"] / a_stat["played"]) + (a_stat["ga"] / a_stat["played"])) / 2)

                            h_history = team_match_history.get(home, [])[-5:]
                            a_history = team_match_history.get(away, [])[-5:]
                            
                            if len(h_history) > 0 and len(a_history) > 0:
                                h_form_gf = sum([x["scored"] for x in h_history]) / len(h_history)
                                h_form_ga = sum([x["conceded"] for x in h_history]) / len(h_history)
                                a_form_gf = sum([x["scored"] for x in a_history]) / len(a_history)
                                a_form_ga = sum([x["conceded"] for x in a_history]) / len(a_history)
                                
                                form_lam_h = max(0.5, (h_form_gf + a_form_ga) / 2)
                                form_lam_a = max(0.5, (a_form_gf + h_form_ga) / 2)
                            else:
                                form_lam_h, form_lam_a = season_lam_h, season_lam_h

                            lam_h = (0.6 * form_lam_h) + (0.4 * season_lam_h)
                            lam_a = (0.6 * form_lam_a) + (0.4 * season_lam_a)
                            
                            max_g = 6
                            matrix = np.outer([poisson.pmf(i, lam_h) for i in range(max_g)], [poisson.pmf(j, lam_a) for j in range(max_g)])
                            
                            p_home_win = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if i > j)
                            p_over_25 = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if (i + j) > 2.5)
                            p_under_25 = 1 - p_over_25
                            p_btts = sum(matrix[i, j] for i in range(1, max_g) for j in range(1, max_g))

                            actual_total_goals = hg + ag
                            actual_home_win = 1 if hg > ag else 0
                            actual_btts = 1 if (hg > 0 and ag > 0) else 0

                            evals_to_check = [
                                ("⚽ BTTS", p_btts, actual_btts == 1),
                                ("🔥 Over 2.5", p_over_25, actual_total_goals > 2.5),
                                ("🏠 Thuiswinst", p_home_win, actual_home_win == 1),
                                ("🛡️ Under 2.5", p_under_25, actual_total_goals < 2.5)
                            ]

                            for cat, prob, did_win in evals_to_check:
                                if prob >= 0.60:
                                    evaluation_results.append({
                                        "Competitie": selected_league_name,
                                        "Datum": date,
                                        "Wedstrijd": f"{home} vs {away}",
                                        "Categorie": cat,
                                        "Model Kans": f"{int(prob*100)}%",
                                        "Echte Uitslag": f"{hg} - {ag}",
                                        "Status": "✅ GOED" if did_win else "❌ FOUT",
                                        "Win_Bool": did_win
                                    })

                        # Seizoensstats & historie bijwerken voor volgende iteratie
                        for team, scored, conceded in [(home, hg, ag), (away, ag, hg)]:
                            if team not in season_stats:
                                season_stats[team] = {"played": 0, "gf": 0, "ga": 0}
                            season_stats[team]["played"] += 1
                            season_stats[team]["gf"] += scored
                            season_stats[team]["ga"] += conceded

                        if home not in team_match_history: team_match_history[home] = []
                        if away not in team_match_history: team_match_history[away] = []
                        team_match_history[home].append({"scored": hg, "conceded": ag})
                        team_match_history[away].append({"scored": ag, "conceded": hg})

                # 3. Komende wedstrijden analyseren voor de Shortlist (Mainpage)
                if scheduled:
                    next_matchday = scheduled[0]["matchday"]
                    next_round = [m for m in scheduled if m["matchday"] == next_matchday]

                    for m in next_round:
                        h = m["homeTeam"]["name"]
                        a = m["awayTeam"]["name"]
                        date = m["utcDate"][:10]
                        
                        h_stat = season_stats.get(h)
                        a_stat = season_stats.get(a)
                        min_games = 1 if league_code in ["CL", "EL"] else 3
                        
                        if not h_stat or not a_stat or h_stat["played"] < min_games or a_stat["played"] < min_games:
                            continue
                            
                        season_lam_h = max(0.5, ((h_stat["gf"] / h_stat["played"]) + (h_stat["ga"] / h_stat["played"])) / 2)
                        season_lam_a = max(0.5, ((a_stat["gf"] / a_stat["played"]) + (a_stat["ga"] / a_stat["played"])) / 2)

                        h_history = team_match_history.get(h, [])[-5:]
                        a_history = team_match_history.get(a, [])[-5:]
                        
                        if len(h_history) > 0 and len(a_history) > 0:
                            h_form_gf = sum([x["scored"] for x in h_history]) / len(h_history)
                            h_form_ga = sum([x["conceded"] for x in h_history]) / len(h_history)
                            a_form_gf = sum([x["scored"] for x in a_history]) / len(a_history)
                            a_form_ga = sum([x["conceded"] for x in a_history]) / len(a_history)
                            
                            form_lam_h = max(0.5, (h_form_gf + a_form_ga) / 2)
                            form_lam_a = max(0.5, (a_form_gf + h_form_ga) / 2)
                        else:
                            form_lam_h, form_lam_a = season_lam_h, season_lam_h

                        lam_h = (0.6 * form_lam_h) + (0.4 * season_lam_h)
                        lam_a = (0.6 * form_lam_a) + (0.4 * season_lam_a)
                        total_lam = lam_h + lam_a  # Volledig uitgeschreven
                        
                        max_g = 6
                        matrix = np.outer([poisson.pmf(i, lam_h) for i in range(max_g)], [poisson.pmf(j, lam_a) for j in range(max_g)])
                        
                        p_home_win = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if i > j)
                        p_over_25 = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if (i + j) > 2.5)
                        p_under_25 = 1 - p_over_25
                        p_btts = sum(matrix[i, j] for i in range(1, max_g) for j in range(1, max_g))

                        form_sample_h = len(h_history)
                        if league_code in ["CL", "EL"]:
                            data_label = f"⚠️ Beperkt (Europa: {form_sample_h}d)"
                        else:
                            data_label = f"Vorm ({form_sample_h}v/{h_stat['played']}s duels)"

                        if p_btts >= 0.60:
                            master_shortlist.append({"Competitie": selected_league_name, "Categorie": "⚽ BTTS (Beide Teams Scoren)", "Datum": date, "Wedstrijd": f"{h} vs {a}", "Indicatie / Model": f"Kans op doelpunten beide kanten: {int(p_btts*100)}%", "Fair Odd": round(1 / p_btts, 2), "Data Basis": data_label, "Prob_Val": p_btts})
                        if p_over_25 >= 0.60:
                            master_shortlist.append({"Competitie": selected_league_name, "Categorie": "🔥 Doelpunten (Over 2.5)", "Datum": date, "Wedstrijd": f"{h} vs {a}", "Indicatie / Model": f"Verw
