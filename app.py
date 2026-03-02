import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon
import matplotlib.pyplot as plt
import numpy as np
import io
import zipfile
import os
import time
import contextily as cx
from PIL import Image

# ================= CONFIG =================
PASSWORD = "admin123"
st.set_page_config(layout="wide")
st.title("Paparan & Ekspot Polygon dari CSV")

# ================= UTILITIES =================
def format_to_dms(deg):
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return f"{d}°{m:02d}'{sd:02.0f}\""

# ================= SIDEBAR =================
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

# ================= LOGIN =================
if user_password == PASSWORD:
    st.sidebar.success("Log masuk berjaya!")

    uploaded_file = st.file_uploader("Upload fail CSV", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.write("Data yang dimuat naik:")
        st.dataframe(df)

        if {"E", "N"}.issubset(df.columns):

            # ---------- MAP SETTINGS ----------
            st.sidebar.markdown("---")
            st.sidebar.subheader("Tetapan Peta")
            epsg_code = st.sidebar.text_input("Kod EPSG Asal", value="4390")
            show_satellite = st.sidebar.checkbox("Buka Layer Satelit (On / Off)", value=True)

            zoom_margin = st.sidebar.slider(
                "Zoom Keluar (Margin dalam Meter)",
                min_value=0, max_value=500, value=50, step=10
            )

            st.sidebar.markdown("---")
            st.sidebar.subheader("Tetapan Label")
            show_stn = st.sidebar.checkbox("Papar Label Stesen (STN)")
            show_labels = st.sidebar.checkbox("Papar Bearing & Jarak")
            show_area = st.sidebar.checkbox("Papar Label Luas")

            # ---------- GEOMETRY PROCESSING ----------
            coords = list(zip(df["E"], df["N"]))
            polygon_orig = Polygon(coords)
            
            # Create GeoDataFrame in Original CRS
            gdf = gpd.GeoDataFrame(geometry=[polygon_orig], crs=f"EPSG:{epsg_code}")
            
            # Simpan luas asal (sebelum reproject) untuk ketepatan
            area_orig = gdf.geometry.area.iloc[0]
            
            # REPROJECT KE WEB MERCATOR UNTUK BASEMAP
            gdf_3857 = gdf.to_crs(epsg=3857)
            poly_3857 = gdf_3857.geometry.iloc[0]
            centroid_3857 = poly_3857.centroid

            # ---------- EXPORT ----------
            st.subheader("Ekspot Data")
            col1, col2 = st.columns(2)
            col1.download_button("Download GeoJSON", gdf.to_json(), "polygon.geojson", "application/json")

            with col2:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    name = "polygon"
                    gdf.to_file(f"{name}.shp")
                    time.sleep(0.5)
                    for ext in ["shp", "shx", "dbf", "prj"]:
                        if os.path.exists(f"{name}.{ext}"):
                            zip_file.write(f"{name}.{ext}")
                st.download_button("Download Shapefile (.zip)", zip_buffer.getvalue(), "polygon_shapefile.zip", "application/zip")

            # ---------- VISUALIZATION ----------
            st.subheader("Visualisasi")
            fig, ax = plt.subplots(figsize=(10, 10))

            # Plot Polygon (Gunakan gdf_3857)
            fill_color = "none" if show_satellite else "lightblue"
            gdf_3857.plot(ax=ax, edgecolor="red", facecolor=fill_color, linewidth=2, alpha=0.7, zorder=10)

            # Masukkan Basemap Satelit
            if show_satellite:
                try:
                    # Pastikan crs dinyatakan supaya contextily tahu kita guna 3857
                    cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, crs=gdf_3857.crs.to_string())
                except Exception as e:
                    st.warning(f"Layer satelit gagal: {e}")

            # ---------- LABELS (Gunakan koordinat 3857) ----------
            pts_3857 = list(poly_3857.exterior.coords)
            pts_orig = list(polygon_orig.exterior.coords) # Untuk kira bearing/jarak sebenar

            for i, p in enumerate(pts_3857[:-1]):
                ax.scatter(p[0], p[1], color="yellow", s=30, zorder=20)
                if show_stn:
                    ax.text(p[0], p[1], f"  STN {i+1}", color="white", fontsize=9, fontweight="bold", zorder=25)

            if show_labels:
                for i in range(len(pts_orig) - 1):
                    # Kira guna data asal (4390) supaya jarak/bearing tepat
                    p1_o, p2_o = pts_orig[i], pts_orig[i + 1]
                    dist = np.hypot(p2_o[0] - p1_o[0], p2_o[1] - p1_o[1])
                    bearing = format_to_dms(np.degrees(np.arctan2(p2_o[0] - p1_o[0], p2_o[1] - p1_o[1])) % 360)
                    
                    # Letak label guna koordinat 3857 (lokasi tengah antara titik)
                    p1_m, p2_m = pts_3857[i], pts_3857[i+1]
                    mx, my = (p1_m[0] + p2_m[0]) / 2, (p1_m[1] + p2_m[1]) / 2
                    ax.text(mx, my, f"{dist:.2f}m\n{bearing}", color="lime", 
                            fontsize=8, fontweight="bold", ha="center", zorder=30,
                            bbox=dict(facecolor='black', alpha=0.4, edgecolor='none'))

            if show_area:
                ax.text(centroid_3857.x, centroid_3857.y, f"LUAS\n{area_orig:.2f} m²",
                    color="white", fontsize=12, fontweight="bold", ha="center", va="center", zorder=40,
                    bbox=dict(facecolor="black", alpha=0.6, boxstyle="round"))

            # ---------- EXTENT & LOOK ----------
            bounds = gdf_3857.total_bounds
            ax.set_xlim(bounds[0] - zoom_margin, bounds[2] + zoom_margin)
            ax.set_ylim(bounds[1] - zoom_margin, bounds[3] + zoom_margin)
            ax.set_axis_off() # Sembunyikan axis untuk rupa lebih bersih
            
            st.pyplot(fig)

        else:
            st.error("Fail CSV mesti mengandungi lajur 'E' dan 'N'.")

elif user_password != "":
    st.sidebar.error("Kata laluan salah. Sila cuba lagi.")
