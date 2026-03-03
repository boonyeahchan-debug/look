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

if 'auth' not in st.session_state: st.session_state['auth'] = False
if 'attempts' not in st.session_state: st.session_state['attempts'] = 0
if 'locked' not in st.session_state: st.session_state['locked'] = False
if 'master_password' not in st.session_state: st.session_state['master_password'] = "admin123"
if 'reset_mode' not in st.session_state: st.session_state['reset_mode'] = False

def format_to_dms(deg):
    d = int(deg); md = abs(deg - d) * 60
    m = int(md); sd = (md - m) * 60
    return f"{d}°{m:02d}'{sd:02.0f}\""

# ================= 2. LOG MASUK & RESET =================
if not st.session_state['auth']:
    _, col_mid, _ = st.columns([1, 1.5, 1])
    with col_mid:
        st.title("🏛️ SISTEM MAKLUMAT TANAH")
        if st.session_state['locked']:
            st.error("❌ Akses Disekat: 3 kali percubaan salah.")
            st.stop()

        if st.session_state['reset_mode']:
            st.subheader("🔑 Reset Kata Laluan")
            reg_no = st.number_input("Nombor Pendaftaran", min_value=1, step=1)
            new_pwd = st.text_input("Kata Laluan Baru", type="password")
            if st.button("Sahkan Reset"):
                if reg_no in USER_DATABASE:
                    st.session_state['master_password'] = new_pwd
                    st.session_state['reset_mode'] = False
                    st.success("Berjaya!"); time.sleep(1); st.rerun()
            if st.button("Batal"): st.session_state['reset_mode'] = False; st.rerun()
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
            if st.button("Lupa Kata Laluan?"): st.session_state['reset_mode'] = True; st.rerun()
    st.stop()

# ================= 3. PROGRAM UTAMA =================
with st.sidebar:
    st.header("Kawalan Peta")
    zoom_margin = st.slider("Auto-Zoom Detail", -100, 100, -20)
    epsg_input = st.text_input("EPSG", "4390")
    if st.button("Log Keluar"): st.session_state['auth'] = False; st.rerun()

st.header(f"Selamat Datang, {st.session_state['current_user']}")
uploaded_file = st.file_uploader("Muat naik CSV (E, N)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    if {"E", "N"}.issubset(df.columns):
        # 1. Proses Geometri
        pts_orig = list(zip(df["E"], df["N"]))
        if pts_orig[0] != pts_orig[-1]: pts_orig.append(pts_orig[0])
        poly_orig = Polygon(pts_orig)
        gdf_poly = gpd.GeoDataFrame(index=[0], geometry=[poly_orig], crs=f"EPSG:{epsg_input}").to_crs(epsg=4326)
        
        # Selesaikan Ralat JSON: Convert ke Python Float
        b = gdf_poly.total_bounds
        map_bounds = [[float(b[1]), float(b[0])], [float(b[3]), float(b[2])]]

        # 2. Bina Peta (PENTING: max_zoom mestilah selari untuk aktifkan butang zum)
        m = folium.Map(
            max_zoom=22, 
            min_zoom=1,
            control_scale=True,
            tiles=None
        )

        folium.TileLayer(
            tiles=TILE_GOOGLE,
            attr='Google Satellite',
            max_zoom=22,
            max_native_zoom=20, # Menggunakan zoom digital melebihi had satelit
            name='Google Satellite',
            overlay=False
        ).add_to(m)

        folium.GeoJson(gdf_poly, style_function=lambda x: {'color':'red','weight':3,'fillOpacity':0.1}).add_to(m)

        # 3. STN Markers + POPUP Koordinat
        for idx, row in df.iterrows():
            p_gdf = gpd.GeoDataFrame(index=[0], geometry=[Point(row['E'], row['N'])], crs=f"EPSG:{epsg_input}").to_crs(epsg=4326)
            lat, lon = float(p_gdf.geometry.iloc[0].y), float(p_gdf.geometry.iloc[0].x)
            
            pop_html = f"""
            <div style='font-family: Arial; width: 150px;'>
                <b>STN {idx+1}</b><hr>
                E: {row['E']:.3f}<br>N: {row['N']:.3f}<br>
                Lat: {lat:.7f}<br>Lon: {lon:.7f}
            </div>"""
            
            folium.CircleMarker(
                [lat, lon], radius=6, color='white', fill_color='red', fill=True, weight=2,
                popup=folium.Popup(pop_html, max_width=250)
            ).add_to(m)
            folium.Marker([lat, lon], icon=folium.DivIcon(html=f'<div style="color:yellow; font-weight:bold; text-shadow:1px 1px black;">STN {idx+1}</div>')).add_to(m)

        # 4. Labels Bearing & Jarak
        pts_4326 = list(gdf_poly.geometry.iloc[0].exterior.coords)
        for i in range(len(pts_orig)-1):
            p1_o, p2_o = pts_orig[i], pts_orig[i+1]
            dist = np.hypot(p2_o[0]-p1_o[0], p2_o[1]-p1_o[1])
            brg = (np.degrees(np.arctan2(p2_o[0]-p1_o[0], p2_o[1]-p1_o[1])) % 360)
            mid = [float(pts_4326[i][1]+pts_4326[i+1][1])/2, float(pts_4326[i][0]+pts_4326[i+1][0])/2]
            
            folium.Marker(mid, icon=folium.DivIcon(html=f'<div style="font-size:8pt; color:lime; background:rgba(0,0,0,0.6); padding:2px; border-radius:4px; text-align:center; width:85px;">{dist:.2f}m<br>{format_to_dms(brg)}</div>')).add_to(m)

        # 5. Paparan Akhir
        st.write(f"**Luas Keseluruhan:** {poly_orig.area:.2f} m²")
        m.fit_bounds(map_bounds, padding=(zoom_margin, zoom_margin))
        st_folium(m, width="100%", height=650, key="land_map")
