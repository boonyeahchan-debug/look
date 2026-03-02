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
from PIL import Image

# ================= CONFIGURATION =================
st.set_page_config(layout="wide", page_title="WebGIS Malaysia")

# CSS untuk mencantikkan paparan
st.markdown("""
    <style>
    .main { backgroundColor: #f0f2f6; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    </style>
    """, unsafe_allow_选取=True)

# ================= UTILITIES =================
def format_to_dms(deg):
    """Tukar darjah decimal ke format DMS (D°M'S\")"""
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return f"{d}°{m:02d}'{sd:02.0f}\""

# ================= SIDEBAR (Task 4) =================
with st.sidebar:
    st.header("🛰️ Tetapan Sistem")
    st.markdown("---")
    
    # Input EPSG (Default 4390 untuk Kertau RSO)
    epsg_code = st.text_input("Sistem Koordinat (EPSG)", value="4390")
    
    st.subheader("Kawalan Lapisan (On/Off)")
    show_satellite = st.checkbox("Paparan Satelit", value=True)
    show_stn = st.checkbox("Label Stesen (STN)", value=True)
    show_labels = st.checkbox("Bearing & Jarak", value=True)
    show_area = st.checkbox("Label Luas", value=True)
    
    st.markdown("---")
    zoom_margin = st.sidebar.slider("Margin Zoom (Meter)", 0, 500, 50, 10)

# ================= MAIN INTERFACE =================
st.title("🗺️ WebGIS: Plotting Polygon & Analisis Tanah")
st.info("Sila muat naik fail CSV yang mengandungi kolum **E** (Easting) dan **N** (Northing).")

uploaded_file = st.file_uploader("Pilih Fail CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    col_data, col_map = st.columns([1, 2])

    with col_data:
        st.subheader("📊 Data Mentah")
        st.dataframe(df, height=300)
        
        if {"E", "N"}.issubset(df.columns):
            # --- PEMPROSESAN GEOMETRI (Task 1) ---
            coords = list(zip(df["E"], df["N"]))
            poly_geom = Polygon(coords)
            
            # GeoDataFrame Asal (EPSG:4390)
            gdf = gpd.GeoDataFrame(geometry=[poly_geom], crs=f"EPSG:{epsg_code}")
            
            # Kira Luas Asal
            area_sqm = gdf.geometry.area.iloc[0]
            area_acre = area_sqm * 0.000247105 # Tukar ke Ekar jika perlu
            
            st.success(f"Luas Polygon: **{area_sqm:.3f} m²**")

            # --- EKSPORT (Task 2) ---
            st.subheader("📥 Eksport Data")
            
            # 1. GeoJSON
            st.download_button(
                "Muat Turun GeoJSON",
                gdf.to_json(),
                "polygon_data.geojson",
                "application/json"
            )
            
            # 2. Shapefile (ZIP)
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "x") as zf:
                gdf.to_file("temp.shp")
                for ext in ["shp", "shx", "dbf", "prj"]:
                    if os.path.exists(f"temp.{ext}"):
                        zf.write(f"temp.{ext}")
                        os.remove(f"temp.{ext}")
            
            st.download_button(
                "Muat Turun Shapefile (.zip)",
                buf.getvalue(),
                "polygon_shp.zip",
                "application/zip"
            )

    with col_map:
        st.subheader("🗺️ Visualisasi Peta")
        
        # --- REPROJECT KE 3857 UNTUK SATELIT (Task 3) ---
        gdf_3857 = gdf.to_crs(epsg=3857)
        poly_3857 = gdf_3857.geometry.iloc[0]
        
        fig, ax = plt.subplots(figsize=(10, 10))
        
        # Plot Polygon
        fill_color = "none" if show_satellite else "lightblue"
        gdf_3857.plot(ax=ax, edgecolor="red", facecolor=fill_color, linewidth=2, alpha=0.7, zorder=10)

        # Overlay Satelit
        if show_satellite:
            try:
                cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, crs=gdf_3857.crs.to_string())
            except Exception as e:
                st.error(f"Gagal memuatkan satelit: {e}")

        # --- LABELING (Task 4) ---
        pts_3857 = list(poly_3857.exterior.coords)
        pts_orig = list(poly_geom.exterior.coords)

        # 1. Label Stesen
        for i, p in enumerate(pts_3857[:-1]):
            ax.scatter(p[0], p[1], color="yellow", s=40, zorder=20, edgecolor="black")
            if show_stn:
                ax.text(p[0], p[1], f"  STN {i+1}", color="white", fontsize=10, fontweight="bold", 
                        zorder=25, path_effects=None)

        # 2. Label Bearing & Jarak
        if show_labels:
            for i in range(len(pts_orig) - 1):
                p1_o, p2_o = pts_orig[i], pts_orig[i+1]
                p1_m, p2_m = pts_3857[i], pts_3857[i+1]
                
                # Kira guna 4390 (Data sebenar)
                dist = np.hypot(p2_o[0] - p1_o[0], p2_o[1] - p1_o[1])
                bearing = format_to_dms(np.degrees(np.arctan2(p2_o[0] - p1_o[0], p2_o[1] - p1_o[1])) % 360)
                
                # Letak label di tengah garisan (koordinat 3857)
                mx, my = (p1_m[0] + p2_m[0]) / 2, (p1_m[1] + p2_m[1]) / 2
                ax.text(mx, my, f"{dist:.2f}m\n{bearing}", color="#00FF00", fontsize=8, 
                        fontweight="bold", ha="center", zorder=30,
                        bbox=dict(facecolor='black', alpha=0.5, edgecolor='none', pad=1))

        # 3. Label Luas
        if show_area:
            centroid = poly_3857.centroid
            ax.text(centroid.x, centroid.y, f"LUAS\n{area_sqm:.2f} m²", 
                    color="white", fontsize=12, fontweight="bold", ha="center", va="center", zorder=40,
                    bbox=dict(facecolor="red", alpha=0.6, boxstyle="round,pad=0.5"))

        # Kemaskan paparan axis
        bounds = gdf_3857.total_bounds
        ax.set_xlim(bounds[0] - zoom_margin, bounds[2] + zoom_margin)
        ax.set_ylim(bounds[1] - zoom_margin, bounds[3] + zoom_margin)
        ax.set_axis_off()
        
        st.pyplot(fig)

else:
    # Paparan awal jika tiada fail
    st.warning("Menunggu fail CSV dimuat naik...")
    st.image("https://www.esri.com/about/newsroom/wp-content/uploads/2019/04/satellite-imagery.jpg", caption="Contoh Paparan WebGIS")

# ================= FOOTER =================
st.markdown("---")
st.caption("Dibangunkan untuk Sistem Pengurusan Maklumat Tanah Malaysia | EPSG:4390 Kertau RSO Ready")
