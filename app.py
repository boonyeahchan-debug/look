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

# Database Pemilik (Gunakan No. Pendaftaran sebagai Key)
USER_DATABASE = {
    1: "Chan Boon Yeah",
    2: "Wong Yuean Yi",
    3: "Ooi Sue Ann"
}

# Inisialisasi Session State
if 'auth' not in st.session_state:
    st.session_state['auth'] = False
if 'attempts' not in st.session_state:
    st.session_state['attempts'] = 0
if 'locked' not in st.session_state:
    st.session_state['locked'] = False
if 'current_user' not in st.session_state:
    st.session_state['current_user'] = ""
if 'master_password' not in st.session_state:
    st.session_state['master_password'] = "admin123"
if 'reset_mode' not in st.session_state:
    st.session_state['reset_mode'] = False

# ================= 2. FUNGSI UTILITI =================
def format_to_dms(deg):
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return f"{d}°{m:02d}'{sd:02.0f}\""

# ================= 3. HALAMAN LOG MASUK & RESET =================
if not st.session_state['auth']:
    _, col_mid, _ = st.columns([1, 1.5, 1])
    with col_mid:
        st.write("#")
        st.title("🏛️ SISTEM MAKLUMAT TANAH")
        
        if st.session_state['locked']:
            st.error("❌ Akses Disekat: Terlalu banyak percubaan salah (Had: 3).")
            st.stop()

        # --- MOD RESET KATA LALUAN (Guna No. Pendaftaran) ---
        if st.session_state['reset_mode']:
            st.subheader("🔑 Tetap Semula Kata Laluan")
            reg_no = st.number_input("Masukkan Nombor Pendaftaran", min_value=1, step=1)
            new_pwd = st.text_input("Kata Laluan Baru", type="password")
            confirm_pwd = st.text_input("Sahkan Kata Laluan Baru", type="password")
            
            col_b1, col_b2 = st.columns(2)
            if col_b1.button("Sahkan Reset", use_container_width=True):
                if reg_no in USER_DATABASE:
                    if new_pwd == confirm_pwd and new_pwd != "":
                        st.session_state['master_password'] = new_pwd
                        st.session_state['reset_mode'] = False
                        st.session_state['attempts'] = 0
                        st.success(f"Kata laluan untuk {USER_DATABASE[reg_no]} dikemaskini!")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("Kata laluan tidak sepadan.")
                else:
                    st.error("Nombor Pendaftaran tidak dijumpai.")
            
            if col_b2.button("Kembali ke Login", use_container_width=True):
                st.session_state['reset_mode'] = False
                st.rerun()
        
        # --- MOD LOG MASUK ---
        else:
            u_no = st.number_input("Nombor Pendaftaran", min_value=1, step=1)
            p_in = st.text_input("Kata Laluan", type="password")
            
            if st.button("Masuk Sistem", use_container_width=True):
                if p_in == st.session_state['master_password']:
                    if u_no in USER_DATABASE:
                        st.session_state['auth'] = True
                        st.session_state['current_user'] = USER_DATABASE[u_no]
                        st.rerun()
                    else:
                        st.error("No. Pendaftaran tidak sah.")
                else:
                    st.session_state['attempts'] += 1
                    if st.session_state['attempts'] >= 3:
                        st.session_state['locked'] = True
                    st.rerun()
            
            st.markdown("---")
            if st.button("Lupa Kata Laluan?"):
                st.session_state['reset_mode'] = True
                st.rerun()
    st.stop()

# ================= 4. PROGRAM UTAMA (WEBGIS) =================
st.success(f"Selamat Datang, {st.session_state['current_user']} ✨")

with st.sidebar:
    st.header("Konfigurasi")
    epsg_input = st.text_input("Sistem Koordinat (EPSG)", "4390")
    # Zoom Padding Negatif memaksa peta zum lebih dekat (Skala 10m)
    zoom_val = st.slider("Auto-Zoom Detail", -100, 100, -20)
    if st.button("Log Keluar 🔓"):
        st.session_state['auth'] = False
        st.rerun()

uploaded_file = st.file_uploader("Muat naik CSV Koordinat (E, N)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    if {"E", "N"}.issubset(df.columns):
        # 1. Pemprosesan Geometri
        pts_orig = list(zip(df["E"], df["N"]))
        poly_orig = Polygon(pts_orig + [pts_orig[0]])
        gdf_poly = gpd.GeoDataFrame(index=[0], geometry=[poly_orig], crs=f"EPSG:{epsg_input}").to_crs(epsg=4326)
        
        # 2. Bina Peta (Google Satellite Sahaja)
        m = folium.Map(max_zoom=20, control_scale=True, tiles=None)
        folium.TileLayer(tiles=TILE_GOOGLE, attr='Google Satellite', max_zoom=20, name='Google Satellite').add_to(m)
        
        # 3. Lukis Poligon
        folium.GeoJson(gdf_poly, style_function=lambda x: {'color':'red','fillOpacity':0.1, 'weight':3}).add_to(m)

        # 4. STN Points dengan POPUP Koordinat & Lat/Lon
        for idx, row in df.iterrows():
            p_gdf = gpd.GeoDataFrame(index=[0], geometry=[Point(row['E'], row['N'])], crs=f"EPSG:{epsg_input}").to_crs(epsg=4326)
            lat, lon = p_gdf.geometry.iloc[0].y, p_gdf.geometry.iloc[0].x
            
            # Kandungan Popup
            popup_html = f"""
            <div style="font-family: Arial; font-size: 10pt; width: 160px;">
                <b>STN {idx+1}</b><hr>
                <b>E:</b> {row['E']:.2f}<br><b>N:</b> {row['N']:.2f}<br>
                <b>Lat:</b> {lat:.7f}<br><b>Lon:</b> {lon:.7f}
            </div>"""
            
            folium.CircleMarker(
                location=[lat, lon], radius=6, color='white', fill=True, fill_color='red', weight=2,
                popup=folium.Popup(popup_html, max_width=200)
            ).add_to(m)
            
            folium.Marker(location=[lat, lon], icon=folium.DivIcon(html=f'<div style="color: yellow; font-weight: bold; text-shadow: 1px 1px black;">STN {idx+1}</div>')).add_to(m)

        # 5. Label Bearing & Jarak (Line Center)
        pts_4326 = list(gdf_poly.geometry.iloc[0].exterior.coords)
        for i in range(len(pts_orig)):
            p1_o, p2_o = pts_orig[i], pts_orig[(i+1)%len(pts_orig)]
            dist = np.hypot(p2_o[0]-p1_o[0], p2_o[1]-p1_o[1])
            brg = (np.degrees(np.arctan2(p2_o[0]-p1_o[0], p2_o[1]-p1_o[1])) % 360)
            mid = [(pts_4326[i][1]+pts_4326[i+1][1])/2, (pts_4326[i][0]+pts_4326[i+1][0])/2]
            
            folium.Marker(
                location=mid, 
                icon=folium.DivIcon(html=f'<div style="font-size: 8pt; color: lime; background: rgba(0,0,0,0.6); padding: 2px; border-radius: 4px; text-align: center; width: 85px;">{dist:.2f}m<br>{format_to_dms(brg)}</div>')
            ).add_to(m)

        # 6. Metrik & Auto-Zoom
        st.write(f"### Luas Tanah: **{poly_orig.area:.2f} m²** | Bilangan Point: **{len(df)}**")
        m.fit_bounds(gdf_poly.total_bounds.reshape(2,2), padding=(zoom_val, zoom_val))
        st_folium(m, width="100%", height=650)
