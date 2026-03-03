import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, Point
import folium
from streamlit_folium import st_folium
import numpy as np
from PIL import Image
import math

# ================= 1. CONFIGURATION & SESSION STATE =================
PASSWORD_CORRECT = "admin123"
TILE_GOOGLE = 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}'
TILE_ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'

st.set_page_config(layout="wide", page_title="Sistem WebGIS Tanah")

# Inisialisasi pembolehubah sesi
if 'attempts' not in st.session_state:
    st.session_state['attempts'] = 0
if 'locked' not in st.session_state:
    st.session_state['locked'] = False
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# ================= 2. UTILITIES =================
def format_to_dms(deg):
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return f"{d}°{m:02d}'{sd:02.0f}\""

def calculate_bearing_distance(p1, p2):
    de = p2[0] - p1[0]
    dn = p2[1] - p1[1]
    dist = math.sqrt(de**2 + dn**2)
    brg_rad = math.atan2(de, dn)
    brg_deg = math.degrees(brg_rad)
    if brg_deg < 0: brg_deg += 360
    return brg_deg, dist

# ================= 3. AUTHENTICATION LOGIC =================
with st.sidebar:
    try:
        img = Image.open("logo.png") 
        st.image(img, use_container_width=True)
    except:
        st.info("Logo 'logo.png' tidak dijumpai.")

    st.markdown("### 🏛️ SISTEM MAKLUMAT TANAH")
    st.markdown("---")

    if st.session_state['locked']:
        st.error("❌ Akses Disekat: Terlalu banyak percubaan salah (Limit: 3).")
        st.stop()

    if not st.session_state['authenticated']:
        user_password = st.text_input("Masukkan Kata Laluan", type="password")
        if st.button("Log Masuk"):
            if user_password == PASSWORD_CORRECT:
                st.session_state['authenticated'] = True
                st.session_state['attempts'] = 0
                st.rerun()
            else:
                st.session_state['attempts'] += 1
                remaining = 3 - st.session_state['attempts']
                if st.session_state['attempts'] >= 3:
                    st.session_state['locked'] = True
                    st.rerun()
                else:
                    st.warning(f"Kata laluan salah. Baki percubaan: {remaining}")
        st.stop()
    else:
        st.sidebar.success("✅ Akses Diterima")
        if st.sidebar.button("Log Keluar"):
            st.session_state['authenticated'] = False
            st.rerun()

# ================= 4. MAIN PROGRAM (Hanya jalan jika authenticated) =================
st.title("🗺️ WebGIS: Poligon, Bearing & Jarak")

uploaded_file = st.file_uploader("Muat naik CSV (Kolum: E, N)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    if {"E", "N"}.issubset(df.columns):
        st.sidebar.markdown("---")
        epsg_input = st.sidebar.text_input("Kod EPSG Asal", value="4390")
        zoom_margin = st.sidebar.slider("Zoom Margin", 0, 1000, 50, 10)
        
        show_points = st.sidebar.toggle("Papar Point Stesen", value=True)
        show_poly = st.sidebar.toggle("Papar Sempadan", value=True)
        show_labels = st.sidebar.toggle("Papar Bearing & Jarak", value=True)
        
        # Pemprosesan Geospatial
        coords = list(zip(df["E"], df["N"]))
        coords_closed = coords + [coords[0]] if coords[0] != coords[-1] else coords
        
        poly_geom = Polygon(coords_closed)
        gdf_poly = gpd.GeoDataFrame(index=[0], geometry=[poly_geom], crs=f"EPSG:{epsg_input}")
        gdf_poly_4326 = gdf_poly.to_crs(epsg=4326)
        
        gdf_points = gpd.GeoDataFrame(
            df, geometry=[Point(x, y) for x, y in zip(df['E'], df['N'])], 
            crs=f"EPSG:{epsg_input}"
        ).to_crs(epsg=4326)

        # Metrik
        area_val = gdf_poly.geometry.area[0]
        c1, c2 = st.columns(2)
        c1.metric("Luas Tanah", f"{area_val:.2f} m²")
        c2.metric("Bilangan Point", len(df))

        # Peta
        bounds = gdf_poly_4326.total_bounds
        m = folium.Map(control_scale=True, max_zoom=20)
        
        folium.TileLayer(tiles=TILE_GOOGLE, attr='Google', name='Google Satellite').add_to(m)
        folium.TileLayer(tiles=TILE_ESRI, attr='Esri', name='Esri Satellite').add_to(m)

        if show_poly:
            folium.GeoJson(gdf_poly_4326, style_function=lambda x: {'color': 'red', 'weight': 3, 'fillOpacity': 0.1}).add_to(m)

        if show_labels:
            for i in range(len(coords_closed) - 1):
                p1, p2 = coords_closed[i], coords_closed[i+1]
                brg, dist = calculate_bearing_distance(p1, p2)
                
                # Cari titik tengah dalam WGS84
                p1_wgs = gdf_points.geometry.iloc[i] if i < len(df) else gdf_points.geometry.iloc[0]
                p2_wgs = gdf_points.geometry.iloc[i+1] if i+1 < len(df) else gdf_points.geometry.iloc[0]
                
                mid_lat, mid_lon = (p1_wgs.y + p2_wgs.y)/2, (p1_wgs.x + p2_wgs.x)/2
                
                label = f"B: {format_to_dms(brg)}<br>J: {dist:.2f}m"
                folium.Marker(
                    location=[mid_lat, mid_lon],
                    icon=folium.DivIcon(html=f'<div style="font-size: 8pt; color: yellow; text-shadow: 1px 1px black; white-space: nowrap;">{label}</div>')
                ).add_to(m)

        if show_points:
            for idx, row in gdf_points.iterrows():
                folium.CircleMarker(location=[row.geometry.y, row.geometry.x], radius=4, color='white', fill=True, fill_color='red').add_to(m)
                folium.Marker(location=[row.geometry.y, row.geometry.x],
                             icon=folium.DivIcon(html=f'<div style="color: cyan; font-weight: bold;">STN {idx+1}</div>')).add_to(m)

        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]], padding=(zoom_margin, zoom_margin))
        folium.LayerControl().add_to(m)
        st_folium(m, width="100%", height=600)

        st.download_button("📥 Eksport GeoJSON", gdf_poly.to_json(), "data.geojson")

