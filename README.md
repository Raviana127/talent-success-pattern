# 🎯 Talent Success Pattern Dashboard

**Talent Success Pattern Dashboard** adalah aplikasi interaktif berbasis Streamlit yang digunakan untuk menganalisis dan menemukan pola keberhasilan karyawan berdasarkan **rating performa, kompetensi, strengths, dan profil psikometrik (IQ & TIKI)**.  
Aplikasi ini juga memungkinkan user untuk **membuat benchmark baru** berdasarkan role, job level, dan role purpose yang diinput secara langsung.

---

## 🚀 Fitur Utama

✅ Terhubung langsung ke **Supabase Database**  
✅ Input form untuk membuat **job benchmark baru**:
- Role Name → diambil dari tabel `dim_departments`
- Job Level → diambil dari tabel `dim_grades`
- Role Purpose → input manual
- Benchmark → memilih karyawan rating tinggi sebagai acuan

✅ Dashboard interaktif menampilkan:
- **Top Strengths Karyawan Rating 5**
- **Perbandingan Kompetensi (Radar Chart)**
- **Heatmap Psikometrik (IQ vs TIKI dan lainnya)**
- **Talent Mapping (Bubble Chart Success Score)**
- **Insight otomatis korelasi IQ & TIKI**

✅ Otomatis menyimpan input user ke tabel `talent_benchmarks` di Supabase.

---

## 🧩 Tech Stack

| Komponen | Teknologi |
|-----------|------------|
| UI Framework | Streamlit |
| Database | Supabase (PostgreSQL) |
| Data Visualization | Plotly Express |
| Bahasa | Python 3.x |
| Source Control | GitHub |

---

## 🗂️ Struktur Project


---

## ⚙️ Cara Menjalankan di Lokal

### 1️⃣ Clone Repository
```bash
git clone https://github.com/Raviana127/talent-success-pattern.git
cd talent-success-pattern

python -m venv venv
venv\Scripts\activate      # Windows
# atau
source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
pip install streamlit plotly pandas supabase
streamlit run app2.py

