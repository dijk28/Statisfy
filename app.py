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
    layout="centered"
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

# --- ZIJBALK VOOR INSTELLINGEN & API-FOOTBALL ---
st.sidebar.header("⚙️ API-Football Instellingen")
rapidapi_key = st.sidebar.text_input("RapidAPI Key", type="password", value="")

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Selecteer Competitie")
LEAGUES = {
    "Premier League (Engeland)": 39,
    "Eredivisie (Nederland)": 88,
    "Bundesliga (Duitsland)": 78,
    "La Liga (Spanje)": 140,
    "Serie A (Italië)": 135,
    "Champions League": 2,
    "Championship (Engeland 2e div)": 40,
    "2. Bundesliga (Duitsland 2e div)": 79,
    "Ligue 1 (Frankrijk)": 61,
    "Primeira Liga (Portugal)": 94,
    "Jupiler Pro League (België)": 144,
    "Serie B (Italië)": 136,
    "Segunda División (Spanje)": 141,
    "Eerste Divisie (Nederland 2e div)": 89,
    "Süper Lig (Turkije)": 203,
    "Super League (Zwitserland)": 207
}
selected_league_name = st.sidebar.selectbox("Kies competitie", list(LEAGUES.keys()))
league_id = LEAGUES[selected_league_name]
season = 2025 # Pas aan naar het actieve seizoen indien nodig

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Bankroll")
total_bankroll = st.sidebar.number_input("Totale Bankroll (€)", min_value=10.0, value=500.0, step=50.0)
unit_percentage = st.sidebar.slider("Inzet per Bet (% van Bankroll)", min_value=0.5, max_value=5.0, value=1.0, step=0.5)
unit_size = total_bankroll * (unit_percentage / 100.0)
st.sidebar.info(f"Standaard unit: **€{round(unit_size, 2)}** ({unit_percentage}%).")

if not rapidapi_key:
    st.warning("⚠️ Voer je RapidAPI Key in via de zijbalk om de data op te halen.")
else:
    # Gecachte API-functie met TTL op 24 uur (86400 seconden)
    @st.cache_data(ttl=86400)
    def get_api_football(endpoint, api_key, league_id, season, status=None, next_fixtures=None):
        url = f"https://api-football-v1.p.rapidapi.com/v3/{endpoint}"
        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
        }
        params = {"league": league_id, "season": season}
        if status:
            params["status"] = status
        if next_fixtures:
            params["next"] = next_fixtures

        response = requests.get(url, headers=headers, params=params)
        time.sleep(0.3)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            st.warning("⚠️ Dagelijkse limiet van API-Football bereikt (100 verzoeken).")
        return None

    if st.sidebar.button("🚀 Haal Data & Analyse op"):
        with st.spinner(f"Bezig met ophalen en analyseren van {selected_league_name} (24u cache)..."):
            
            # Data ophalen via de cache-functie
            standings_data = get_api_football("standings", rapidapi_key, league_id, season)
            fixtures_data = get_api_football("fixtures", rapidapi_key, league_id, season, status="FT")
            upcoming_data = get_api_football("fixtures", rapidapi_key, league_id, season, next_fixtures=10)

            master_shortlist = []

            if upcoming_data and "response" in upcoming_data:
                scheduled_matches = upcoming_data["response"]
                
                for match in scheduled_matches:
                    h = match["teams"]["home"]["name"]
                    a = match["teams"]["away"]["name"]
                    date = match["fixture"]["date"][:10]

                    # Poisson model berekening
                    lam_h, lam_a = 1.4, 1.2
                    total_lam = lam_h + lam_a
                    
                    max_g = 6
                    matrix = np.outer([poisson.pmf(i, lam_h) for i in range(max_g)], [poisson.pmf(j, lam_a) for j in range(max_g)])
                    p_over_25 = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if (i + j) > 2.5)
                    p_btts = sum(matrix[i, j] for i in range(1, max_g) for j in range(1, max_g))
                    p_home_win = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if i > j)

                    if p_btts >= 0.60:
                        master_shortlist.append({"Competitie": selected_league_name, "Categorie": "⚽ BTTS", "Datum": date, "Wedstrijd": f"{h} vs {a}", "Model": f"Kans: {int(p_btts*100)}%", "Fair Odd": round(1/p_btts, 2), "Inzet (€)": round(unit_size, 2), "Prob": p_btts})
                    if p_over_25 >= 0.60:
                        master_shortlist.append({"Competitie": selected_league_name, "Categorie": "🔥 Over 2.5", "Datum": date, "Wedstrijd": f"{h} vs {a}", "Model": f"Kans: {int(p_over_25*100)}%", "Fair Odd": round(1/p_over_25, 2), "Inzet (€)": round(unit_size, 2), "Prob": p_over_25})
                    if p_home_win >= 0.60:
                        master_shortlist.append({"Competitie": selected_league_name, "Categorie": "🏠 Thuiswinst", "Datum": date, "Wedstrijd": f"{h} vs {a}", "Model": f"Kans: {int(p_home_win*100)}%", "Fair Odd": round(1/p_home_win, 2), "Inzet (€)": round(unit_size, 2), "Prob": p_home_win})

            st.success("Analyse voltooid!")

            # --- RENDER SHORTLIST (MOBIELE KAARTEN) ---
            st.header(f"🏆 Shortlist: {selected_league_name}")
            if master_shortlist:
                df_short = pd.DataFrame(master_shortlist).sort_values(by="Prob", ascending=False)
                for _, row in df_short.iterrows():
                    with st.container(border=True):
                        st.caption(f"📅 {row['Datum']}")
                        st.markdown(f"### {row['Wedstrijd']}")
                        st.markdown(f"**{row['Categorie']}**")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Kans", row['Model'].split(":")[-1].strip())
                        c2.metric("Fair Odd", f"{row['Fair Odd']}")
                        c3.metric("Inzet", f"€{row['Inzet (€)']}")
            else:
                st.info("Geen wedstrijden gevonden die voldoen aan de >= 60% drempel voor deze selectie.")
