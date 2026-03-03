import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, Point
import folium
from streamlit_folium import st_folium
import numpy as np
from PIL import Image
import time

# ================= 1. PANGKALAN DATA ATRIBUT =================
# Daftar Nama mengikut Angka Giliran
STUDENT_DATABASE = {
    1: "Chan Boon Yeah",
    2: "Wong Yuean Yi",
    3: "Ooi Sue Ann"
}

PASSWORD_ADMIN = "admin123"
TILE_GOOGLE = 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}'

st.set_page_config(layout="wide", page_title="Sistem WebGIS Tanah")

if 'auth' not in st.session_state:
    st.session_state['auth'] = False
if 'user_name' not in st.session_state:
    st.session_state['user_name'] = ""

# ================= 2. HALAMAN LOG MASUK (WHOLE TAB) =================
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
        st.subheader("Log Masuk Pentadbir")
        
        pwd_input = st.text_input("Masukkan Kata Laluan", type="password")
        
        if st.button("Akses Sistem", use_container_width=True):
            if pwd_input == PASSWORD_ADMIN:
                st.session_state['auth'] = True
                # Simulasi pengecaman admin (Boleh ditukar mengikut ID unik jika perlu)
                st.session_state['user_name'] = "Administrator"
                st.success(f"Selamat Datang, {st.session_state['user_name']}!")
                time.sleep(1) # Beri masa untuk mesej Welcome muncul
                st.rerun()
            else:
                st.error("Kata laluan salah.")
    st.stop()

# ================= 3. PROGRAM UTAMA (SELEPAS AKSES) =================
# Paparan Welcome selepas Login
st.toast(f"Welcome, {st.session_state['user_name']}! 👋")

if st.sidebar.button("Log Keluar 🔓"):
    st.session_state['auth'] = False
    st.rerun()

st.title("🌍 WebGIS Interaktif: Lot Tanah & Atribut Nama")

uploaded_file = st.file_uploader("Muat naik CSV Koordinat (Lajur: E, N)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    if {"E", "N"}.issubset(df.columns):
        # Tambah Atribut Nama berdasarkan Angka Giliran (Index + 1)
        df['Angka Giliran'] = range(1, len(df) + 1)
        df['Nama Pemilik'] = df['Angka Giliran'].map(STUDENT_DATABASE).fillna("Tiada Data")

        # --- Sidebar Settings ---
        st.sidebar.header("Tetapan Paparan")
        zoom_margin = st.sidebar.slider("Zoom Margin", 0, 1000, 50, 10)
        epsg_input = st.sidebar.text_input("EPSG Asal", value="4390")
        
        # --- Pemprosesan Geospatial ---
        gdf_poly = gpd.GeoDataFrame(index=[0], geometry=[Polygon(list(zip(df["E"], df["N"])))], crs=f"EPSG:{epsg_input}")
        gdf_poly_4326 = gdf_poly.to_crs(epsg=4326)
        gdf_points = gpd.GeoDataFrame(df, geometry=[Point(x, y) for x, y in zip(df['E'], df['N'])], crs=f"EPSG:{epsg_input}").to_crs(epsg=4326)

        # --- Paparan Jadual Atribut ---
        st.subheader("📊 Jadual Atribut Stesen")
        st.dataframe(df[['Angka Giliran', 'Nama Pemilik', 'E', 'N']], use_container_width=True)

        # --- Konfigurasi Peta ---
        bounds = gdf_poly_4326.total_bounds
        m = folium.Map(control_scale=True, max_zoom=20, tiles=None)

        folium.TileLayer(tiles=TILE_GOOGLE, attr='Google', name='Google Satellite', overlay=False).add_to(m)
        folium.TileLayer('openstreetmap', name='OpenStreetMap').add_to(m)

        # Poligon
        folium.GeoJson(gdf_poly_4326, name="Lot Tanah", style_function=lambda x: {'color': 'red', 'fillOpacity': 0.1}).add_to(m)

        # Point Markers dengan Nama Pop-out
        for idx, row in gdf_points.iterrows():
            pop_info = f"""
            <div style="font-family: sans-serif;">
                <b>Angka Giliran:</b> {row['Angka Giliran']}<br>
                <b>Nama:</b> {row['Nama Pemilik']}<br>
                <b>E:</b> {row['E']}<br>
                <b>N:</b> {row['N']}
            </div>
            """
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=6, color='white', fill=True, fill_color='red',
                popup=folium.Popup(pop_info, max_width=300)
            ).add_to(m)
            
            folium.Marker(
                location=[row.geometry.y, row.geometry.x],
                icon=folium.DivIcon(html=f'<div style="color: yellow; font-weight: bold; text-shadow: 2px 2px #000;">STN {row["Angka Giliran"]}</div>')
            ).add_to(m)

        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]], padding=(zoom_margin, zoom_margin))
        folium.LayerControl().add_to(m)
        st_folium(m, width="100%", height=500, returned_objects=[])

    else:
        st.error("Ralat: Pastikan CSV mempunyai lajur 'E' dan 'N'.")
