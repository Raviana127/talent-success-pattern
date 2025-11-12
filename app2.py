import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from datetime import datetime

# ========== CONFIG ==========
st.set_page_config(layout="wide", page_title="Talent Success Pattern Dashboard")

# === Supabase credentials (isi dengan kunci milikmu) ===
SUPABASE_URL = "https://qiorcnwdjfgoajyzihdv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFpb3JjbndkamZnb2FqeXppaGR2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIzOTgzNzUsImV4cCI6MjA3Nzk3NDM3NX0.spRN_LRjjX_FJPK8R0dmsbmQJ9_C-z7sVa4cpjS_Ksg"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ========== SAFE TABLE LOAD ==========
def load_table(name):
    try:
        resp = supabase.table(name).select("*").limit(3000).execute()
        return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()
    except Exception as e:
        st.warning(f"Failed to load {name}: {e}")
        return pd.DataFrame()

# ========== LOAD DATA ==========
employees = load_table("employees")
performance = load_table("performance_yearly")
competencies = load_table("competencies_yearly")
strengths = load_table("strengths")
pillars = load_table("dim_competency_pillars")
psych = load_table("profiles_psych")
departments = load_table("dim_departments")
grades = load_table("dim_grades")

# ========== CLEAN / TYPE CAST ==========
# convert potential numeric fields safely
performance["rating"] = pd.to_numeric(performance.get("rating"), errors="coerce")
competencies["score"] = pd.to_numeric(competencies.get("score"), errors="coerce")
psych_cols_try = ["iq", "tiki", "gtq", "pauli", "faxtor"]
for c in psych_cols_try:
    if c in psych.columns:
        psych[c] = pd.to_numeric(psych.get(c), errors="coerce")

# helpful lookups
# employees display options: "Fullname | EMPID"
if "employee_id" in employees.columns:
    employees["display"] = employees.apply(
        lambda r: f"{r.get('fullname','Unknown')} | {r.get('employee_id')}", axis=1
    )
else:
    employees["display"] = employees.get("fullname", "Unknown")

# department & grade options - pick sensible columns if exist
if "department_id" in departments.columns:
    dept_options = departments["department_id"].astype(str).unique().tolist()
elif "name" in departments.columns:
    dept_options = departments["name"].astype(str).unique().tolist()
else:
    dept_options = []

if "grades_id" in grades.columns:
    grade_options = grades["grades_id"].astype(str).unique().tolist()
elif "name" in grades.columns:
    grade_options = grades["name"].astype(str).unique().tolist()
else:
    grade_options = []

# ========== UI HEADER ==========
st.title("Talent Success Pattern Dashboard")
st.markdown("Isi form di bawah untuk menyimpan job vacancy dan generate analisis berbasis benchmark.")

# ========== FORM: Role Info & Benchmarks ==========
with st.form("role_form"):
    st.subheader("1️⃣ Role Information")

    c1, c2 = st.columns(2)
    with c1:
        role_name = st.selectbox("Role Name (from dim_departments)", options=dept_options)
        job_level = st.selectbox("Job Level (from dim_grades)", options=grade_options)
    with c2:
        role_purpose = st.text_area("Role Purpose", placeholder="1-2 kalimat untuk tujuan role")
        st.write("Pilih Employee Benchmark (max 3):")
        bench_options = employees["display"].tolist() if not employees.empty else []
        benchmark_selected = st.multiselect("Employee Benchmarking", options=bench_options, max_selections=3)

    submitted = st.form_submit_button("🚀 Generate Job Description & Variable Score")

# ========== HELPER: make JSON-safe values ==========
def make_json_safe(v):
    """
    Convert numpy / pandas types to plain python types for JSON insert.
    """
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    # convert numpy ints/floats
    if isinstance(v, (int, float, str, bool)):
        return v
    try:
        return int(v)
    except Exception:
        try:
            return float(v)
        except Exception:
            return str(v)

# ========== AFTER SUBMIT ==========
if submitted:
    # map selected display -> employee_id
    bench_ids = []
    for disp in benchmark_selected:
        # disp format: "Fullname | EMPID"
        if isinstance(disp, str) and " | " in disp:
            empid = disp.split(" | ")[1].strip()
            bench_ids.append(empid)
        else:
            # try match by fullname
            match = employees[employees["display"] == disp]
            if not match.empty and "employee_id" in match.columns:
                bench_ids.append(str(match.iloc[0]["employee_id"]))

    # build job_vacancy object
    job_vacancy_id = f"JV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    data_insert = {
        "job_vacancy_id": str(job_vacancy_id),
        "role_name": make_json_safe(role_name),
        "job_level": make_json_safe(job_level),
        "role_purpose": make_json_safe(role_purpose),
        "selected_benchmark": make_json_safe(", ".join(benchmark_selected)),
        "created_at": datetime.now().isoformat(),
    }

    # insert to supabase (JSON-safe)
    try:
        supabase.table("talent_benchmarks").insert(data_insert).execute()
        st.success(f"✅ Job vacancy saved: {job_vacancy_id}")
    except Exception as e:
        st.error(f"Failed to save to Supabase: {e}")

    # ========== DYNAMIC ANALYSIS BASED ON BENCHMARK ==========
    st.markdown("---")
    st.header("📊 Analysis based on selected benchmark")

    if len(bench_ids) == 0:
        st.warning("No benchmark selected — choose at least 1 employee.")
        st.stop()

    # filter data for benchmark employees
    comp_bench = competencies[competencies["employee_id"].isin(bench_ids)] if not competencies.empty else pd.DataFrame()
    strengths_bench = strengths[strengths["employee_id"].isin(bench_ids)] if not strengths.empty else pd.DataFrame()
    psych_bench = psych[psych["employee_id"].isin(bench_ids)] if not psych.empty else pd.DataFrame()

    # ----- Strengths chart -----
    col_s1, col_s2 = st.columns([1, 1])
    with col_s1:
        st.subheader("Top Strengths (Benchmark)")
        if strengths_bench.empty:
            st.info("No strengths data for selected benchmark.")
        else:
            top_strengths = strengths_bench.groupby("theme").size().reset_index(name="count")
            top_strengths = top_strengths.sort_values("count", ascending=False)
            fig_strength = px.bar(top_strengths.head(12), x="theme", y="count", title=None)
            fig_strength.update_layout(height=420)
            st.plotly_chart(fig_strength, use_container_width=True)

    # ----- Radar: competencies (show all pillars) -----
    with col_s2:
        st.subheader("Competency profile (Benchmark Median per Pillar)")

        # compute avg score per pillar for bench
        if comp_bench.empty:
            st.info("No competency records for selected benchmark.")
            avg_comp_df = pd.DataFrame()
        else:
            avg_comp = comp_bench.groupby("pillar_code", as_index=False)["score"].mean()
            # merge to pillar labels
            if not pillars.empty and "pillar_code" in pillars.columns and "pillar_label" in pillars.columns:
                avg_comp = avg_comp.merge(pillars[["pillar_code", "pillar_label"]].drop_duplicates(), on="pillar_code", how="left")
            else:
                # fallback: use pillar_code as label
                avg_comp["pillar_label"] = avg_comp["pillar_code"]

            # ensure all pillars present (fillna 0)
            if not pillars.empty and "pillar_code" in pillars.columns and "pillar_label" in pillars.columns:
                all_pillars = pillars[["pillar_code", "pillar_label"]].drop_duplicates()
                avg_comp_df = all_pillars.merge(avg_comp, on=["pillar_code", "pillar_label"], how="left").fillna(0)
            else:
                avg_comp_df = avg_comp.copy()

        if avg_comp_df.empty:
            st.info("No pillar info to show.")
        else:
            # plot radar - plotly expects rows per (pillar_label)
            radar = px.line_polar(avg_comp_df, r="score", theta="pillar_label", line_close=True)
            radar.update_layout(height=420)
            st.plotly_chart(radar, use_container_width=True)

    st.markdown("---")

    # ----- Heatmap psikometrik -----
    st.subheader("Psychometric correlation (Benchmark)")
    psych_numeric_cols = [c for c in ["pauli", "faxtor", "iq", "gtq", "tiki"] if c in psych_bench.columns]
    if len(psych_numeric_cols) < 2:
        st.info("Not enough psychometric numeric columns available for heatmap (need at least 2).")
    else:
        psych_num = psych_bench[psych_numeric_cols].apply(pd.to_numeric, errors="coerce")
        corr = psych_num.corr()
        heat = px.imshow(corr, text_auto=True, color_continuous_scale="Plasma")
        heat.update_layout(height=500)
        st.plotly_chart(heat, use_container_width=True)

    st.markdown("---")

    # ----- Talent mapping (bubble) -----
    st.subheader("Talent Mapping: Success score (Benchmark Individuals)")
    if comp_bench.empty:
        st.info("No competency data to build success scores.")
    else:
        # success scores for benchmark employees
        success = comp_bench.groupby("employee_id", as_index=False)["score"].mean()
        # merge psych data (bench)
        if "employee_id" in psych_bench.columns:
            success = success.merge(psych_bench[["employee_id"] + [c for c in psych_numeric_cols if c in psych_bench.columns]],
                                    on="employee_id", how="left")
        # compute success_score with fallback if tiki or iq missing (coerce to 0)
        success["tiki"] = pd.to_numeric(success.get("tiki"), errors="coerce").fillna(0)
        success["iq"] = pd.to_numeric(success.get("iq"), errors="coerce").fillna(0)
        success["success_score"] = (success["score"].fillna(0) * 0.6) + (success["tiki"] * 0.25) + (success["iq"] * 0.15)

        # attach fullname if available
        if "employee_id" in employees.columns and "fullname" in employees.columns:
            success = success.merge(employees[["employee_id", "fullname"]], on="employee_id", how="left")
        else:
            success["fullname"] = success["employee_id"]

        fig_bubble = px.scatter(success,
                                x="iq", y="tiki",
                                size="success_score",
                                color="success_score",
                                hover_name="fullname",
                                title="IQ vs TIKI")
        fig_bubble.update_layout(height=520)
        st.plotly_chart(fig_bubble, use_container_width=True)

    # ----- Automated insight (IQ-TIKI) -----
    st.markdown("---")
    st.subheader("Automated insight")
    if 'corr' in locals() and not corr.empty and "iq" in corr.index and "tiki" in corr.columns:
        r = corr.loc["iq", "tiki"]
        if pd.isna(r):
            st.write("Correlation cannot be calculated (NaN).")
        elif abs(r) < 0.2:
            st.write(f"Korelasi IQ–TIKI = {r:.3f} → **Lemah**. Kedua pengukuran cenderung independen.")
        elif r > 0.2:
            st.write(f"Korelasi IQ–TIKI = {r:.3f} → **Positif**. IQ & TIKI cenderung meningkat bersama.")
        else:
            st.write(f"Korelasi IQ–TIKI = {r:.3f} → **Negatif**. IQ tinggi tidak menjamin TIKI tinggi.")
    else:
        st.info("Tidak ada korelasi yang valid untuk IQ dan TIKI berdasarkan benchmark saat ini.")
