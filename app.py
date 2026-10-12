import streamlit as st
import requests
import pandas as pd
import numpy as np
from scipy.stats import poisson

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

# --- ZIJBALK VOOR INSTELLINGEN & FOOTBALL-DATA.ORG ---
st.sidebar.header("⚙️ API Instellingen")
api_key = st.sidebar.text_input("football-data.org API Key", type="password", value="")
st.sidebar.markdown("[Vraag hier gratis je key aan](https://www.football-data.org/)")

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Selecteer Competitie")
LEAGUES = {
    "Premier League (Engeland)": "PL",
    "Eredivisie (Nederland)": "ED",
    "Bundesliga (Duitsland)": "BL1",
    "La Liga (Spanje)": "PD",
    "Serie A (Italië)": "SA",
    "Champions League": "CL",
    "Championship (Engeland)": "ELC",
    "Ligue 1 (Frankrijk)": "FL1",
    "Primeira Liga (Portugal)": "PPL"
}
selected_league_name = st.sidebar.selectbox("Kies competitie", list(LEAGUES.keys()))
league_code = LEAGUES[selected_league_name]

if not api_key:
    st.warning("⚠️ Voer je gratis API-key van football-data.org in via de zijbalk om wedstrijden op te halen.")
else:
    # Gecachte API-functie met TTL op 24 uur (86400 seconden)
    @st.cache_data(ttl=86400)
    def get_football_data(code, key):
        url = f"https://api.football-data.org/v4/competitions/{code}/matches?status=SCHEDULED"
        headers = {"X-Auth-Token": key}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        return None

    if st.sidebar.button("🚀 Haal Data & Analyse op"):
        with st.spinner(f"Bezig met ophalen van speelschema voor {selected_league_name}..."):
            data = get_football_data(league_code, api_key)
            master_shortlist = []

            if data and "matches" in data:
                matches = data["matches"][:15] # Pak de komende wedstrijden
                
                for match in matches:
                    h = match["homeTeam"]["name"]
                    a = match["awayTeam"]["name"]
                    date = match["utcDate"][:10]

                    # Poisson model berekening op basis van verwachte doelpunten
                    lam_h, lam_a = 1.45, 1.15
                    max_g = 6
                    matrix = np.outer([poisson.pmf(i, lam_h) for i in range(max_g)], [poisson.pmf(j, lam_a) for j in range(max_g)])
                    p_over_25 = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if (i + j) > 2.5)
                    p_btts = sum(matrix[i, j] for i in range(1, max_g) for j in range(1, max_g))
                    p_home_win = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if i > j)

                    if p_btts >= 0.55:
                        master_shortlist.append({"Competitie": selected_league_name, "Categorie": "⚽ BTTS", "Datum": date, "Wedstrijd": f"{h} vs {a}", "Model": f"Kans: {int(p_btts*100)}%", "Fair Odd": round(1/p_bitts, 2), "Prob": p_btts})
                    if p_over_25 >= 0.55:
                        master_shortlist.append({"Competitie": selected_league_name, "Categorie": "🔥 Over 2.5", "Datum": date, "Wedstrijd": f"{h} vs {a}", "Model": f"Kans: {int(p_over_25*100)}%", "Fair Odd": round(1/p_over_25, 2), "Prob": p_over_25})
                    if p_home_win >= 0.55:
                        master_shortlist.append({"Competitie": selected_league_name, "Categorie": "🏠 Thuiswinst", "Datum": date, "Wedstrijd": f"{h} vs {a}", "Model": f"Kans: {int(p_home_win*100)}%", "Fair Odd": round(1/p_home_win, 2), "Prob": p_home_win})

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
                        c1, c2 = st.columns(2)
                        c1.metric("Kans", row['Model'].split(":")[-1].strip())
                        c2.metric("Fair Odd", f"{row['Fair Odd']}")
            else:
                st.info("Geen wedstrijden gevonden die voldoen aan de drempel voor deze selectie.")
