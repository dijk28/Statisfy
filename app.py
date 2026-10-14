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

# Custom CSS voor mobiel en zichtbare header
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: visible !important;}
        [data-testid="stHeader"] { background-color: transparent; }
        .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
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

# --- UITLEG & HANDLEIDING ---
with st.expander("📖 Hoe werkt Statisfy & Hoe gebruik je dit het slimste?", expanded=False):
    st.markdown("""
    Welkom bij **Statisfy**! Deze app berekent objectieve, wiskundige kansen voor voetbalwedstrijden om je te helpen bij het vinden van waarde.
    
    ### 🧠 Wat wordt er precies berekend?
    * **Poisson Verdeling:** Het model berekent op basis van historische data de verwachte doelpunten ($\lambda$) voor zowel de thuis- als uitploeg. Hiermee wordt een complete kansenmatrix (0 t/m 5 goals) en de kans op markten zoals *Over/Under*, *BTTS (Beide Teams Scoren)* en *1X2* bepaald.
    * **Vorm vs. Seizoen:** De berekening combineert de recente vorm van de laatste 5 wedstrijden (**60% weging**) met de totale seizoensdata (**40% weging**). Voor Europese bekers (CL/EL) wordt een slimme *Bayesian shrinkage* baseline gebruikt.
    * **Expected Value ($\text{EV}\%$):** Het model vergelijkt de werkelijke modelkans (de *Fair Odd*) met een geschatte bookmaker odd (inclusief jouw ingestelde bookmaker marge). Via de zijbalk kun je instellen of je alleen de allersterkste pick per wedstrijd wilt zien of alle geldige markten.

    ### 💡 Hoe gebruik je dit het slimste?
    1. **Stel je filters scherp:** Gebruik de zijbalk om odds onder de gewenste drempel (bijv. `< 1.2`) automatisch weg te filteren, zodat je geen tijd verliest aan weddenschappen met te weinig rendement.
    2. **Speel bij voorkeur SINGLES:** Het combineren van meerdere wedstrijden (accumulators/combis) verkleint je winkans exponentieel en laat bookmakers dubbel profiteren via gestapelde marges. Focus op losse weddenschappen met een sterke $\text{EV}\%$.
    3. **Check de Simulator:** Twijfel je over een specifieke wedstrijd? Gebruik de **Wedstrijd Simulator** in Tab 2 om de exacte kansenmatrix en verwachte doelpunten van twee willekeurige teams tegen elkaar te bekijken.
    4. **Beheer je risico:** Geen enkele statistiek biedt 100% garantie. Gebruik dit model als hulpmiddel en data-analyse, niet als garantie op winst.
    """)

st.markdown("---")

# --- ZIJBALK ---
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

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Betting Filters & EV")
min_odd = st.sidebar.slider("Minimale Odd Filter", min_value=1.0, max_value=2.5, value=1.2, step=0.05, help="Filter odds onder deze waarde eruit (standaard 1.2).")
bookmaker_margin = st.sidebar.slider("Bookmaker Marge (%)", min_value=0.0, max_value=10.0, value=5.0, step=0.5, help="Gebruikt voor Expected Value (EV) berekening ten opzichte van fair odds.")

st.sidebar.markdown("---")
st.sidebar.subheader("📌 Shortlist Weergave")
only_best_pick = st.sidebar.toggle(
    "Beperk tot 1 beste pick per wedstrijd", 
    value=True, 
    help="Aan: Toont per wedstrijd alleen de allersterkste/scherpste weddenschap. Uit: Toont alle geldige markten die aan de criteria voldoen."
)

# --- SESSION STATE INITIALISATIE ---
if "master_shortlist" not in st.session_state:
    st.session_state.master_shortlist = []
if "evaluation_results" not in st.session_state:
    st.session_state.evaluation_results = []
if "league_top_players" not in st.session_state:
    st.session_state.league_top_players = {}
if "season_stats" not in st.session_state:
    st.session_state.season_stats = {}
if "team_match_history" not in st.session_state:
    st.session_state.team_match_history = {}
if "analyzed_league" not in st.session_state:
    st.session_state.analyzed_league = None

if not api_key_input:
    st.warning("⚠️ Voer je API-key in via de zijbalk aan de linkerkant om de analyse te starten.")
else:
    BASE_URL = "https://api.football-data.org/v4/"

    @st.cache_data(ttl=3600, show_spinner=False)
    def get_api_data_cached(endpoint, api_key):
        url = f"{BASE_URL}{endpoint}"
        resp_headers = {"X-Auth-Token": api_key}
        try:
            response = requests.get(url, headers=resp_headers, timeout=10)
            time.sleep(0.3)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                return "RATE_LIMIT"
        except requests.exceptions.Timeout:
            return "TIMEOUT"
        except Exception:
            return None
        return None

    if st.sidebar.button("🚀 Start Analyse"):
        with st.spinner(f"🔄 Bezig met berekenen en ophalen van data voor {selected_league_name}... Even geduld aub."):
            master_shortlist = []
            evaluation_results = []
            league_top_players = {}
            season_stats = {}
            team_match_history = {}

            # 1. Spelerstatistieken ophalen
            scorers_data = get_api_data_cached(f"competitions/{league_code}/scorers?limit=3", api_key_input)
            if scorers_data == "RATE_LIMIT":
                st.error("⚠️ Te veel verzoeken naar de API tegelijk. Wacht even een minuutje en probeer opnieuw.")
                st.stop()
            elif scorers_data == "TIMEOUT":
                st.error("⚠️ De verbinding met de server duurde te lang. Probeer het zo nog eens.")
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
            match_data = get_api_data_cached(f"competitions/{league_code}/matches", api_key_input)
            if match_data == "RATE_LIMIT":
                st.error("⚠️ Te veel verzoeken naar de API tegelijk. Wacht even een minuutje en probeer opnieuw.")
                st.stop()
            elif match_data == "TIMEOUT":
                st.error("⚠️ De verbinding met de server duurde te lang. Probeer het zo nog eens.")
                st.stop()
            
            if not match_data or not isinstance(match_data, dict) or "matches" not in match_data:
                st.error(f"⚠️ Kon geen wedstrijddata ophalen voor {selected_league_name}.")
            else:
                matches = match_data["matches"]
                finished_matches = [m for m in matches if m["status"] == "FINISHED"]
                scheduled = [m for m in matches if m["status"] in ["SCHEDULED", "TIMED"]]
                
                if finished_matches:
                    finished_sorted = sorted(finished_matches, key=lambda x: x["utcDate"])

                    for idx, m in enumerate(finished_sorted):
                        home = m["homeTeam"]["name"]
                        away = m["awayTeam"]["name"]
                        date = m["utcDate"][:10]
                        ft = m["score"]["fullTime"]
                        hg, ag = ft["home"], ft["away"]
                        if hg is None or ag is None: 
                            continue

                        h_stat = season_stats.get(home)
                        a_stat = season_stats.get(away)
                        min_games = 1 if league_code in ["CL", "EL"] else 3

                        if h_stat and a_stat and h_stat["played"] >= min_games and a_stat["played"] >= min_games:
                            raw_lam_h = max(0.5, ((h_stat["gf"] / h_stat["played"]) + (h_stat["ga"] / h_stat["played"])) / 2)
                            raw_lam_a = max(0.5, ((a_stat["gf"] / a_stat["played"]) + (a_stat["ga"] / a_stat["played"])) / 2)

                            # --- BAYESIAN SHRINKAGE VOOR CL & EL ---
                            if league_code in ["CL", "EL"]:
                                baseline_lambda = 1.35
                                weight_h = min(1.0, h_stat["played"] / 4.0)
                                weight_a = min(1.0, a_stat["played"] / 4.0)
                                season_lam_h = (weight_h * raw_lam_h) + ((1 - weight_h) * baseline_lambda)
                                season_lam_a = (weight_a * raw_lam_a) + ((1 - weight_a) * baseline_lambda)
                            else:
                                season_lam_h = raw_lam_h
                                season_lam_a = raw_lam_a

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
                            p_away_win = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if i < j)
                            p_draw = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if i == j)
                            
                            p_over_15 = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if (i + j) > 1.5)
                            p_over_25 = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if (i + j) > 2.5)
                            p_under_25 = 1 - p_over_25
                            p_under_35 = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if (i + j) < 3.5)
                            
                            p_btts = sum(matrix[i, j] for i in range(1, max_g) for j in range(1, max_g))
                            p_dc_1x = p_home_win + p_draw
                            p_dc_x2 = p_away_win + p_draw

                            actual_total_goals = hg + ag
                            actual_home_win = 1 if hg > ag else 0
                            actual_away_win = 1 if hg < ag else 0
                            actual_btts = 1 if (hg > 0 and ag > 0) else 0

                            evals_to_check = [
                                ("⚽ BTTS", p_btts, actual_btts == 1),
                                ("🔥 Over 2.5", p_over_25, actual_total_goals > 2.5),
                                ("⚡ Over 1.5", p_over_15, actual_total_goals > 1.5),
                                ("🏠 Thuiswinst", p_home_win, actual_home_win == 1),
                                ("✈️ Uitwinst", p_away_win, actual_away_win == 1),
                                ("🛡️ Under 2.5", p_under_25, actual_total_goals < 2.5),
                                ("🛡️ Under 3.5", p_under_35, actual_total_goals < 3.5),
                                ("🤝 Dubbele Kans (1X)", p_dc_1x, hg >= ag),
                                ("🤝 Dubbele Kans (X2)", p_dc_x2, hg <= ag)
                            ]

                            for cat, prob, did_win in evals_to_check:
                                fair_odd = round(1 / prob, 2) if prob > 0 else 99.0
                                if prob >= 0.60 and fair_odd >= min_odd:
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

                        for team, scored, conceded in [(home, hg, ag), (away, ag, hg)]:
                            if team not in season_stats:
                                season_stats[team] = {"played": 0, "gf": 0, "ga": 0}
                            season_stats[team]["played"] += 1
                            season_stats[team]["gf"] += scored
                            season_stats[team]["ga"] += conceded

                        if home not in team_match_history: 
                            team_match_history[home] = []
                        if away not in team_match_history: 
                            team_match_history[away] = []
                        team_match_history[home].append({"scored": hg, "conceded": ag})
                        team_match_history[away].append({"scored": ag, "conceded": hg})

                # 3. Komende wedstrijden analyseren (Afhankelijk van de toggle: 1 beste pick of alle geldige picks)
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
                            
                        raw_lam_h = max(0.5, ((h_stat["gf"] / h_stat["played"]) + (h_stat["ga"] / h_stat["played"])) / 2)
                        raw_lam_a = max(0.5, ((a_stat["gf"] / a_stat["played"]) + (a_stat["ga"] / a_stat["played"])) / 2)

                        if league_code in ["CL", "EL"]:
                            baseline_lambda = 1.35
                            weight_h = min(1.0, h_stat["played"] / 4.0)
                            weight_a = min(1.0, a_stat["played"] / 4.0)
                            season_lam_h = (weight_h * raw_lam_h) + ((1 - weight_h) * baseline_lambda)
                            season_lam_a = (weight_a * raw_lam_a) + ((1 - weight_a) * baseline_lambda)
                        else:
                            season_lam_h = raw_lam_h
                            season_lam_a = raw_lam_a

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
                        total_lam = lam_h + lam_a
                        
                        max_g = 6
                        matrix = np.outer([poisson.pmf(i, lam_h) for i in range(max_g)], [poisson.pmf(j, lam_a) for j in range(max_g)])
                        
                        p_home_win = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if i > j)
                        p_away_win = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if i < j)
                        p_draw = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if i == j)
                        
                        p_over_15 = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if (i + j) > 1.5)
                        p_over_25 = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if (i + j) > 2.5)
                        p_under_25 = 1 - p_over_25
                        p_under_35 = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if (i + j) < 3.5)
                        
                        p_btts = sum(matrix[i, j] for i in range(1, max_g) for j in range(1, max_g))
                        p_dc_1x = p_home_win + p_draw
                        p_dc_x2 = p_away_win + p_draw

                        form_sample_h = len(h_history)
                        if league_code in ["CL", "EL"]:
                            data_label = f"🇪🇺 Europa (Spelers: {h_stat['played']}d)"
                        else:
                            data_label = f"Vorm ({form_sample_h}v/{h_stat['played']}s duels)"

                        predictions_to_evaluate = [
                            ("⚽ BTTS (Beide Teams Scoren)", p_btts, f"Kans op doelpunten beide kanten: {int(p_btts*100)}%"),
                            ("🔥 Doelpunten (Over 2.5)", p_over_25, f"Verwacht: {round(total_lam, 2)} goals (Kans: {int(p_over_25*100)}%)"),
                            ("⚡ Doelpunten (Over 1.5)", p_over_15, f"Verwacht: {round(total_lam, 2)} goals (Over 1.5 kans: {int(p_over_15*100)}%)"),
                            ("🏠 Sterke Thuiswinst", p_home_win, f"Thuiswinst kans: {int(p_home_win*100)}%"),
                            ("✈️ Sterke Uitwinst", p_away_win, f"Uitwinst kans: {int(p_away_win*100)}%"),
                            ("🛡️ Weinig Goals (Under 2.5)", p_under_25, f"Verwacht: {round(total_lam, 2)} goals (Under kans: {int(p_under_25*100)}%)"),
                            ("🛡️ Veilige Goals (Under 3.5)", p_under_35, f"Verwacht: {round(total_lam, 2)} goals (Under 3.5 kans: {int(p_under_35*100)}%)"),
                            ("🤝 Dubbele Kans (1X)", p_dc_1x, f"Thuis of Gelijk kans: {int(p_dc_1x*100)}%"),
                            ("🤝 Dubbele Kans (X2)", p_dc_x2, f"Uit of Gelijk kans: {int(p_dc_x2*100)}%")
                        ]

                        match_candidates = []
                        for cat, prob, indication in predictions_to_evaluate:
                            threshold = 0.65 if "Dubbele Kans" in cat else 0.60
                            if prob >= threshold:
                                fair_odd = round(1 / prob, 2)
                                
                                if fair_odd < min_odd:
                                    continue
                                
                                bookie_odd = round(fair_odd * (1 - (bookmaker_margin / 100)), 2)
                                bookie_odd = max(1.01, bookie_odd)
                                
                                ev_value = (prob * bookie_odd) - 1
                                ev_percentage = round(ev_value * 100, 1)

                                match_candidates.append({
                                    "Competitie": selected_league_name,
                                    "Categorie": cat,
                                    "Datum": date,
                                    "Wedstrijd": f"{h} vs {a}",
                                    "Indicatie / Model": indication,
                                    "Fair Odd": fair_odd,
                                    "Bookie Odd (est.)": bookie_odd,
                                    "EV (%)": f"{ev_percentage}%",
                                    "Data Basis": data_label,
                                    "Prob_Val": prob,
                                    "EV_Val": ev_value
                                })

                        # Toepassen van de selectie op basis van de toggle in de zijbalk
                        if match_candidates:
                            if only_best_pick:
                                match_candidates.sort(key=lambda x: x["EV_Val"], reverse=True)
                                master_shortlist.append(match_candidates[0])
                            else:
                                for cand in match_candidates:
                                    master_shortlist.append(cand)

            # Resultaten opslaan in session state
            st.session_state.master_shortlist = master_shortlist
            st.session_state.evaluation_results = evaluation_results
            st.session_state.league_top_players = league_top_players
            st.session_state.season_stats = season_stats
            st.session_state.team_match_history = team_match_history
            st.session_state.analyzed_league = selected_league_name
            st.success("Analyse succesvol voltooid!")

    # --- RENDER TABS VANUIT SESSION STATE ---
    if st.session_state.analyzed_league == selected_league_name and (st.session_state.master_shortlist or st.session_state.evaluation_results or st.session_state.league_top_players):
        tab1, tab2, tab3 = st.tabs([
            "🎯 Shortlist (Komende Speelronde)", 
            "🔬 Wedstrijd Simulator & Matrix", 
            "📈 Track Record & Evaluatie"
        ])
        
        with tab1:
            st.header(f"🏆 Shortlist: {selected_league_name} (Odds ≥ {min_odd})")
            if st.session_state.master_shortlist:
                df_shortlist = pd.DataFrame(st.session_state.master_shortlist)
                df_shortlist = df_shortlist.sort_values(by="EV_Val", ascending=False)
                df_display = df_shortlist.drop(columns=["Prob_Val", "EV_Val"])
                st.dataframe(df_display, use_container_width=True)
            else:
                st.info(f"Geen wedstrijden gevonden voor {selected_league_name} die voldoen aan de criteria (Kans ≥ 60%, Odd ≥ {min_odd}).")

            st.markdown("---")
            st.header(f"⚽ Top Spelers: {selected_league_name}")
            if st.session_state.league_top_players:
                for comp_name, players in st.session_state.league_top_players.items():
                    with st.expander(f"📊 Bekijk topscorers van {comp_name}"):
                        df_p = pd.DataFrame(players)
                        st.dataframe(df_p, use_container_width=True)
            else:
                st.info("Geen topscorersdata beschikbaar.")

        with tab2:
            st.header("🔬 Diepgaande Wedstrijd Simulator & Poisson Matrix")
            st.markdown("Selecteer twee teams uit deze competitie om de verwachte doelpunten, de kansenmatrix (0 t/m 5 goals) en alle marktkansen te berekenen.")
            
            teams_list = sorted(list(st.session_state.season_stats.keys()))
            if len(teams_list) >= 2:
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    sim_home = st.selectbox("Thuisploeg", teams_list, index=0)
                with col_t2:
                    sim_away = st.selectbox("Uitploeg", teams_list, index=1 if len(teams_list) > 1 else 0)
                
                if sim_home == sim_away:
                    st.warning("⚠️ Kies twee verschillende teams om een simulatie uit te voeren.")
                else:
                    h_stat = st.session_state.season_stats.get(sim_home)
                    a_stat = st.session_state.season_stats.get(sim_away)
                    
                    if h_stat and a_stat:
                        h_history = st.session_state.team_match_history.get(sim_home, [])[-5:]
                        a_history = st.session_state.team_match_history.get(sim_away, [])[-5:]
                        
                        raw_lam_h = max(0.5, ((h_stat["gf"] / h_stat["played"]) + (h_stat["ga"] / h_stat["played"])) / 2)
                        raw_lam_a = max(0.5, ((a_stat["gf"] / a_stat["played"]) + (a_stat["ga"] / a_stat["played"])) / 2)
                        
                        if league_code in ["CL", "EL"]:
                            baseline_lambda = 1.35
                            w_h = min(1.0, h_stat["played"] / 4.0)
                            w_a = min(1.0, a_stat["played"] / 4.0)
                            season_lam_h = (w_h * raw_lam_h) + ((1 - w_h) * baseline_lambda)
                            season_lam_a = (w_a * raw_lam_a) + ((1 - w_a) * baseline_lambda)
                        else:
                            season_lam_h = raw_lam_h
                            season_lam_a = raw_lam_a

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
                        
                        st.markdown("### 📈 Verwachte Doelpunten ($\lambda$)")
                        col_m1, col_m2, col_m3 = st.columns(3)
                        col_m1.metric(f"Verwacht {sim_home} (Thuis)", round(lam_h, 2))
                        col_m2.metric(f"Verwacht {sim_away} (Uit)", round(lam_a, 2))
                        col_m3.metric("Totaal Verwacht", round(lam_h + lam_a, 2))
                        
                        max_g = 6
                        matrix = np.outer([poisson.pmf(i, lam_h) for i in range(max_g)], [poisson.pmf(j, lam_a) for j in range(max_g)])
                        
                        score_matrix_df = pd.DataFrame(
                            matrix * 100, 
                            index=[f"{sim_home} {i}" for i in range(max_g)], 
                            columns=[f"{sim_away} {j}" for j in range(max_g)]
                        ).round(1)
                        
                        st.markdown("### 🧮 Poisson Kansmatrix (%)")
                        st.markdown("Kans op elke mogelijke eindstand (in %):")
                        st.dataframe(score_matrix_df, use_container_width=True)
                        
                        p_hw = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if i > j)
                        p_draw = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if i == j)
                        p_aw = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if i < j)
                        p_o25 = sum(matrix[i, j] for i in range(max_g) for j in range(max_g) if (i + j) > 2.5)
                        p_u25 = 1 - p_o25
                        p_btts = sum(matrix[i, j] for i in range(1, max_g) for j in range(1, max_g))
                        
                        st.markdown("### 📊 Model Kansen & Fair Odds")
                        col_o1, col_o2, col_o3, col_o4 = st.columns(4)
                        col_o1.metric("Thuiswinst", f"{int(p_hw*100)}%", f"Odd: {round(1/p_hw, 2)}")
                        col_o2.metric("Gelijkspel", f"{int(p_draw*100)}%", f"Odd: {round(1/p_draw, 2)}")
                        col_o3.metric("Uitwinst", f"{int(p_aw*100)}%", f"Odd: {round(1/p_aw, 2)}")
                        col_o4.metric("BTTS (Ja)", f"{int(p_btts*100)}%", f"Odd: {round(1/p_btts, 2)}")
            else:
                st.info("Start eerst de analyse via de zijbalk zodat er teamdata beschikbaar is voor de simulator.")

        with tab3:
            st.header(f"📊 Historische Evaluatie: {selected_league_name}")
            st.markdown(f"Hier zie je per reeds gespeelde wedstrijd in {selected_league_name} of de voorspelling van het model daadwerkelijk uitkwam.")
            
            if st.session_state.evaluation_results:
                df_eval = pd.DataFrame(st.session_state.evaluation_results)
                
                total_preds = len(df_eval)
                correct_preds = df_eval["Win_Bool"].sum()
                hitrate = (correct_preds / total_preds) * 100 if total_preds > 0 else 0
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Totaal Geteste Picks", total_preds)
                col2.metric("Aantal Goed", int(correct_preds))
                col3.metric("Nauwkeurigheid (Hitrate)", f"{round(hitrate, 1)}%")
                
                st.markdown("---")
                df_eval_display = df_eval.drop(columns=["Win_Bool"])
                df_eval_display = df_eval_display.sort_values(by="Datum", ascending=False)
                st.dataframe(df_eval_display, use_container_width=True)
            else:
                st.info("Nog niet genoeg historische data beschikbaar om te evalueren.")
