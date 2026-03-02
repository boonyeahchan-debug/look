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
st.set_page_config(layout="wide", page_title="WebGIS Google Satellite")

# ================= 2. UTILITIES =================
def format_to_dms(deg):
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return f"{d}°{m:02d}'{sd:02.0f}\""

# URL XYZ untuk Google Satellite
GOOGLE_SATELLITE_URL = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"

# ================= 3. SIDEBAR =================
with st.sidebar:
    st.header("⚙️ Tetapan Lapisan")
    st.subheader("Google Maps Satellite")
    show_labels = st.checkbox("Papar Bearing & Jarak", value=True)
    show_area = st.checkbox("Papar Luas (4390)", value=True)
    zoom_margin = st.slider("Margin Zoom (Meter)", 0, 1000, 100, 50)
    
    st.markdown("---")
    st.info("Nota: Koordinat input mestilah dalam unit Meter (EPSG:4390 Kertau RSO).")

# ================= 4. MAIN INTERFACE =================
st.title("🗺️ WebGIS: Google Satellite Layer (EPSG:4390)")

uploaded_file = st.file_uploader("Upload CSV (Kolum E, N)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    if {"E", "N"}.issubset(df.columns):
        # --- PROSES DATA (EPSG:4390) ---
        coords = list(zip(df["E"], df["N"]))
        poly_orig = Polygon(coords)
        gdf_4390 = gpd.GeoDataFrame(geometry=[poly_orig], crs="EPSG:4390")
        
        # Kira Luas Sebenar
        area_4390 = gdf_4390.geometry.area.iloc[0]
        
        # --- REPROJECT UNTUK GOOGLE MAPS (EPSG:3857) ---
        gdf_3857 = gdf_4390.to_crs(epsg=3857)
        poly_3857 = gdf_3857.geometry.iloc[0]

        # --- PLOTTING ---
        fig, ax = plt.subplots(figsize=(10, 10))
        
        # Lukis Polygon
        gdf_3857.plot(ax=ax, edgecolor="#FF0000", facecolor="none", linewidth=2.5, zorder=20)

        # Tambah Google Satellite Menggunakan URL XYZ
        try:
            cx.add_basemap(ax, source=GOOGLE_SATELLITE_URL, zoom='auto')
        except Exception as e:
            st.error(f"Gagal memuatkan Google Satellite: {e}")

        # --- LABELS (Value 4390, Kedudukan 3857) ---
        pts_3857 = list(poly_3857.exterior.coords)
        pts_4390 = list(poly_orig.exterior.coords)

        if show_labels:
            for i in range(len(pts_4390) - 1):
                # Kira Jarak & Bearing (Kertau)
                p1, p2 = pts_4390[i], pts_4390[i+1]
                dist = np.hypot(p2[0]-p1[0], p2[1]-p1[1])
                bearing = format_to_dms(np.degrees(np.arctan2(p2[0]-p1[0], p2[1]-p1[1])) % 360)
                
                # Plot pada posisi 3857
                p1v, p2v = pts_3857[i], pts_3857[i+1]
                mx, my = (p1v[0]+p2v[0])/2, (p1v[1]+p2v[1])/2
                
                ax.text(mx, my, f"{dist:.2f}m\n{bearing}", color="#FFFF00", fontsize=8, 
                        fontweight="bold", ha="center", va="center",
                        bbox=dict(facecolor='black', alpha=0.5, edgecolor='none', pad=2))

        if show_area:
            c = poly_3857.centroid
            ax.text(c.x, c.y, f"LUAS (4390)\n{area_4390:.2f} m²", color="white", 
                    ha="center", va="center", fontweight="bold", fontsize=12,
                    bbox=dict(facecolor="#FF0000", alpha=0.7, boxstyle="round,pad=0.5"))

        # Set Zoom Extent
        bounds = gdf_3857.total_bounds
        ax.set_xlim(bounds[0] - zoom_margin, bounds[2] + zoom_margin)
        ax.set_ylim(bounds[1] - zoom_margin, bounds[3] + zoom_margin)
        ax.set_axis_off()
        
        st.pyplot(fig)
    else:
        st.error("Ralat: Fail CSV mesti mempunyai kolum 'E' dan 'N'.")
