import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, Point
import folium
from streamlit_folium import st_folium
import numpy as np
from PIL import Image

# ================= 1. KONFIGURASI & SESSION STATE =================
PASSWORD_ADMIN = "admin123"
# URL untuk Google Satellite
TILE_GOOGLE = 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}'

st.set_page_config(layout="wide", page_title="Sistem WebGIS Tanah")

if 'auth' not in st.session_state:
    st.session_state['auth'] = False

# ================= 2. HALAMAN LOG MASUK (SKRIN PENUH) =================
if not st.session_state['auth']:
    _, col_mid, _ = st.columns([1, 1.5, 1])
    with col_mid:
        st.write("#")
        try:
            img = Image.open("logo.png") 
            st.image(img, width=150)
        except:
            pass
        st.title("🏛️ SISTEM MAKLUMAT TANAH")
        st.markdown("---")
        st.subheader("Log Masuk Pentadbir")
        pwd_input = st.text_input("Masukkan Kata Laluan", type="password")
        if st.button("Akses Sistem", use_container_width=True):
            if pwd_input == PASSWORD_ADMIN:
                st.session_state['auth'] = True
                st.rerun()
            else:
                st.error("Kata laluan salah.")
    st.stop()

# ================= 3. PROGRAM UTAMA (SELEPAS AKSES) =================
if st.sidebar.button("Log Keluar 🔓"):
    st.session_state['auth'] = False
    st.rerun()

st.title("🌍 WebGIS Interaktif: Lot Tanah & Stesen")

uploaded_file = st.file_uploader("Muat naik CSV Koordinat (Lajur: E, N)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    if {"E", "N"}.issubset(df.columns):
        st.sidebar.header("Tetapan Paparan")
        
        zoom_margin = st.sidebar.slider(
            "Zoom Margin (Padding Pixel)", 
            min_value=0, max_value=1000, value=100, step=10
        )
        
        epsg_input = st.sidebar.text_input("Kod EPSG", value="4390")
        show_points = st.sidebar.toggle("Papar Point Stesen", value=True)
        show_poly = st.sidebar.toggle("Papar Sempadan Poligon", value=True)
        
        # Pemprosesan Geospatial
        coords = list(zip(df["E"], df["N"]))
        poly_geom = Polygon(coords)
        gdf_poly = gpd.GeoDataFrame(index=[0], geometry=[poly_geom], crs=f"EPSG:{epsg_input}")
        gdf_poly_4326 = gdf_poly.to_crs(epsg=4326)
        
        gdf_points = gpd.GeoDataFrame(
            df, geometry=[Point(x, y) for x, y in zip(df['E'], df['N'])], 
            crs=f"EPSG:{epsg_input}"
        ).to_crs(epsg=4326)

        # Matlamat Peta
        bounds = gdf_poly_4326.total_bounds
        sw, ne = [bounds[1], bounds[0]], [bounds[3], bounds[2]]

        # --- KONFIGURASI PETA (GOOGLE SATELLITE SEBAGAI MAIN) ---
        m = folium.Map(control_scale=True, max_zoom=20, tiles=None) # tiles=None supaya kita boleh kawal susunan

        # 1. Tambah Google Satellite sebagai Main Layer (Pertama ditambah = Default)
        folium.TileLayer(
            tiles=TILE_GOOGLE, 
            attr='Google Satellite', 
            name='Google Satellite',
            overlay=False, 
            control=True
        ).add_to(m)

        # 2. Tambah OpenStreetMap sebagai Pilihan Kedua
        folium.TileLayer('openstreetmap', name='OpenStreetMap').add_to(m)

        # Lukis Data
        if show_poly:
            folium.GeoJson(
                gdf_poly_4326,
                name="Lot Tanah",
                style_function=lambda x: {'fillColor': 'yellow', 'color': 'red', 'weight': 3, 'fillOpacity': 0.1}
            ).add_to(m)

        if show_points:
            for idx, row in gdf_points.iterrows():
                folium.CircleMarker(
                    location=[row.geometry.y, row.geometry.x],
                    radius=5, color='white', weight=2, fill=True, fill_color='red'
                ).add_to(m)
                folium.Marker(
                    location=[row.geometry.y, row.geometry.x],
                    icon=folium.DivIcon(html=f"""<div style="font-family: sans-serif; color: yellow; font-weight: bold; font-size: 10pt; text-shadow: 2px 2px #000; width: 100px;">STN {idx+1}</div>""")
                ).add_to(m)

        m.fit_bounds([sw, ne], padding=(zoom_margin, zoom_margin))
        folium.LayerControl().add_to(m)
        st_folium(m, width="100%", height=650, returned_objects=[])

        st.markdown("---")
        st.download_button("📥 Muat Turun Data GeoJSON", gdf_poly.to_json(), "lot_tanah.geojson")
    else:
        st.error("Ralat: Fail CSV memerlukan lajur 'E' dan 'N'.")
