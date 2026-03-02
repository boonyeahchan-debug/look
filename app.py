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
st.set_page_config(layout="wide", page_title="WebGIS Malaysia")

# Membaiki ralat CSS / Markdown
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button { width: 100%; border-radius: 5px; background-color: #007bff; color: white; }
    </style>
    """, unsafe_allow_html=True)

# ================= 2. UTILITIES =================
def format_to_dms(deg):
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return f"{d}°{m:02d}'{sd:02.0f}\""

# ================= 3. SIDEBAR (Task 4) =================
with st.sidebar:
    st.header("🛰️ Tetapan Sistem")
    epsg_code = st.text_input("Sistem Koordinat Asal (EPSG)", value="4390")
    
    st.subheader("Kawalan Paparan")
    show_satellite = st.checkbox("Paparan Satelit", value=True)
    show_stn = st.checkbox("Label Stesen (STN)", value=True)
    show_labels = st.checkbox("Bearing & Jarak", value=True)
    show_area = st.checkbox("Label Luas", value=True)
    
    zoom_margin = st.slider("Margin Zoom (Meter)", 0, 200, 50, 10)

# ================= 4. MAIN INTERFACE =================
st.title("🗺️ WebGIS: Plotting Polygon EPSG:4390")

uploaded_file = st.file_uploader("Muat naik fail CSV (Kolum E, N)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    if {"E", "N"}.issubset(df.columns):
        # --- TASK 1: GEOMETRY & AREA ---
        coords = list(zip(df["E"], df["N"]))
        poly_geom = Polygon(coords)
        gdf = gpd.GeoDataFrame(geometry=[poly_geom], crs=f"EPSG:{epsg_code}")
        
        area_sqm = gdf.geometry.area.iloc[0]
        
        col_data, col_map = st.columns([1, 2])
        
        with col_data:
            st.success(f"Luas: {area_sqm:.2f} m²")
            st.write("Data Koordinat:")
            st.dataframe(df)

            # --- TASK 2: EXPORT ---
            st.subheader("📥 Eksport")
            # GeoJSON
            st.download_button("Download GeoJSON", gdf.to_json(), "data.geojson", "application/json")
            
            # Shapefile
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as zf:
                gdf.to_file("temp.shp")
                for ext in ["shp", "shx", "dbf", "prj"]:
                    if os.path.exists(f"temp.{ext}"):
                        zf.write(f"temp.{ext}")
                        os.remove(f"temp.{ext}")
            st.download_button("Download Shapefile (.zip)", buf.getvalue(), "data_shp.zip")

        with col_map:
            # --- TASK 3: SATELLITE OVERLAY ---
            gdf_3857 = gdf.to_crs(epsg=3857)
            fig, ax = plt.subplots(figsize=(10, 10))
            
            fill = "none" if show_satellite else "lightblue"
            gdf_3857.plot(ax=ax, edgecolor="red", facecolor=fill, linewidth=2, zorder=10)

            if show_satellite:
                try:
                    cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, crs=gdf_3857.crs.to_string())
                except:
                    st.warning("Satelit tidak dapat dimuatkan.")

            # --- TASK 4: LABELS ---
            pts_3857 = list(gdf_3857.geometry.iloc[0].exterior.coords)
            pts_orig = list(poly_geom.exterior.coords)

            for i, p in enumerate(pts_3857[:-1]):
                ax.scatter(p[0], p[1], color="yellow", s=30, zorder=20)
                if show_stn:
                    ax.text(p[0], p[1], f" STN {i+1}", color="white", fontsize=9, fontweight="bold")

            if show_labels:
                for i in range(len(pts_orig) - 1):
                    p1_o, p2_o = pts_orig[i], pts_orig[i+1]
                    dist = np.hypot(p2_o[0] - p1_o[0], p2_o[1] - p1_o[1])
                    bearing = format_to_dms(np.degrees(np.arctan2(p2_o[0]-p1_o[0], p2_o[1]-p1_o[1])) % 360)
                    
                    p1_m, p2_m = pts_3857[i], pts_3857[i+1]
                    mx, my = (p1_m[0]+p2_m[0])/2, (p1_m[1]+p2_m[1])/2
                    ax.text(mx, my, f"{dist:.1f}m\n{bearing}", color="lime", fontsize=8, ha="center", 
                            bbox=dict(facecolor='black', alpha=0.4, edgecolor='none'))

            if show_area:
                c = gdf_3857.geometry.iloc[0].centroid
                ax.text(c.x, c.y, f"LUAS\n{area_sqm:.2f} m²", color="white", ha="center", 
                        bbox=dict(facecolor="red", alpha=0.5))

            bounds = gdf_3857.total_bounds
            ax.set_xlim(bounds[0]-zoom_margin, bounds[2]+zoom_margin)
            ax.set_ylim(bounds[1]-zoom_margin, bounds[3]+zoom_margin)
            ax.set_axis_off()
            st.pyplot(fig)
    else:
        st.error("Format CSV salah. Perlu kolum 'E' dan 'N'.")
