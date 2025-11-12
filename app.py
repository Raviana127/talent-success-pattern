import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

st.set_page_config(layout="wide", page_title="Talent Success Pattern Dashboard")

# === CONNECT SUPABASE ===
SUPABASE_URL = "https://qiorcnwdjfgoajyzihdv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFpb3JjbndkamZnb2FqeXppaGR2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIzOTgzNzUsImV4cCI6MjA3Nzk3NDM3NX0.spRN_LRjjX_FJPK8R0dmsbmQJ9_C-z7sVa4cpjS_Ksg"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# === LOAD TABLE SAFE ===
def load(name):
    try:
        return pd.DataFrame(supabase.table(name).select("*").execute().data)
    except:
        return pd.DataFrame()

employees = load("employees")
performance = load("performance_yearly")
competencies = load("competencies_yearly")
strengths = load("strengths")
pillars = load("dim_competency_pillars")
psych = load("profiles_psych")

# === CLEAN DATA ===
performance["rating"] = pd.to_numeric(performance.get("rating"), errors="coerce")
competencies["score"] = pd.to_numeric(competencies.get("score"), errors="coerce")
psych["iq"] = pd.to_numeric(psych.get("iq"), errors="coerce")
psych["tiki"] = pd.to_numeric(psych.get("tiki"), errors="coerce")

performance["group"] = performance["rating"].apply(lambda x: "Rating 5" if x == 5 else "Non-5")
top_ids = performance.loc[performance["rating"] == 5, "employee_id"].unique()

st.title("Talent Success Pattern Dashboard")
st.markdown("Analisis pola keberhasilan berdasarkan **karyawan dengan Rating 5**.")

# === ROW 1: STRENGTHS (LEFT) | RADAR (RIGHT) ===
col1, col2 = st.columns(2)

with col1:
    st.subheader("Top Strengths Karyawan Rating 5")
    top_strengths = strengths[strengths["employee_id"].isin(top_ids)]
    top_strengths_count = top_strengths.groupby("theme").size().reset_index(name="count")
    fig = px.bar(top_strengths_count.sort_values("count", ascending=False).head(10),
                 x="theme", y="count",
                 title=None)
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Perbandingan Kompetensi: Rating 5 vs Non-5")
    comp = competencies.merge(pillars, on="pillar_code", how="left")
    comp = comp.merge(performance, on=["employee_id","year"], how="left")
    comp = comp.dropna(subset=["score", "rating"])
    comp["group"] = comp["rating"].apply(lambda x: "Rating 5" if x == 5 else "Non-5")
    avg_comp = comp.groupby(["pillar_label", "group"])["score"].mean().reset_index()
    radar = px.line_polar(avg_comp, r="score", theta="pillar_label", color="group", line_close=True)
    radar.update_layout(height=500)
    st.plotly_chart(radar, use_container_width=True)

st.markdown("---")

# === ROW 2: HEATMAP (LEFT) | TALENT MAPPING (RIGHT) ===
col3, col4 = st.columns(2)

with col3:
    st.subheader("Heatmap Korelasi Psikometrik")
    psych_cols = [c for c in ["pauli","faxtor","iq","gtq","tiki"] if c in psych.columns]
    corr = psych[psych_cols].apply(pd.to_numeric, errors="coerce").corr()
    heat = px.imshow(corr, text_auto=True, color_continuous_scale="Plasma")
    heat.update_layout(height=520)
    st.plotly_chart(heat, use_container_width=True)

with col4:
    st.subheader("Talent Mapping")
    success = comp.groupby("employee_id")["score"].mean().reset_index()
    success = success.merge(psych[["employee_id","iq","tiki"]], on="employee_id", how="left")
    success["success_score"] = (success["score"]*0.6) + (success["tiki"]*0.25) + (success["iq"]*0.15)
    fig_bubble = px.scatter(success.dropna(),
                            x="iq", y="tiki",
                            size="success_score",
                            hover_name="employee_id")
    fig_bubble.update_layout(height=500)
    st.plotly_chart(fig_bubble, use_container_width=True)

st.markdown("---")

# === INSIGHT AUTO ===
st.subheader("Insight Otomatis")
r = corr.loc["iq", "tiki"] if ("iq" in corr.index and "tiki" in corr.columns) else None
if r is None or pd.isna(r):
    st.write("Tidak cukup data untuk menghitung korelasi IQ dan TIKI.")
elif abs(r) < 0.2:
    st.write(f"Korelasi **{r:.3f} → Lemah**. IQ dan TIKI mengukur kemampuan berbeda.")
elif r > 0.2:
    st.write(f"Korelasi **{r:.3f} → Positif**. IQ tinggi cenderung diikuti TIKI tinggi.")
else:
    st.write(f"Korelasi **{r:.3f} → Negatif**. IQ tinggi tidak menjamin TIKI tinggi.")
