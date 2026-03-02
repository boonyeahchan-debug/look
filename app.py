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

# ================= CONFIGURATION =================
st.set_page_config(layout="wide", page_title="WebGIS Kertau 4390")

# ================= UTILITIES =================
def format_to_dms(deg):
    """Format darjah ke DMS untuk label pelan."""
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return f"{d}°{m:02d}'{sd:02.0f}\""

# ================= SIDEBAR (Task 4) =================
with st.sidebar:
    st.header("⚙️ Tetapan WebGIS")
    st.info("Input & Pengiraan: EPSG:4390\nPaparan: Web Mercator (3857)")
    
    # Kawalan Lapisan
    show_satellite = st.checkbox("Paparan Satelit", value=True)
    show_stn = st.checkbox("Papar Label Stesen", value=True)
    show_labels = st.checkbox("Papar Bearing & Jarak", value=True)
    show_area = st.checkbox("Papar Label Luas", value=True)
    
    st.markdown("---")
    zoom_margin = st.slider("Margin Zoom (Meter)", 0, 500, 100, 10)

# ================= MAIN INTERFACE =================
st.title("🗺️ Sistem Plotting Polygon (EPSG:4390)")

uploaded_file = st.file_uploader("Upload CSV (Kolum E, N dalam unit meter)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    if {"E", "N"}.issubset(df.columns):
        # --- 1. GEOMETRI ASAL (EPSG:4390) ---
        coords = list(zip(df["E"], df["N"]))
        poly_orig = Polygon(coords)
        gdf_4390 = gpd.GeoDataFrame(geometry=[poly_orig], crs="EPSG:4390")
        
        # Pengiraan Luas Sebenar (Kertau RSO)
        area_4390 = gdf_4390.geometry.area.iloc[0]
        
        # --- 2. REPROJEKSI UNTUK VISUAL (EPSG:3857) ---
        # Jubin satelit contextily memerlukan EPSG:3857 supaya tidak ralat
        gdf_3857 = gdf_4390.to_crs(epsg=3857)
        poly_3857 = gdf_3857.geometry.iloc[0]

        # --- 3. PLOTTING ---
        fig, ax = plt.subplots(figsize=(10, 10))
        
        # Lukis Polygon (Guna koordinat visual 3857)
        fill_opt = "none" if show_satellite else "lightblue"
        gdf_3857.plot(ax=ax, edgecolor="red", facecolor=fill_opt, linewidth=2.5, zorder=10)

        # Tambah Basemap Satelit
        if show_satellite:
            try:
                # Source Esri.WorldImagery sangat stabil untuk RSO Malaya
                cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery)
            except Exception as e:
                st.warning(f"Satelit gagal dimuat: {e}")

        # --- 4. LABELING (Logic Hybrid) ---
        pts_3857 = list(poly_3857.exterior.coords)
        pts_4390 = list(poly_orig.exterior.coords)

        # Label Bearing & Jarak (Value dari 4390, Lokasi pada 3857)
        if show_labels:
            for i in range(len(pts_4390) - 1):
                p1_43, p2_43 = pts_4390[i], pts_4390[i+1]
                dist = np.hypot(p2_43[0] - p1_43[0], p2_43[1] - p1_43[1])
                bearing = format_to_dms(np.degrees(np.arctan2(p2_43[0]-p1_43[0], p2_43[1]-p1_43[1])) % 360)
                
                # Lokasi teks pada peta (3857)
                p1_38, p2_38 = pts_3857[i], pts_3857[i+1]
                mx, my = (p1_38[0]+p2_38[0])/2, (p1_38[1]+p2_38[1])/2
                
                ax.text(mx, my, f"{dist:.2f}m\n{bearing}", color="yellow", fontsize=8, 
                        fontweight="bold", ha="center", va="center",
                        bbox=dict(facecolor='black', alpha=0.5, edgecolor='none'))

        # Label Luas
        if show_area:
            centroid = poly_3857.centroid
            ax.text(centroid.x, centroid.y, f"LUAS (4390)\n{area_4390:.2f} m²", 
                    color="white", ha="center", fontweight="bold",
                    bbox=dict(facecolor="red", alpha=0.7, boxstyle="round,pad=0.3"))

        # --- 5. EXTENT & DISPLAY ---
        bounds = gdf_3857.total_bounds
        ax.set_xlim(bounds[0] - zoom_margin, bounds[2] + zoom_margin)
        ax.set_ylim(bounds[1] - zoom_margin, bounds[3] + zoom_margin)
        ax.set_axis_off()
        
        st.pyplot(fig)
        
        # Eksport (Task 2)
        st.download_button("Download GeoJSON (Kertau)", gdf_4390.to_json(), "lot_kertau.geojson")
    else:
        st.error("Fail CSV tidak mengandungi lajur 'E' dan 'N'.")
