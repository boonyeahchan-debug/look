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
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return f"{d}°{m:02d}'{sd:02.0f}\""

# ================= SIDEBAR =================
with st.sidebar:
    st.header("⚙️ Tetapan Peta")
    st.info("Pastikan unit E & N dalam METER (EPSG:4390)")
    
    show_satellite = st.checkbox("Paparan Satelit", value=True)
    
    # Pilihan Provider jika satu tidak berfungsi
    map_provider = st.selectbox("Penyedia Satelit", 
                                ["Esri.WorldImagery", "OpenStreetMap.Mapnik", "CartoDB.Positron"])
    
    show_labels = st.checkbox("Papar Bearing & Jarak", value=True)
    show_area = st.checkbox("Papar Luas", value=True)
    
    zoom_margin = st.slider("Margin Zoom (Meter)", 0, 1000, 200, 50)

# ================= MAIN INTERFACE =================
st.title("🗺️ WebGIS: Visual Satelit EPSG:4390")

uploaded_file = st.file_uploader("Upload CSV (E, N dalam Meter)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    if {"E", "N"}.issubset(df.columns):
        # 1. Bina Data Asal (Kertau 4390)
        coords = list(zip(df["E"], df["N"]))
        poly_orig = Polygon(coords)
        gdf_4390 = gpd.GeoDataFrame(geometry=[poly_orig], crs="EPSG:4390")
        
        # Kira Luas (Guna 4390 untuk ketepatan)
        area_4390 = gdf_4390.geometry.area.iloc[0]
        
        # 2. Tukar ke Web Mercator (3857) - WAJIB untuk Basemap
        gdf_3857 = gdf_4390.to_crs(epsg=3857)
        poly_3857 = gdf_3857.geometry.iloc[0]

        # 3. Plotting
        fig, ax = plt.subplots(figsize=(10, 10))
        
        # Plot Polygon
        gdf_3857.plot(ax=ax, edgecolor="red", facecolor="none", linewidth=2.5, zorder=15)

        if show_satellite:
            try:
                # Memanggil provider secara dinamik berdasarkan pilihan sidebar
                source = eval(f"cx.providers.{map_provider}")
                cx.add_basemap(ax, source=source)
            except Exception as e:
                st.error(f"Peta gagal dimuatkan: {e}")

        # 4. Labeling (Value 4390, Lokasi 3857)
        pts_3857 = list(poly_3857.exterior.coords)
        pts_4390 = list(poly_orig.exterior.coords)

        if show_labels:
            for i in range(len(pts_4390) - 1):
                p1, p2 = pts_4390[i], pts_4390[i+1]
                dist = np.hypot(p2[0]-p1[0], p2[1]-p1[1])
                bearing = format_to_dms(np.degrees(np.arctan2(p2[0]-p1[0], p2[1]-p1[1])) % 360)
                
                # Kedudukan pada peta visual
                p1v, p2v = pts_3857[i], pts_3857[i+1]
                mx, my = (p1v[0]+p2v[0])/2, (p1v[1]+p2v[1])/2
                
                ax.text(mx, my, f"{dist:.2f}m\n{bearing}", color="yellow", fontsize=8, 
                        fontweight="bold", ha="center", bbox=dict(facecolor='black', alpha=0.5))

        if show_area:
            c = poly_3857.centroid
            ax.text(c.x, c.y, f"LUAS (4390)\n{area_4390:.2f} m²", color="white", 
                    ha="center", fontweight="bold", bbox=dict(facecolor="red", alpha=0.7))

        # Set Zoom Extent
        bounds = gdf_3857.total_bounds
        ax.set_xlim(bounds[0] - zoom_margin, bounds[2] + zoom_margin)
        ax.set_ylim(bounds[1] - zoom_margin, bounds[3] + zoom_margin)
        ax.set_axis_off()
        
        st.pyplot(fig)
    else:
        st.error("Sila pastikan kolum CSV bertajuk 'E' dan 'N'.")
