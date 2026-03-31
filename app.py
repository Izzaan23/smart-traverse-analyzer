import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
import json

st.set_page_config(page_title="Smart Traverse Analyzer", layout="wide")

st.title("🧭 Smart Traverse Analyzer")
st.markdown("Kira Latit, Dipat, Pelarasan Bowditch, Keluasan (Shoelace) dan Plot Pelan secara automatik.")

# --- BAHAGIAN 1: INPUT MAKLUMAT ASAS ---
st.header("1. Maklumat Stesen & Koordinat Mula")
col1, col2 = st.columns(2)
start_n = col1.number_input("Koordinat Mula (Utara / N)", value=1000.000, format="%.3f")
start_e = col2.number_input("Koordinat Mula (Timur / E)", value=1000.000, format="%.3f")

# --- BAHAGIAN 2: INPUT DATA CERAPAN ---
st.header("2. Data Cerapan (Bearing & Jarak)")
st.info("Sila masukkan data traverse anda di dalam jadual di bawah. Tambah baris baru jika perlu.")

# Jadual lalai (Default data untuk rujukan)
default_data = pd.DataFrame({
    "Garisan": ["1-2", "2-3", "3-4", "4-1"],
    "Darjah": [45, 135, 225, 315],
    "Minit": [0, 0, 0, 0],
    "Saat": [0, 0, 0, 0],
    "Jarak (m)": [100.0, 100.0, 100.0, 100.0]
})

# Gunakan st.data_editor untuk membolehkan pengguna edit data secara terus di web
edited_df = st.data_editor(default_data, num_rows="dynamic", use_container_width=True)

# --- BAHAGIAN 3: PENGIRAAN & PROSES ---
if st.button("Kira Traverse & Jana Pelan", type="primary"):
    df = edited_df.copy()
    
    # 1. Tukar Bearing ke Decimal Degrees & Radians
    df['Decimal_Deg'] = df['Darjah'] + (df['Minit'] / 60) + (df['Saat'] / 3600)
    df['Radians'] = np.radians(df['Decimal_Deg'])
    
    # 2. Kira Latit (N/S) dan Dipat (E/W)
    df['Latit'] = df['Jarak (m)'] * np.cos(df['Radians'])
    df['Dipat'] = df['Jarak (m)'] * np.sin(df['Radians'])
    
    # Kira Tikaian Lurus (Misclosure)
    sum_latit = df['Latit'].sum()
    sum_dipat = df['Dipat'].sum()
    sum_jarak = df['Jarak (m)'].sum()
    
    misclosure = math.sqrt(sum_latit**2 + sum_dipat**2)
    
    # 3. Pelarasan Bowditch
    df['Koreksi_Latit'] = -(sum_latit * (df['Jarak (m)'] / sum_jarak))
    df['Koreksi_Dipat'] = -(sum_dipat * (df['Jarak (m)'] / sum_jarak))
    
    df['Latit_Laras'] = df['Latit'] + df['Koreksi_Latit']
    df['Dipat_Laras'] = df['Dipat'] + df['Koreksi_Dipat']
    
    # 4. Kira Koordinat Berlaras
    n_coords = [start_n]
    e_coords = [start_e]
    
    for i in range(len(df)):
        n_coords.append(n_coords[-1] + df['Latit_Laras'].iloc[i])
        e_coords.append(e_coords[-1] + df['Dipat_Laras'].iloc[i])
        
    # Masukkan koordinat ke dalam DataFrame untuk paparan
    df['Koordinat N'] = n_coords[1:]
    df['Koordinat E'] = e_coords[1:]
    
    # 5. Kira Keluasan menggunakan Formula Shoelace
    x = np.array(e_coords)
    y = np.array(n_coords)
    area = 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

    # --- BAHAGIAN 4: PAPARAN HASIL ---
    st.markdown("---")
    st.header("3. Hasil Analisis")
    
    col_res1, col_res2, col_res3 = st.columns(3)
    col_res1.metric("Jumlah Jarak Perimeter", f"{sum_jarak:.3f} m")
    col_res2.metric("Tikaian Lurus (Misclosure)", f"{misclosure:.4f} m")
    col_res3.metric("Keluasan Terkandung", f"{area:.3f} m²")
    
    st.subheader("Jadual Pelarasan Bowditch & Koordinat")
    # Format paparan jadual
    display_df = df[['Garisan', 'Jarak (m)', 'Latit', 'Dipat', 'Latit_Laras', 'Dipat_Laras', 'Koordinat N', 'Koordinat E']]
    st.dataframe(display_df.style.format(precision=3), use_container_width=True)
    
    # --- BAHAGIAN 5: PLOT VISUAL ---
    st.subheader("4. Pelan Plot Traverse")
    
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(e_coords, n_coords, marker='o', linestyle='-', color='b', linewidth=2, markersize=6)
    
    # Letak label titik
    for i, (txt_e, txt_n) in enumerate(zip(e_coords, n_coords)):
        ax.annotate(f"Stn {i+1}", (txt_e, txt_n), textcoords="offset points", xytext=(5,5), ha='center')
        
    ax.set_title("Plot Poligon Traverse")
    ax.set_xlabel("Timur (E)")
    ax.set_ylabel("Utara (N)")
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.set_aspect('equal') # Pastikan skala paksi X dan Y seimbang
    
    st.pyplot(fig)
    
    # --- BAHAGIAN 6: EKSPORT DATA ---
    st.subheader("5. Muat Turun Data")
    
    # Jana GeoJSON
    geojson_data = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[e, n] for e, n in zip(e_coords, n_coords)]]
            },
            "properties": {"name": "Traverse Plot", "area_sqm": area}
        }]
    }
    
    json_string = json.dumps(geojson_data)
    csv_string = display_df.to_csv(index=False).encode('utf-8')
    
    col_dl1, col_dl2 = st.columns(2)
    col_dl1.download_button(
        label="Muat Turun Laporan (CSV)",
        data=csv_string,
        file_name="laporan_traverse.csv",
        mime="text/csv"
    )
    col_dl2.download_button(
        label="Muat Turun Pelan (GeoJSON untuk QGIS)",
        data=json_string,
        file_name="pelan_traverse.geojson",
        mime="application/json"
    )
