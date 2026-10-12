import streamlit as st
import requests
import pandas as pd
import numpy as np
from scipy.stats import poisson
import time

# Pagina configuratie
st.set_page_config(
    page_title="Personal Betting Assistant",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ Professionele Betting Analyser & Trechter")
st.markdown("Welkom bij je persoonlijke beslissingsondersteunende systeem met bankroll management en grafieken.")

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

    # Gecachte API-functie om binnen de gratis limiet (10 req/min) te blijven
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

                    # Gespeelde wedstrijden verwerken voor statistieken & evaluatie
                    for m in finished_sorted:
                        home = m["homeTeam"]["name"]
                        away = m["awayTeam"]["name"]
                        date = m["utcDate"][:10]
                        ft = m["score"]["fullTime"]
                        hg, ag = ft["home"], ft["away"]
                        if hg is None or ag is None: continue

                        h_stat = season_stats.get(home)
                        a_stat = season_stats.get(away)
                        min_games = 1 if league_code in ["CL", "EL"] else 3

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
                                        "Win_Bool": 1 if did_win else 0
                                    })

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

                # 3. Komende wedstrijden analyseren voor de Shortlist
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
                            
                        season_lam_h = max(0.5, ((h_stat["gf"] / h_stat["played"]) + (a_stat["ga"] / a_stat["played"])) / 2)
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
                        total_lam = lam_h + lam_a
                        
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
                            master_shortlist.append({"Competitie": selected_league_name, "Categorie": "⚽ BTTS (Beide Teams Scoren)", "Datum": date, "Wedstrijd": f"{h} vs {a}", "Indicatie / Model": f"Kans: {int(p_btts*100)}%", "Fair Odd": round(1 / p_btts, 2), "Inzet (€)": round(unit_size, 2), "Data Basis": data_label, "Prob_Val": p_btts})
                        if p_over_25 >= 0.60:
                            master_shortlist.append({"Competitie": selected_league_name, "Categorie": "🔥 Doelpunten (Over 2.5)", "Datum": date, "Wedstrijd": f"{h} vs {a}", "Indicatie / Model": f"Verwacht: {round(total_lam, 2)} goals (Kans: {int(p_over_25*100)}%)", "Fair Odd": round(1 / p_over_25, 2), "Inzet (€)": round(unit_size, 2), "Data Basis": data_label, "Prob_Val": p_over_25})
                        if p_home_win >= 0.60:
                            master_shortlist.append({"Competitie": selected_league_name, "Categorie": "🏠 Sterke Thuiswinst", "Datum": date, "Wedstrijd": f"{h} vs {a}", "Indicatie / Model": f"Thuiswinst kans: {int(p_home_win*100)}%", "Fair Odd": round(1 / p_home_win, 2), "Inzet (€)": round(unit_size, 2), "Data Basis": data_label, "Prob_Val": p_home_win})
                        if p_under_25 >= 0.60:
                            master_shortlist.append({"Competitie": selected_league_name, "Categorie": "🛡️ Weinig Goals (Under 2.5)", "Datum": date, "Wedstrijd": f"{h} vs {a}", "Indicatie / Model": f"Verwacht: {round(total_lam, 2)} goals (Under kans: {int(p_under_25*100)}%)", "Fair Odd": round(1 / p_under_25, 2), "Inzet (€)": round(unit_size, 2), "Data Basis": data_label, "Prob_Val": p_under_25})

        st.success("Analyse succesvol voltooid!")
        
        # --- TABBLADEN ---
        tab1, tab2 = st.tabs(["🎯 Shortlist & Bankroll", "📈 Track Record & Grafieken"])
        
        with tab1:
            st.header(f"🏆 Shortlist: {selected_league_name} (>= 60% Kans)")
            if master_shortlist:
                df_shortlist = pd.DataFrame(master_shortlist)
                df_filtered = df_shortlist.sort_values(by="Prob_Val", ascending=False)
                df_display = df_filtered.drop(columns=["Prob_Val"])
                st.dataframe(df_display, use_container_width=True)
            else:
                st.info("Geen wedstrijden gevonden die aan de strenge criteria van >= 60% kans voldoen voor deze ronde.")

            st.markdown("---")
            st.header("⚽ Top Spelers")
            if league_top_players:
                for comp_name, players in league_top_players.items():
                    df_p = pd.DataFrame(players)
                    st.dataframe(df_p, use_container_width=True)
            else:
                st.info("Geen topscorersdata beschikbaar.")

        with tab2:
            st.header("📊 Historische Evaluatie & Grafieken")
            st.markdown("Hier zie je of de voorspellingen uit het verleden (kansen van 60% of hoger) goed of fout waren.")
            
            if evaluation_results:
                df_eval = pd.DataFrame(evaluation_results)
                
                total_preds = len(df_eval)
                correct_preds = df_eval["Win_Bool"].sum()
                hitrate = (correct_preds / total_preds) * 100 if total_preds > 0 else 0
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Totaal Geteste Picks", total_preds)
                col2.metric("Aantal Goed", int(correct_preds))
                col3.metric("Nauwkeurigheid (Hitrate)", f"{round(hitrate, 1)}%")
                
                st.markdown("---")
                
                st.subheader("📊 Prestatie per Categorie")
                cat_summary = df_eval.groupby("Categorie")["Win_Bool"].agg(
                    Totaal="count",
                    Goed=lambda x: (x == 1).sum()
                ).reset_index()
                cat_summary["Hitrate (%)"] = round((cat_summary["Goed"] / cat_summary["Totaal"]) * 100, 1)
                st.dataframe(cat_summary, use_container_width=True)
                
                chart_data = cat_summary.set_index("Categorie")[["Goed", "Totaal"]]
                st.bar_chart(chart_data)

                st.markdown("---")
                st.subheader("📝 Alle Geteste Wedstrijden")
                df_eval_display = df_eval.drop(columns=["Win_Bool"]).sort_values(by="Datum", ascending=False)
                st.dataframe(df_eval_display, use_container_width=True)
            else:
                st.info("Nog niet genoeg historische data beschikbaar om te evalueren.")
