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
st.set_page_config(layout="wide", page_title="WebGIS Kertau 4390")

# ================= 2. UTILITIES =================
def format_to_dms(deg):
    """Format decimal degrees to DMS for plan labeling."""
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return f"{d}°{m:02d}'{sd:02.0f}\""

# URL XYZ for Google Satellite
GOOGLE_SATELLITE_URL = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"

# ================= 3. SIDEBAR =================
with st.sidebar:
    st.header("⚙️ Map Settings")
    st.info("Input & Calculations: EPSG:4390\nDisplay: Web Mercator (3857)")
    
    # Layer Controls
    show_labels = st.checkbox("Show Bearing & Distance", value=True)
    show_area = st.checkbox("Show Area Label", value=True)
    
    st.markdown("---")
    zoom_margin = st.slider("Zoom Margin (Meters)", 0, 1000, 200, 50)

# ================= 4. MAIN INTERFACE =================
st.title("🗺️ Polygon Plotting System (EPSG:4390)")

uploaded_file = st.file_uploader("Upload CSV (E, N columns in meters)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    if {"E", "N"}.issubset(df.columns):
        # --- 1. ORIGINAL GEOMETRY (EPSG:4390) ---
        coords = list(zip(df["E"], df["N"]))
        poly_orig = Polygon(coords)
        gdf_4390 = gpd.GeoDataFrame(geometry=[poly_orig], crs="EPSG:4390")
        
        # Real Area Calculation (Kertau RSO)
        area_4390 = gdf_4390.geometry.area.iloc[0]
        
        # --- 2. REPROJECTION FOR VISUALIZATION (EPSG:3857) ---
        # Contextily satellite tiles require EPSG:3857 for correct alignment
        gdf_3857 = gdf_4390.to_crs(epsg=3857)
        poly_3857 = gdf_3857.geometry.iloc[0]

        # --- 3. PLOTTING ---
        fig, ax = plt.subplots(figsize=(10, 10))
        
        # Plot Polygon (Using visual 3857 coordinates)
        gdf_3857.plot(ax=ax, edgecolor="#FF0000", facecolor="none", linewidth=2.5, zorder=20)

        # Add Google Satellite using XYZ URL with zoom adjustment to prevent 404s
        try:
            cx.add_basemap(ax, source=GOOGLE_SATELLITE_URL, zoom='auto', zoom_adjust=-2)
        except Exception as e:
            st.warning(f"Satellite map failed to load: {e}")

        # --- 4. LABELING (Hybrid Logic) ---
        pts_3857 = list(poly_3857.exterior.coords)
        pts_4390 = list(poly_orig.exterior.coords)

        # Labels for Bearing & Distance (Value from 4390, Position on 3857)
        if show_labels:
            for i in range(len(pts_4390) - 1):
                p1_43, p2_43 = pts_4390[i], pts_4390[i+1]
                dist = np.hypot(p2_43[0] - p1_43[0], p2_43[1] - p1_43[1])
                bearing = format_to_dms(np.degrees(np.arctan2(p2_43[0]-p1_43[0], p2_43[1]-p1_43[1])) % 360)
                
                # Text location on map (3857)
                p1_38, p2_38 = pts_3857[i], pts_3857[i+1]
                mx, my = (p1_38[0]+p2_38[0])/2, (p1_38[1]+p2_38[1])/2
                
                ax.text(mx, my, f"{dist:.2f}m\n{bearing}", color="#FFFF00", fontsize=8, 
                        fontweight="bold", ha="center", va="center",
                        bbox=dict(facecolor='black', alpha=0.5, edgecolor='none'))

        # Area Label
        if show_area:
            centroid = poly_3857.centroid
            ax.text(centroid.x, centroid.y, f"LUAS \n{area_4390:.2f} m²", 
                    color="white", ha="center", fontweight="bold",
                    bbox=dict(facecolor="#FF0000", alpha=0.7, boxstyle="round,pad=0.3"))

        # --- 5. EXTENT & DISPLAY ---
        bounds = gdf_3857.total_bounds
        ax.set_xlim(bounds[0] - zoom_margin, bounds[2] + zoom_margin)
        ax.set_ylim(bounds[1] - zoom_margin, bounds[3] + zoom_margin)
        ax.set_axis_off()
        
        st.pyplot(fig)
        
        # Export (Task 2)
        st.download_button("Download GeoJSON (Kertau)", gdf_4390.to_json(), "lot_kertau.geojson")
    else:
        st.error("CSV file does not contain 'E' and 'N' columns.")
