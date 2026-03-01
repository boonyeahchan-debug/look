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

# ... (kod tetapan PASSWORD dan fungsi format_to_dms tidak berubah)

st.set_page_config(layout="wide")
st.title("Paparan & Ekspot Polygon dari CSV")

# ... (kod sidebar, paparan logo, dan sistem log masuk tidak berubah)

if user_password == PASSWORD:
    st.sidebar.success("Log masuk berjaya!")
    
    uploaded_file = st.file_uploader("Upload fail CSV", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.write("Data yang dimuat naik:")
        st.dataframe(df)

        if {"E", "N"}.issubset(df.columns):
            # ... (kod tetapan sidebar peta dan label tidak berubah)
            
            # --- PEMPROSESAN DATA GEOSPATIAL ---
            coords = list(zip(df["E"], df["N"]))
            polygon = Polygon(coords)
            
            # 1. Bina GeoDataFrame asal dengan EPSG:4390
            gdf = gpd.GeoDataFrame(index=[0], geometry=[polygon], crs=f"EPSG:{epsg_code}")
            
            area = gdf.geometry.area[0]
            centroid = gdf.geometry.centroid[0]

            # ... (kod ekspot data tidak berubah)

            # --- SEKSYEN PLOT ---
            st.subheader("Visualisasi")
            fig, ax = plt.subplots(figsize=(10, 10))
            
            # --- TETAPAN WARNA ---
            fill_color = "none" if show_satellite else "lightblue"
            
            # Plot Polygon (asal)
            gdf.plot(ax=ax, edgecolor="red", facecolor=fill_color, 
                     alpha=0.6, linewidth=2, zorder=5)
            
            # --- LOGIK LAYER SATELIT (PERBAIKAN DI SINI) ---
            if show_satellite:
                try:
                    # 2. TUKAR DATA KE WEB MERCATOR (EPSG:3857) UNTUK CONTEXTILY
                    gdf_mercator = gdf.to_crs(epsg=3857)
                    
                    # 3. Plot polygon yang sudah ditukar unjuran (halimunan) untuk set extent
                    gdf_mercator.plot(ax=ax, alpha=0)
                    
                    # Tambah basemap satelit
                    cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery)
                    
                except Exception as e:
                    st.error(f"Gagal memuatkan layer satelit: {e}")

            # ... (kod logik label, slider zoom, dan st.pyplot tidak berubah)
