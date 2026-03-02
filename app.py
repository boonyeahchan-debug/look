import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon
import matplotlib.pyplot as plt
import numpy as np
import io
import zipfile
import os
import contextily as cx

# ================= 1. CONFIGURATION =================
st.set_page_config(layout="wide", page_title="WebGIS WGS84 & Kertau")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# ================= 2. UTILITIES =================
def format_to_dms(deg):
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return f"{d}°{m:02d}'{sd:02.0f}\""

# ================= 3. SIDEBAR =================
with st.sidebar:
    st.header("⚙️ Tetapan Koordinat")
    # User input coordinates are treated as 4390
    st.info("Input: EPSG:4390 (Kertau)\nDisplay: WGS 84 (Satelit)")
    
    st.subheader("Kawalan Lapisan")
    show_satellite = st.checkbox("Paparan Satelit", value=True)
    show_labels = st.checkbox("Bearing & Jarak (Value 4390)", value=True)
    show_area = st.checkbox("Label Luas (Value 4390)", value=True)
    
    zoom_margin = st.slider("Margin Zoom (Meter)", 0, 200, 50, 10)

# ================= 4. MAIN INTERFACE =================
st.title("🗺️ WebGIS: Visual WGS 84 | Data EPSG:4390")

uploaded_file = st.file_uploader("Muat naik fail CSV (Kolum E, N dalam format Kertau)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    if {"E", "N"}.issubset(df.columns):
        # --- LANGKAH A: BINA GEOMETRI ASAL (EPSG:4390) ---
        coords = list(zip(df["E"], df["N"]))
        poly_orig = Polygon(coords)
        gdf_4390 = gpd.GeoDataFrame(geometry=[poly_orig], crs="EPSG:4390")
        
        # Pengiraan Luas Sebenar (Guna 4390)
        area_4390 = gdf_4390.geometry.area.iloc[0]
        
        # --- LANGKAH B: REPROJECT UNTUK VISUAL (WGS 84 / 3857) ---
        # Kita guna 3857 untuk plotting supaya basemap satelit tidak herot
        gdf_visual = gdf_4390.to_crs(epsg=3857)
        poly_visual = gdf_visual.geometry.iloc[0]
        
        # Paparan Metrik
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Luas (Kertau 4390)", f"{area_4390:.2f} m²")
        col_m2.metric("Sistem Visual", "WGS 84 / Web Mercator")

        col_data, col_map = st.columns([1, 2])
        
        with col_data:
            st.write("Senarai Koordinat (E, N):")
            st.dataframe(df, height=250)
            
            # Export (Tetap kekalkan 4390 untuk profesional)
            st.subheader("📥 Eksport")
            st.download_button("Download GeoJSON (4390)", gdf_4390.to_json(), "kertau_data.geojson")

        with col_map:
            fig, ax = plt.subplots(figsize=(10, 10))
            
            # Plot Polygon Visual
            gdf_visual.plot(ax=ax, edgecolor="red", facecolor="none", linewidth=2, zorder=10)

            # Task 3: Basemap Satelit (WGS 84 / 3857 compatible)
            if show_satellite:
                try:
                    cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery)
                except:
                    st.warning("Satelit offline.")

            # --- TASK 4: LABELS (VALUE DARI 4390, POSISI PADA VISUAL) ---
            pts_visual = list(poly_visual.exterior.coords)
            pts_4390 = list(poly_orig.exterior.coords)

            if show_labels:
                for i in range(len(pts_4390) - 1):
                    # Kira Jarak & Bearing menggunakan titik ASAL (4390)
                    p1_4390, p2_4390 = pts_4390[i], pts_4390[i+1]
                    dist = np.hypot(p2_4390[0] - p1_4390[0], p2_4390[1] - p1_4390[1])
                    bearing = format_to_dms(np.degrees(np.arctan2(p2_4390[0]-p1_4390[0], p2_4390[1]-p1_4390[1])) % 360)
                    
                    # Tentukan kedudukan teks pada koordinat VISUAL
                    p1_v, p2_v = pts_visual[i], pts_visual[i+1]
                    mx, my = (p1_v[0]+p2_v[0])/2, (p1_v[1]+p2_v[1])/2
                    
                    ax.text(mx, my, f"{dist:.2f}m\n{bearing}", color="yellow", fontsize=8, 
                            fontweight="bold", ha="center", 
                            bbox=dict(facecolor='black', alpha=0.6, edgecolor='none'))

            if show_area:
                c_v = poly_visual.centroid
                ax.text(c_v.x, c_v.y, f"LUAS (4390)\n{area_4390:.2f} m²", 
                        color="white", ha="center", fontweight="bold",
                        bbox=dict(facecolor="red", alpha=0.7, boxstyle="round"))

            # Set extent
            bounds = gdf_visual.total_bounds
            ax.set_xlim(bounds[0]-zoom_margin, bounds[2]+zoom_margin)
            ax.set_ylim(bounds[1]-zoom_margin, bounds[3]+zoom_margin)
            ax.set_axis_off()
            st.pyplot(fig)
    else:
        st.error("Pastikan CSV ada kolum E dan N.")
