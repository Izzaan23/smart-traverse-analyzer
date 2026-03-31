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

default_data = pd.DataFrame({
    "Garisan": ["1-2", "2-3", "3-4", "4-1"],
    "Darjah": [45, 135, 225, 315],
    "Minit": [0, 0, 0, 0],
    "Saat": [0, 0, 0, 0],
    "Jarak (m)": [100.0, 100.0, 100.0, 100.0]
})

edited_df = st.data_editor(default_data, num_rows="dynamic", use_container_width=True)

# --- BAHAGIAN 3: PENGIRAAN & PROSES ---
if st.button("Kira Traverse & Jana Pelan", type="primary"):
    # Pembersihan data
    df = edited_df.dropna(subset=['Darjah', 'Minit', 'Saat', 'Jarak (m)']).copy()
    cols_to_fix = ['Darjah', 'Minit', 'Saat', 'Jarak (m)']
    for col in cols_to_fix:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=cols_to_fix)

    if not df.empty:
        # 1. Tukar Bearing ke Decimal Degrees & Radians
        df['Decimal_Deg'] = df['Darjah'] + (df['Minit'] / 60) + (df['Saat'] / 3600)
        df['Radians'] = np.radians(df['Decimal_Deg'].astype(float))
        
        # 2. Kira Latit (N/S) dan Dipat (E/W)
        df['Latit'] = df['Jarak (m)'] * np.cos(df['Radians'])
        df['Dipat'] = df['Jarak (m)'] * np.sin(df['Radians'])
        
        # Kira Tikaian Lurus (Misclosure)
        sum_latit = df['Latit'].sum()
        sum_dipat = df['Dipat'].sum()
        sum_jarak = df['Jarak (m)'].sum()
        
        misclosure = math.sqrt(sum_latit**2 + sum_dipat**2)
        
        # --- PENGIRAAN NISBAH TIKAIAN (1 : X) ---
        if misclosure > 0:
            ratio_val = sum_jarak / misclosure
            # Dibundarkan kepada nombor bulat terdekat
            misclosure_ratio = f"1 : {int(round(ratio_val))}"
        else:
            misclosure_ratio = "1 : 0 (Sempurna)"
        
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
            
        df['Koordinat N'] = n_coords[1:]
        df['Koordinat E'] = e_coords[1:]
        
        # 5. Kira Keluasan (Shoelace)
        x_area = np.array(e_coords)
        y_area = np.array(n_coords)
        area = 0.5 * np.abs(np.dot(x_area, np.roll(y_area, 1)) - np.dot(y_area, np.roll(x_area, 1)))

        # --- BAHAGIAN 4: PAPARAN HASIL ---
        st.markdown("---")
        st.header("3. Hasil Analisis")
        
        col_res1, col_res2, col_res3, col_res4 = st.columns(4)
        col_res1.metric("Jumlah Jarak", f"{sum_jarak:.3f} m")
        col_res2.metric("Tikaian Lurus", f"{misclosure:.4f} m")
        col_res3.metric("Nisbah Tikaian", misclosure_ratio)
        col_res4.metric("Keluasan", f"{area:.3f} m²")
        
        st.subheader("Jadual Pelarasan Bowditch & Koordinat")
        display_df = df[['Garisan', 'Jarak (m)', 'Latit', 'Dipat', 'Latit_Laras', 'Dipat_Laras', 'Koordinat N', 'Koordinat E']]
        st.dataframe(display_df.style.format(precision=3), use_container_width=True)
        
        # --- BAHAGIAN 5: PLOT VISUAL (PEMBETULAN POLIGON) ---
        st.subheader("4. Pelan Plot Traverse")
        
        fig, ax = plt.subplots(figsize=(8, 6))
        
        # Supaya poligon nampak tertutup, kita sambung koordinat akhir ke koordinat asal
        plot_e = e_coords + [e_coords[0]]
        plot_n = n_coords + [n_coords[0]]
        
        ax.plot(plot_e, plot_n, marker='o', linestyle='-', color='b', linewidth=2, markersize=6)
        
        # Labelkan setiap stesen
        for i, (txt_e, txt_n) in enumerate(zip(e_coords, n_coords)):
            # Jika titik terakhir sama dengan titik pertama, kita label sekali sahaja
            if i < len(e_coords) - 1 or i == 0:
                ax.annotate(f"Stn {i+1}", (txt_e, txt_n), textcoords="offset points", xytext=(5,5), ha='center')
            
        ax.set_title("Plot Poligon Tertutup (Laras)")
        ax.set_xlabel("Timur (E)")
        ax.set_ylabel("Utara (N)")
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.set_aspect('equal')
        
        st.pyplot(fig)
        
        # --- BAHAGIAN 6: EKSPORT DATA ---
        st.subheader("5. Muat Turun Data")
        
        geojson_data = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[e, n] for e, n in zip(plot_e, plot_n)]]
                },
                "properties": {"name": "Traverse Plot", "area_sqm": area, "misclosure_ratio": misclosure_ratio}
            }]
        }
        
        json_string = json.dumps(geojson_data)
        csv_string = display_df.to_csv(index=False).encode('utf-8')
        
        col_dl1, col_dl2 = st.columns(2)
        col_dl1.download_button("Muat Turun Laporan (CSV)", data=csv_string, file_name="laporan_traverse.csv", mime="text/csv")
        col_dl2.download_button("Muat Turun Pelan (GeoJSON)", data=json_string, file_name="pelan_traverse.geojson", mime="application/json")
    else:
        st.error("Sila isi data cerapan yang sah.")
