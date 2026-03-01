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

# ================== CONFIG ==================
PASSWORD = "admin123"

st.set_page_config(layout="wide")
st.title("Paparan & Ekspot Polygon dari CSV")

# ================== UTILITIES ==================
def format_to_dms(deg):
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return f"{d}°{m:02d}'{sd:02.0f}\""

@st.cache_data(show_spinner=False)
def reproject_to_3857(gdf):
    return gdf.to_crs(epsg=3857)

# ================== SIDEBAR ==================
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

# ================== LOGIN ==================
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
            epsg_code = st.sidebar.text_input("Kod EPSG", value="4390")
            show_satellite = st.sidebar.checkbox("Buka Layer Satelit (On/Off)")

            if show_satellite:
                st.sidebar.info("Layer satelit menggunakan Web Mercator (EPSG:3857).")

            st.sidebar.markdown("---")
            zoom_margin = st.sidebar.slider(
                "Zoom Keluar (Margin dalam Meter)",
                min_value=0, max_value=500, value=10, step=5
            )

            st.sidebar.markdown("---")
            st.sidebar.subheader("Tetapan Label")
            show_stn = st.sidebar.checkbox("Papar Label Stesen (STN)")
            show_labels = st.sidebar.checkbox("Papar Bearing & Jarak")
            show_area = st.sidebar.checkbox("Papar Label Luas")

            # ---------- GEOMETRY ----------
            coords = list(zip(df["E"], df["N"]))
            polygon = Polygon(coords)

            gdf = gpd.GeoDataFrame(
                index=[0],
                geometry=[polygon],
                crs=f"EPSG:{epsg_code}"
            )

            area = gdf.geometry.area[0]
            centroid = gdf.geometry.centroid[0]

            # ---------- EXPORT ----------
            st.subheader("Ekspot Data")
            col1, col2 = st.columns(2)

            geojson_data = gdf.to_json()
            col1.download_button(
                "Download GeoJSON",
                geojson_data,
                "polygon.geojson",
                "application/json"
            )

            with col2:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
                    name = "temp_polygon"
                    gdf.to_file(f"{name}.shp")
                    time.sleep(1)
                    for ext in ["shp", "shx", "dbf", "prj"]:
                        f = f"{name}.{ext}"
                        if os.path.exists(f):
                            zip_file.write(f)

                st.download_button(
                    "Download Shapefile (.zip)",
                    zip_buffer.getvalue(),
                    "polygon_shapefile.zip",
                    "application/zip"
                )

            # ---------- VISUALIZATION ----------
            st.subheader("Visualisasi")
            fig, ax = plt.subplots(figsize=(10, 10))

            gdf_3857 = reproject_to_3857(gdf)

            fill_color = "none" if show_satellite else "lightblue"

            gdf_3857.plot(
                ax=ax,
                edgecolor="red",
                facecolor=fill_color,
                alpha=0.6,
                linewidth=2,
                zorder=10
            )

            if show_satellite:
                try:
                    cx.add_basemap(
                        ax,
                        source=cx.providers.Esri.WorldImagery,
                        zoom="auto",
                        attribution=False
                    )
                except:
                    st.warning("Layer satelit gagal dimuatkan.")

            # ---------- LABELS ----------
            points = list(polygon.exterior.coords)

            for i, p in enumerate(points[:-1]):
                ax.scatter(p[0], p[1], color="black", s=20, zorder=20)
                if show_stn:
                    ax.text(
                        p[0], p[1],
                        f" STN {i+1}",
                        fontsize=9,
                        fontweight="bold",
                        zorder=25
                    )

            if show_labels:
                for i in range(len(points) - 1):
                    p1, p2 = points[i], points[i + 1]
                    dist = np.hypot(p2[0] - p1[0], p2[1] - p1[1])
                    angle = np.degrees(np.arctan2(p2[0] - p1[0], p2[1] - p1[1])) % 360
                    bearing = format_to_dms(angle)

                    mid_x = (p1[0] + p2[0]) / 2
                    mid_y = (p1[1] + p2[1]) / 2

                    ax.text(
                        mid_x, mid_y,
                        f"{dist:.2f} m\n{bearing}",
                        fontsize=10,
                        color="yellow",
                        fontweight="bold",
                        ha="center",
                        va="center",
                        zorder=30
                    )

            if show_area:
                ax.text(
                    centroid.x,
                    centroid.y,
                    f"LUAS\n{area:.2f} m²",
                    fontsize=12,
                    color="white",
                    fontweight="bold",
                    ha="center",
                    va="center",
                    bbox=dict(facecolor="black", alpha=0.5, boxstyle="round,pad=0.5"),
                    zorder=35
                )

            # ---------- EXTENT ----------
            bounds = gdf_3857.total_bounds
            ax.set_xlim(bounds[0] - zoom_margin, bounds[2] + zoom_margin)
            ax.set_ylim(bounds[1] - zoom_margin, bounds[3] + zoom_margin)

            ax.set_aspect("equal")
            ax.set_title(f"Polygon Visualisasi (EPSG:{epsg_code})")
            ax.set_xlabel("X (meters)")
            ax.set_ylabel("Y (meters)")

            st.pyplot(fig)

        else:
            st.error("Fail CSV mesti mengandungi lajur 'E' dan 'N'.")

elif user_password != "":
    st.sidebar.error("Kata laluan salah. Sila cuba lagi.")
