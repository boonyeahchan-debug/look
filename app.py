import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon
import matplotlib.pyplot as plt
import numpy as np
import contextily as cx
from PIL import Image

# ================= CONFIGURATION & UTILITIES =================
PASSWORD = "admin123"
GOOGLE_SATELLITE_URL = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"

def format_to_dms(deg):
    """Menukar Decimal Degrees ke format DMS (Darjah, Minit, Saat)."""
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return f"{d}°{m:02d}'{sd:02.0f}\""

def calculate_bearing(p1, p2):
    """Mengira bearing antara dua titik."""
    angle_rad = np.arctan2(p2[0] - p1[0], p2[1] - p1[1])
    return np.degrees(angle_rad) % 360

st.set_page_config(layout="wide", page_title="Sistem Maklumat Tanah")

# ================= SIDEBAR & LOGIN =================
with st.sidebar:
    try:
        img = Image.open("logo.png") 
        st.image(img, use_container_width=True)
    except:
        st.warning("Logo 'logo.png' tidak dijumpai.")
    
    st.markdown("### SISTEM PENGURUSAN MAKLUMAT TANAH")
    st.markdown("---")
    st.subheader("Log Masuk")
    user_password = st.text_input("Masukkan Kata Laluan", type="password")

# ================= MAIN LOGIC =================
if user_password == PASSWORD:
    st.sidebar.success("Log masuk berjaya!")
    st.title("Paparan & Eksport Polygon dari CSV")
    
    uploaded_file = st.file_uploader("Upload fail CSV (Mesti ada kolum E dan N)", type=["csv"])

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        
        if {"E", "N"}.issubset(df.columns):
            # --- Sidebar Settings ---
            st.sidebar.markdown("---")
            st.sidebar.subheader("Tetapan Peta")
            epsg_code = st.sidebar.text_input("Kod EPSG (Contoh: 4390)", value="4390")
            show_satellite = st.sidebar.checkbox("Buka Layer Satelit (Google)")
            
            st.sidebar.markdown("---")
            st.sidebar.subheader("Tetapan Paparan")
            zoom_margin = st.sidebar.slider("Margin Zoom (Meter)", 0, 500, 50, 10)
            show_stn = st.sidebar.checkbox("Papar Label Stesen (STN)")
            show_labels = st.sidebar.checkbox("Papar Bearing & Jarak", value=True)
            show_area = st.sidebar.checkbox("Papar Label Luas", value=True)

            # --- Geospatial Processing ---
            coords = list(zip(df["E"], df["N"]))
            poly_orig = Polygon(coords)
            
            # GDF Asal (untuk kira luas & bearing tepat)
            gdf_orig = gpd.GeoDataFrame(index=[0], geometry=[poly_orig], crs=f"EPSG:{epsg_code}")
            area_val = gdf_orig.geometry.area[0]
            
            # GDF Visual (Wajib 3857 untuk Basemap/Satelit)
            gdf_visual = gdf_orig.to_crs(epsg=3857)
            poly_visual = gdf_visual.geometry.iloc[0]

            # --- Display Metrics ---
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("Luas (Sistem Asal)", f"{area_val:.2f} m²")
            col_m2.metric("Bilangan Stesen", f"{len(df)}")

            # --- Data & Export Section ---
            col_data, col_export = st.columns([2, 1])
            with col_data:
                st.write("Pratinjau Data:")
                st.dataframe(df, height=200)
            
            with col_export:
                st.subheader("📥 Eksport")
                geojson_data = gdf_orig.to_json()
                st.download_button("Download GeoJSON", data=geojson_data, file_name="polygon.geojson", mime="application/json")

            # --- Visualization Section ---
            st.subheader("Visualisasi Peta")
            fig, ax = plt.subplots(figsize=(12, 12))
            
            # Plot Polygon (Guna GDF Visual 3857)
            gdf_visual.plot(ax=ax, edgecolor="red", facecolor="none", linewidth=2.5, zorder=10)

            # Basemap Satelit
            if show_satellite:
                try:
                    # Menggunakan Google Satellite tiles
                    cx.add_basemap(ax, source=GOOGLE_SATELLITE_URL, zoom='auto', zoom_adjust=-1)
                except Exception as e:
                    st.warning("Gagal memuatkan satelit. Pastikan sambungan internet aktif.")

            # --- Labeling Logic ---
            ext_coords_v = list(poly_visual.exterior.coords) # Koordinat untuk posisi teks
            ext_coords_o = list(poly_orig.exterior.coords)   # Koordinat untuk kira nilai asal

            # Label Stesen (STN)
            if show_stn:
                for j, p in enumerate(ext_coords_v[:-1]):
                    ax.text(p[0], p[1], f" STN {j+1}", fontsize=9, color='white', fontweight='bold', 
                            bbox=dict(facecolor='black', alpha=0.5, edgecolor='none'))
                    ax.scatter(p[0], p[1], color='red', s=30, zorder=15)

            # Label Bearing & Jarak
            if show_labels:
                for i in range(len(ext_coords_v) - 1):
                    p1_v, p2_v = ext_coords_v[i], ext_coords_v[i+1]
                    p1_o, p2_o = ext_coords_o[i], ext_coords_o[i+1]
                    
                    # Kira nilai berdasarkan koordinat asal
                    dist = np.sqrt((p2_o[0]-p1_o[0])**2 + (p2_o[1]-p1_o[1])**2)
                    brg = calculate_bearing(p1_o, p2_o)
                    brg_str = format_to_dms(brg)
                    
                    # Posisi tengah garisan (Visual)
                    mid_x, mid_y = (p1_v[0] + p2_v[0]) / 2, (p1_v[1] + p2_v[1]) / 2
                    
                    # Kira sudut putaran teks (Visual)
                    angle = np.degrees(np.arctan2(p2_v[1] - p1_v[1], p2_v[0] - p1_v[0]))
                    if angle > 90: angle -= 180
                    elif angle < -90: angle += 180

                    ax.text(mid_x, mid_y, f"{brg_str}\n{dist:.2f}m", color="yellow", 
                            fontsize=8, fontweight="bold", ha="center", va="center", 
                            rotation=angle,
                            bbox=dict(facecolor="black", alpha=0.7, edgecolor="none", pad=1),
                            zorder=20)

            # Label Luas (Centroid)
            if show_area:
                c_v = poly_visual.centroid
                ax.text(c_v.x, c_v.y, f"LUAS\n{area_val:.2f} m²", 
                        color="white", ha="center", fontweight="bold", fontsize=10,
                        bbox=dict(facecolor="black", alpha=0.6, boxstyle="round,pad=0.3", edgecolor="none"),
                        zorder=25)

            # Final Map Tweaks
            bounds = gdf_visual.total_bounds
            ax.set_xlim(bounds[0] - zoom_margin, bounds[2] + zoom_margin)
            ax.set_ylim(bounds[1] - zoom_margin, bounds[3] + zoom_margin)
            ax.set_axis_off()
            ax.set_aspect('equal')
            
            st.pyplot(fig)
            
        else:
            st.error("Ralat: Fail CSV tidak mengandungi lajur 'E' (Easting) dan 'N' (Northing).")

elif user_password != "":
    st.sidebar.error("Kata laluan salah.")
