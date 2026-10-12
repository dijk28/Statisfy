import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import random

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

# --- ZIJBALK VOOR INSTELLINGEN ---
st.sidebar.header("⚙️ Statisfy Instellingen")
demo_mode = st.sidebar.checkbox("🚀 Gebruik Demo/Simulatie Modus", value=True, help="Zet dit aan om direct te testen zonder API-sleutel.")

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

if st.sidebar.button("🚀 Haal Data & Analyse op"):
    with st.spinner(f"Bezig met berekenen van Poisson-model voor {selected_league_name}..."):
        
        master_shortlist = []
        
        # Realistische wedstrijdparen per competitie voor de simulatie
        teams_dict = {
            "Eredivisie (Nederland)": [("PSV", "Ajax"), ("Feyenoord", "AZ Alkmaar"), ("FC Utrecht", "FC Twente"), ("Go Ahead Eagles", "NEC Nijmegen")],
            "Premier League (Engeland)": [("Manchester City", "Arsenal"), ("Liverpool", "Chelsea"), ("Aston Villa", "Tottenham Hotspur"), ("Newcastle United", "Brighton")],
            "Bundesliga (Duitsland)": [("Bayern München", "Borussia Dortmund"), ("Bayer Leverkusen", "RB Leipzig"), ("Stuttgart", "Eintracht Frankfurt")]
        }
        
        default_teams = [("Team Alpha", "Team Beta"), ("Team Gamma", "Team Delta"), ("Team Omega", "Team Zeta")]
        match_list = teams_dict.get(selected_league_name, default_teams)
        
        for h, a in match_list:
            # Poisson berekening op basis van gesimuleerde xG waardes
            lam_h = round(random.uniform(1.3, 2.3), 2)
            lam_a = round(random.uniform(0.7, 1.4), 2)
            
            max_g = 6
            matrix = np.outer([poisson.pmf(i, lam_h) for i in range(max_g)], [poisson.pmf(j, lam_a) for j in range(max_g)])
            p_over_25 = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if (i + j) > 2.5)
            p_btts = sum(matrix[i, j] for i in range(1, max_g) for j in range(1, max_g))
            p_home_win = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if i > j)

            if p_btts >= 0.55:
                master_shortlist.append({"Competitie": selected_league_name, "Categorie": "⚽ BTTS", "Datum": "2026-10-15", "Wedstrijd": f"{h} vs {a}", "Model": f"Kans: {int(p_btts*100)}%", "Fair Odd": round(1/p_btts, 2), "Prob": p_btts})
            if p_over_25 >= 0.55:
                master_shortlist.append({"Competitie": selected_league_name, "Categorie": "🔥 Over 2.5", "Datum": "2026-10-15", "Wedstrijd": f"{h} vs {a}", "Model": f"Kans: {int(p_over_25*100)}%", "Fair Odd": round(1/p_over_25, 2), "Prob": p_over_25})
            if p_home_win >= 0.55:
                master_shortlist.append({"Competitie": selected_league_name, "Categorie": "🏠 Thuiswinst", "Datum": "2026-10-15", "Wedstrijd": f"{h} vs {a}", "Model": f"Kans: {int(p_home_win*100)}%", "Fair Odd": round(1/p_home_win, 2), "Prob": p_home_win})

        st.success("Analyse succesvol voltooid!")

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
            st.info("Geen wedstrijden gevonden die voldoen aan de drempel.")
