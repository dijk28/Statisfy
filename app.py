import streamlit as st
import requests
import pandas as pd
import numpy as np
from scipy.stats import poisson
import time

# Pagina configuratie & mobiele optimalisatie
st.set_page_config(
    page_title="Statisfy - Betting Assistant",
    page_icon="⚽",
    layout="wide"
)

# Custom CSS voor native app look
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

# --- ZIJBALK VOOR INSTELLINGEN & BANKROLL ---
st.sidebar.header("⚙️ Instellingen & Bankroll")
api_key_input = st.sidebar.text_input("Football-Data.org API Key", type="password", value="ccd41811b56d4cf6bb944d2a5d5286f7")

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Bankroll Management")
total_bankroll = st.sidebar.number_input("Totale Bankroll (€)", min_value=10.0, value=500.0, step=50.0)
unit_percentage = st.sidebar.slider("Inzet per Bet (% van Bankroll)", min_value=0.5, max_value=5.0, value=1.0, step=0.5)
unit_size = total_bankroll * (unit_percentage / 100.0)
st.sidebar.info(f"Standaard unit: **€{round(unit_size, 2)}** ({unit_percentage}%).")

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
selected_league_name = st.sidebar.selectbox("Kies competitie om te analyseren", list(LEAGUES.keys()))
league_code = LEAGUES[selected_league_name]

if not api_key_input:
    st.warning("⚠️ Voer je API-key in via de zijbalk aan de linkerkant om de analyse te starten.")
else:
    BASE_URL = "https://api.football-data.org/v4/"

    # Gecachte API-functie met 24-uurs TTL om binnen de gratis limiet te blijven
    @st.cache_data(ttl=86400, show_spinner=False)
    def get_api_data(endpoint, api_key):
        headers = {"X-Auth-Token": api_key}
        url = f"{BASE_URL}{endpoint}"
        response = requests.get(url, headers=headers)
        time.sleep(0.5)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            return "RATE_LIMIT"
        return None

    if st.sidebar.button("🚀 Start Analyse"):
        with st.spinner(f"Bezig met het ophalen en analyseren van {selected_league_name}..."):
            master_shortlist = []
            evaluation_results = []
            league_top_players = {}

            # 1. Spelerstatistieken ophalen
            scorers_data = get_api_data(f"competitions/{league_code}/scorers?limit=3", api_key_input)
            if scorers_data == "RATE_LIMIT":
                st.error("⚠️ API-limiet bereikt (max 10 verzoeken per minuut). Wacht even een minuutje en probeer het opnieuw.")
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

            # 2. Wedstrijddata ophalen
            match_data = get_api_data(f"competitions/{league_code}/matches", api_key_input)
            if match_data == "RATE_LIMIT":
                st.error("⚠️ API-limiet bereikt. Wacht even een minuutje en probeer het opnieuw.")
                st.stop()

            if match_data and isinstance(match_data, dict) and "matches" in match_data:
                matches = match_data["matches"]
                finished_matches = [m for m in matches if m["status"] == "FINISHED"]
                scheduled = [m for m in matches if m["status"] in ["SCHEDULED", "TIMED"]]
                
                if finished_matches:
                    finished_sorted = sorted(finished_matches, key=lambda x: x["utcDate"])

                    season_stats = {}
                    team_match_history = {}
                    min_games = 1  # Versoepeld naar 1 wedstrijd

                    # Gespeelde wedstrijden verwerken voor statistieken & evaluatie (Drempel: 55%)
                    for m in finished_sorted:
                        home = m["homeTeam"]["name"]
                        away = m["awayTeam"]["name"]
                        date = m["utcDate"][:10]
                        ft = m["score"]["fullTime"]
                        hg, ag = ft["home"], ft["away"]
                        if hg is None or ag is None: continue

                        h_stat = season_stats.get(home)
                        a_stat = season_stats.get(away)

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

                            for cat, prob, did_win in evals_to_
