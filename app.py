import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, Point
import folium
from streamlit_folium import st_folium
import numpy as np
from PIL import Image
import time

# ================= 1. KONFIGURASI & SESSION STATE =================
TILE_GOOGLE = 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}'
TILE_ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'

st.set_page_config(layout="wide", page_title="Sistem WebGIS Tanah")

# Database Pemilik
USER_DATABASE = {
    1: "Chan Boon Yeah",
    2: "Wong Yuean Yi",
    3: "Ooi Sue Ann"
}

# Inisialisasi Session State
if 'auth' not in st.session_state: st.session_state['auth'] = False
if 'attempts' not in st.session_state: st.session_state['attempts'] = 0
if 'locked' not in st.session_state: st.session_state['locked'] = False
if 'master_password' not in st.session_state: st.session_state['master_password'] = "admin123"
if 'reset_mode' not in st.session_state: st.session_state['reset_mode'] = False

def format_to_dms(deg):
    """Format Decimal ke Darjah Minit Saat (DMS)."""
    d = int(deg); md = abs(deg - d) * 60
    m = int(md); sd = (md - m) * 60
    return f"{d}°{m:02d}'{sd:02.0f}\""

# ================= 2. LOG MASUK & RESET =================
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
                    st.success("Berjaya!"); time.sleep(1); st.rerun()
                else:
                    st.error("Nombor Pendaftaran tidak sah.")
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
                    if st.session_state['attempts'] >= 3: 
                        st.session_state['locked'] = True
                    st.error(f"Salah! Cubaan: {st.session_state['attempts']}/3")
            
            if st.button("Lupa Kata Laluan?"): 
                st.session_state['reset_mode'] = True; st.rerun()
    st.stop()

# ================= 3. MAIN INTERFACE (AFTER LOGIN) =================
st.success(f"Selamat Datang, {st.session_state['current_user']} ✨")

with st.sidebar:
    try:
        img = Image.open("logo.png") 
        st.image(img, use_container_width=True)
    except:
        st.info("Logo 'logo.png' tidak dijumpai.")
    
    st.markdown("### ⚙️ TETAPAN SISTEM")
    epsg_input = st.text_input("Kod EPSG Asal", value="4390")
    
    zoom_margin = st.slider(
        "Zoom Margin (Padding)", 
        min_value=0, max_value=1000, value=50, step=10
    )
    
    show_points = st.checkbox("Papar Point Stesen", value=True)
    show_poly = st.checkbox("Papar Poligon", value=True)
    
    if st.button("Log Keluar"):
        st.session_state['auth'] = False
        st.rerun()

# ================= 4. PEMPROSESAN DATA & PETA =================
uploaded_file = st.file_uploader("Muat naik CSV (Kolum: E, N)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    if {"E", "N"}.issubset(df.columns):
        # Pemprosesan GeoPandas
        coords = list(zip(df["E"], df["N"]))
        poly_geom = Polygon(coords)
        
        gdf_poly = gpd.GeoDataFrame(index=[0], geometry=[poly_geom], crs=f"EPSG:{epsg_input}").to_crs(epsg=4326)
        
        # Metrik
        area_val = gpd.GeoDataFrame(index=[0], geometry=[poly_geom], crs=f"EPSG:{epsg_input}").geometry.area[0]
        m1, m2, m3 = st.columns(3)
        m1.metric("Luas Tanah", f"{area_val:.2f} m²")
        m2.metric("Bilangan Point", len(df))
        m3.metric("Sistem Koordinat", f"EPSG:{epsg_input}")

        # Bina Peta Folium
        m = folium.Map(max_zoom=22, min_zoom=1, control_scale=True, tiles=None)

        folium.TileLayer(
            tiles=TILE_GOOGLE, attr='Google Satellite', name='Google Satellite',
            max_zoom=22, max_native_zoom=20, overlay=False
        ).add_to(m)
        
        folium.TileLayer(
            tiles=TILE_ESRI, attr='Esri World Imagery', name='Esri Satellite',
            max_zoom=22, max_native_zoom=19, overlay=False
        ).add_to(m)

        # Tambah Poligon
        if show_poly:
            folium.GeoJson(
                gdf_poly,
                name="Sempadan Poligon",
                style_function=lambda x: {'color': 'red', 'fillColor': '#ffff00', 'weight': 3, 'fillOpacity': 0.1}
            ).add_to(m)

        # Tambah Point Stesen
        if show_points:
            for idx, row in df.iterrows():
                # Tukar koordinat ke 4326 untuk plotting
                pt_gdf = gpd.GeoDataFrame(index=[0], geometry=[Point(row['E'], row['N'])], crs=f"EPSG:{epsg_input}").to_crs(epsg=4326)
                lat, lon = pt_gdf.geometry.iloc[0].y, pt_gdf.geometry.iloc[0].x
                
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
                
                folium.Marker(
                    [lat, lon], 
                    icon=folium.DivIcon(html=f'<div style="color:yellow; font-weight:bold; text-shadow:1px 1px black; width:100px;">STN {idx+1}</div>')
                ).add_to(m)

        # Auto-Zoom
        bounds = gdf_poly.total_bounds
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]], padding=(zoom_margin, zoom_margin))
        
        folium.LayerControl().add_to(m)
        st_folium(m, width="100%", height=600, returned_objects=[])

        # Eksport
        st.markdown("---")
        c1, c2 = st.columns(2)
        c1.download_button("📥 Eksport GeoJSON", gdf_poly.to_json(), "data_tanah.geojson")
        c2.download_button("📥 Eksport CSV", df.to_csv(index=False).encode('utf-8'), "koordinat.csv")

    else:
        st.error("Fail CSV mesti mempunyai lajur 'E' dan 'N'.")
else:
    st.info("Sila muat naik fail CSV untuk melihat visualisasi peta.")
