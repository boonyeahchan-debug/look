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
PASSWORD_SYSTEM = "admin123"
# URL Tile Google Satellite (Satu-satunya Layer Utama)
TILE_GOOGLE = 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}'

st.set_page_config(layout="wide", page_title="Sistem WebGIS Tanah")

# Database Pemilik (Angka Giliran)
USER_DATABASE = {
    1: "Chan Boon Yeah",
    2: "Wong Yuean Yi",
    3: "Ooi Sue Ann"
}

if 'auth' not in st.session_state:
    st.session_state['auth'] = False
if 'attempts' not in st.session_state:
    st.session_state['attempts'] = 0
if 'locked' not in st.session_state:
    st.session_state['locked'] = False
if 'current_user' not in st.session_state:
    st.session_state['current_user'] = ""

# ================= 2. FUNGSI UTILITI =================
def format_to_dms(deg):
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return f"{d}°{m:02d}'{sd:02.0f}\""

# ================= 3. HALAMAN LOG MASUK =================
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
        
        if st.session_state['locked']:
            st.error("❌ Akses Disekat: Terlalu banyak percubaan salah (Had: 3).")
            st.stop()

        st.subheader("Sila Log Masuk")
        user_no = st.number_input("Angka Giliran (Nombor)", min_value=1, step=1)
        pwd_input = st.text_input("Kata Laluan", type="password")
        
        if st.button("Masuk Sistem", use_container_width=True):
            if pwd_input == PASSWORD_SYSTEM:
                name_found = USER_DATABASE.get(user_no)
                if name_found:
                    st.session_state['auth'] = True
                    st.session_state['current_user'] = name_found
                    st.success("Log Masuk Berjaya!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Angka Giliran tidak dijumpai.")
            else:
                st.session_state['attempts'] += 1
                if st.session_state['attempts'] >= 3:
                    st.session_state['locked'] = True
                    st.rerun()
                else:
                    st.warning(f"Katalaluan Salah. Baki percubaan: {3 - st.session_state['attempts']}")
    st.stop()

# ================= 4. PROGRAM UTAMA (WEBGIS) =================
st.success(f"Welcome, {st.session_state['current_user']} ✨")

with st.sidebar:
    if st.button("Log Keluar 🔓"):
        st.session_state['auth'] = False
        st.session_state['attempts'] = 0
        st.rerun()
    st.markdown("---")
    st.header("Kawalan Peta")
    # Zoom Margin 0 membolehkan zum masuk paling dekat
    zoom_margin = st.sidebar.slider("Zoom Margin (Padding)", 0, 1000, 50, 10)
    epsg_input = st.sidebar.text_input("Kod EPSG Asal", value="4390")
    show_labels = st.sidebar.toggle("Papar Bearing & Jarak", value=True)
    show_area = st.sidebar.toggle("Papar Luas Tanah", value=True)

uploaded_file = st.file_uploader("Muat naik CSV Koordinat (E, N)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    if {"E", "N"}.issubset(df.columns):
        # 1. Pemprosesan Geometri (Data Asal - meter)
        pts_orig = list(zip(df["E"], df["N"]))
        if pts_orig[0] != pts_orig[-1]: 
            pts_orig.append(pts_orig[0]) 
            
        poly_orig = Polygon(pts_orig)
        area_orig = poly_orig.area

        # 2. Penukaran ke WGS84
        gdf_poly = gpd.GeoDataFrame(index=[0], geometry=[poly_orig], crs=f"EPSG:{epsg_input}")
        gdf_poly_4326 = gdf_poly.to_crs(epsg=4326)
        pts_4326 = list(gdf_poly_4326.geometry.iloc[0].exterior.coords)

        # 3. Bina Peta (GOOGLE SATELLITE SAHAJA)
        bounds = gdf_poly_4326.total_bounds
        # max_zoom=20 membolehkan zum masuk sehingga skala ~10m
        m = folium.Map(control_scale=True, max_zoom=20, tiles=None)
        
        folium.TileLayer(
            tiles=TILE_GOOGLE, 
            attr='Google Satellite', 
            name='Google Satellite', 
            overlay=False,
            control=False # Tutup kawalan layer kerana hanya ada satu layer
        ).add_to(m)

        # 4. Lukis Poligon
        folium.GeoJson(gdf_poly_4326, style_function=lambda x: {'color':'red','fillOpacity':0.1, 'weight':3}).add_to(m)

        # 5. Label Bearing & Jarak di Tengah Garisan
        if show_labels:
            for i in range(len(pts_orig) - 1):
                p1_o, p2_o = pts_orig[i], pts_orig[i+1]
                dist = np.hypot(p2_o[0] - p1_o[0], p2_o[1] - p1_o[1])
                bearing = (np.degrees(np.arctan2(p2_o[0] - p1_o[0], p2_o[1] - p1_o[1])) % 360)
                
                p1_w, p2_w = pts_4326[i], pts_4326[i+1]
                mid_lat, mid_lon = (p1_w[1] + p2_w[1]) / 2, (p1_w[0] + p2_w[0]) / 2

                label_html = f"""
                <div style="font-size: 8pt; color: lime; font-weight: bold; 
                background: rgba(0,0,0,0.6); padding: 3px; border-radius: 4px; 
                text-align: center; width: 85px; line-height: 1.1;">
                {dist:.2f}m<br>{format_to_dms(bearing)}
                </div>"""
                folium.Marker(location=[mid_lat, mid_lon], icon=folium.DivIcon(html=label_html)).add_to(m)

        # 6. Papar Luas
        if show_area:
            centroid = gdf_poly_4326.geometry.centroid.iloc[0]
            folium.Marker(
                location=[centroid.y, centroid.x],
                icon=folium.DivIcon(html=f"""<div style="font-size: 10pt; color: white; font-weight: bold; 
                background: rgba(0,0,0,0.75); padding: 6px; border-radius: 8px; text-align: center; width: 120px;">
                LUAS<br>{area_orig:.2f} m²</div>""")
            ).add_to(m)

        # 7. STN Markers
        for idx in range(len(df)):
            lat_w, lon_w = pts_4326[idx][1], pts_4326[idx][0]
            folium.CircleMarker(location=[lat_w, lon_w], radius=5, color='white', fill=True, fill_color='red', weight=2).add_to(m)
            folium.Marker(
                location=[lat_w, lon_w],
                icon=folium.DivIcon(html=f'<div style="color: yellow; font-weight: bold; font-size: 10pt; text-shadow: 1px 1px black; width: 60px;">STN {idx+1}</div>')
            ).add_to(m)

        # Zum automatik ke poligon
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]], padding=(zoom_margin, zoom_margin))
        st_folium(m, width="100%", height=650)

        st.download_button("📥 Eksport GeoJSON", gdf_poly.to_json(), "data_lot.geojson")
