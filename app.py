import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, Point
import folium
from streamlit_folium import st_folium
import numpy as np
from PIL import Image
import math
import time

# ================= 1. KONFIGURASI & SESSION STATE =================
TILE_GOOGLE = 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}'

st.set_page_config(layout="wide", page_title="Sistem WebGIS Tanah")

# Database Pemilik
USER_DATABASE = {
    1: "Chan Boon Yeah",
    2: "Wong Yuean Yi",
    3: "Ooi Sue Ann"
}

# Inisialisasi Memori Sesi
if 'auth' not in st.session_state: st.session_state['auth'] = False
if 'attempts' not in st.session_state: st.session_state['attempts'] = 0
if 'locked' not in st.session_state: st.session_state['locked'] = False
if 'master_password' not in st.session_state: st.session_state['master_password'] = "admin123"
if 'reset_mode' not in st.session_state: st.session_state['reset_mode'] = False

def format_to_dms(deg):
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return f"{d}°{m:02d}'{sd:02.0f}\""

# ================= 2. HALAMAN LOG MASUK & RESET =================
if not st.session_state['auth']:
    _, col_mid, _ = st.columns([1, 1.5, 1])
    with col_mid:
        st.title("🏛️ SISTEM MAKLUMAT TANAH")
        
        if st.session_state['locked']:
            st.error("❌ Akses Disekat: Terlalu banyak percubaan salah.")
            st.stop()

        if st.session_state['reset_mode']:
            st.subheader("🔑 Reset Kata Laluan")
            reg_no = st.number_input("Nombor Pendaftaran", min_value=1, step=1)
            new_pwd = st.text_input("Kata Laluan Baru", type="password")
            if st.button("Sahkan Reset"):
                if reg_no in USER_DATABASE:
                    st.session_state['master_password'] = new_pwd
                    st.session_state['reset_mode'] = False
                    st.session_state['attempts'] = 0
                    st.success("Berjaya! Sila log masuk.")
                    time.sleep(1)
                    st.rerun()
            if st.button("Batal"): 
                st.session_state['reset_mode'] = False
                st.rerun()
        else:
            u_no = st.number_input("Nombor Pendaftaran", min_value=1, step=1)
            p_in = st.text_input("Kata Laluan", type="password")
            if st.button("Masuk", use_container_width=True):
                if p_in == st.session_state['master_password'] and u_no in USER_DATABASE:
                    st.session_state['auth'] = True
                    st.session_state['current_user'] = USER_DATABASE[u_no]
                    st.rerun()
                else:
                    st.session_state['attempts'] += 1
                    if st.session_state['attempts'] >= 3: st.session_state['locked'] = True
                    st.rerun()
            if st.button("Lupa Kata Laluan?"): 
                st.session_state['reset_mode'] = True
                st.rerun()
    st.stop()

# ================= 3. PROGRAM UTAMA (WEBGIS) =================
st.sidebar.header("Konfigurasi Peta")
epsg_input = st.sidebar.text_input("EPSG Asal", "4390")
zoom_pad = st.sidebar.slider("Zoom Detail", -50, 100, -20)
if st.sidebar.button("Log Keluar"): 
    st.session_state['auth'] = False
    st.rerun()

st.header(f"📍 Analisis Lot: {st.session_state['current_user']}")
uploaded_file = st.file_uploader("Muat naik CSV Koordinat (E, N)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    if {"E", "N"}.issubset(df.columns):
        # Pemprosesan Geometri
        pts_orig = list(zip(df["E"], df["N"]))
        poly_orig = Polygon(pts_orig + [pts_orig[0]])
        gdf_poly = gpd.GeoDataFrame(index=[0], geometry=[poly_orig], crs=f"EPSG:{epsg_input}").to_crs(epsg=4326)
        
        # Selesaikan Ralat JSON: Tukar bounds ke format Python Float List
        b = gdf_poly.total_bounds
        map_bounds = [[float(b[1]), float(b[0])], [float(b[3]), float(b[2])]]

        # Bina Peta
        m = folium.Map(max_zoom=20, control_scale=True, tiles=None)
        folium.TileLayer(tiles=TILE_GOOGLE, attr='Google Satellite', max_zoom=20).add_to(m)
        folium.GeoJson(gdf_poly, style_function=lambda x: {'color':'red','fillOpacity':0.1, 'weight':3}).add_to(m)

        # STN Points & Popup
        for idx, row in df.iterrows():
            p_gdf = gpd.GeoDataFrame(index=[0], geometry=[Point(row['E'], row['N'])], crs=f"EPSG:{epsg_input}").to_crs(epsg=4326)
            lat, lon = float(p_gdf.geometry.iloc[0].y), float(p_gdf.geometry.iloc[0].x)
            
            pop_html = f"<b>STN {idx+1}</b><br>E: {row['E']}<br>N: {row['N']}<br>Lat: {lat:.6f}<br>Lon: {lon:.6f}"
            folium.CircleMarker([lat, lon], radius=6, color='white', fill=True, fill_color='red', weight=2,
                               popup=folium.Popup(pop_html, max_width=200)).add_to(m)
            folium.Marker([lat, lon], icon=folium.DivIcon(html=f'<div style="color:yellow; font-weight:bold; text-shadow:1px 1px black;">STN {idx+1}</div>')).add_to(m)

        # Label Bearing & Jarak
        pts_4326 = list(gdf_poly.geometry.iloc[0].exterior.coords)
        for i in range(len(pts_orig)):
            p1, p2 = pts_orig[i], pts_orig[(i+1)%len(pts_orig)]
            dist = np.hypot(p2[0]-p1[0], p2[1]-p1[1])
            brg = (np.degrees(np.arctan2(p2[0]-p1[0], p2[1]-p1[1])) % 360)
            mid = [float(pts_4326[i][1]+pts_4326[i+1][1])/2, float(pts_4326[i][0]+pts_4326[i+1][0])/2]
            
            folium.Marker(mid, icon=folium.DivIcon(html=f'<div style="font-size:8pt; color:lime; background:rgba(0,0,0,0.6); padding:2px; border-radius:4px; text-align:center; width:85px;">{dist:.2f}m<br>{format_to_dms(brg)}</div>')).add_to(m)

        # Paparan Akhir
        st.info(f"Keluasan Lot: {poly_orig.area:.2f} meter persegi")
        m.fit_bounds(map_bounds, padding=(zoom_pad, zoom_pad))
        st_folium(m, width="100%", height=650)
