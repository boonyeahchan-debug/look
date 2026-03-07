import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, Point
import folium
from streamlit_folium import st_folium
import numpy as np
import time
import json # Tambahan untuk pemprosesan GeoJSON

# ================= 1. KONFIGURASI & SESSION STATE =================
st.set_page_config(layout="wide", page_title="Sistem WebGIS Tanah V2 - Final Edition")

TILE_GOOGLE = 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}'

# Database Pemilik Sah (ID sebagai Key)
USER_DATABASE = {
    "USER01": "Chan Boon Yeah",
    "USER02": "Wong Yuean Yi",
    "USER03": "Ooi Sue Ann"
}

if 'auth' not in st.session_state: st.session_state['auth'] = False
if 'passwords' not in st.session_state: 
    # Simpan kata laluan dalam dict supaya setiap ID boleh ada password sendiri
    st.session_state['passwords'] = {k: "admin123" for k in USER_DATABASE.keys()}
if 'reset_mode' not in st.session_state: st.session_state['reset_mode'] = False

# ================= 2. FUNGSI TEKNIKAL & GEOMETRI =================
def format_to_dms(deg):
    """Tukar Decimal Degree ke format Darjah Minit Saat."""
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return f"{d}°{m:02d}'{sd:02.0f}\""

# ================= 3. SISTEM KESELAMATAN (LOGIN) =================
if not st.session_state['auth']:
    _, col_mid, _ = st.columns([1, 1.5, 1])
    with col_mid:
        st.title("🏛️ SISTEM MAKLUMAT TANAH")
        
        if st.session_state['reset_mode']:
            st.subheader("🔑 Reset Kata Laluan")
            # Input ID Sendiri untuk Reset
            reset_id = st.text_input("Masukkan ID Anda untuk Pengesahan")
            new_pwd = st.text_input("Kata Laluan Baru", type="password")
            
            if st.button("Sahkan Reset"):
                if reset_id in USER_DATABASE:
                    # Tukar password spesifik untuk ID tersebut
                    st.session_state['passwords'][reset_id] = new_pwd
                    st.success(f"Kata laluan untuk {reset_id} berjaya ditukar!")
                    time.sleep(1)
                    st.session_state['reset_mode'] = False
                    st.rerun()
                else:
                    st.error("ID tidak dijumpai dalam sistem!")
            
            if st.button("Batal"): 
                st.session_state['reset_mode'] = False
                st.rerun()
        
        else:
            # Input ID Sendiri untuk Login
            u_id = st.text_input("Masukkan ID Pengguna (Contoh: USER01)")
            p_in = st.text_input("Kata Laluan", type="password")
            
            if st.button("Masuk", use_container_width=True):
                # Semak ID dan Password yang sepadan
                if u_id in USER_DATABASE and p_in == st.session_state['passwords'].get(u_id):
                    st.session_state['auth'] = True
                    st.session_state['current_user'] = USER_DATABASE[u_id]
                    st.rerun()
                else:
                    st.error("ID atau Kata Laluan Salah!")
            
            if st.button("Lupa Kata Laluan?"): 
                st.session_state['reset_mode'] = True
                st.rerun()
    st.stop()

# ================= 4. INTERFACE KAWALAN SIDEBAR =================
with st.sidebar:
    st.success(f"Log Masuk: {st.session_state['current_user']} ✨")
    st.header("🎮 Kawalan Lapisan")
    
    show_sat = st.checkbox("Peta Satelit (Google)", value=True)
    st.markdown("---")
    
    # --- BAHAGIAN: TETAPAN WARNA & WIDTH ---
    st.subheader("🎨 Tetapan Visual")
    label_color = st.color_picker("Warna Teks (Bearing/Jarak)", "#FFFF00") 
    line_color = st.color_picker("Warna Garisan Sempadan", "#FF0000") 
    line_width = st.slider("Ketebalan Garisan", 1, 10, 4)
    font_size = st.slider("Saiz Tulisan Label", 6, 16, 9)

    st.markdown("---")
    st.info("🖱️ **Tips Interaktif:**\n1. Hover poligon untuk info luas.\n2. Klik stesen untuk koordinat.")
    show_line_labels = st.checkbox("Papar Bearing & Jarak", value=True)
    
    st.markdown("---")
    epsg_input = st.text_input("Sistem Koordinat (EPSG)", value="4390")
    zoom_margin = st.slider("Margin Zoom (Meter)", 0, 500, 50, step=10)
    
    if st.button("Log Keluar"):
        st.session_state['auth'] = False
        st.rerun()

# ================= 5. PEMPROSESAN & VISUALISASI PETA =================
st.title("📋 Pelan Interaktif Bersepadu")

uploaded_file = st.file_uploader("Muat naik CSV Koordinat (E, N)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    if {"E", "N"}.issubset(df.columns):
        # --- Pemprosesan Data ---
        pts = [Point(x, y) for x, y in zip(df["E"], df["N"])]
        polygon = Polygon([(p.x, p.y) for p in pts])
        luas, perimeter = polygon.area, polygon.length
        
        # Penukaran Projeksi (Asal -> WGS84 untuk Folium)
        gdf_poly = gpd.GeoDataFrame(index=[0], geometry=[polygon], crs=f"EPSG:{epsg_input}")
        
        # Tambah Points ke dalam GeoDataFrame untuk eksport
        gdf_points = gpd.GeoDataFrame(df, geometry=pts, crs=f"EPSG:{epsg_input}")
        
        gdf_4326 = gdf_poly.to_crs(epsg=4326)
        bounds = gdf_4326.total_bounds
        centroid_4326 = gdf_4326.geometry.centroid[0]
        coords_4326 = list(gdf_4326.geometry.exterior[0].coords)

        # Inisialisasi Peta Folium
        m = folium.Map(location=[centroid_4326.y, centroid_4326.x], zoom_start=18, control_scale=True, max_zoom=22)

        # 1. Lapisan Satelit
        if show_sat:
            folium.TileLayer(tiles=TILE_GOOGLE, attr='Google', name='Satellite', max_zoom=22, max_native_zoom=20).add_to(m)

        # 2. Lapisan Poligon
        info_tooltip = f"""
            <div style='font-family: Arial; font-size: 11pt; padding: 5px; width: 180px;'>
                <b style='color: {line_color};'>MAKLUMAT TANAH</b><br>
                <b>Pemilik:</b> {st.session_state['current_user']}<br>
                <b>Luas:</b> {luas:.2f} m²<br>
                <b>Perimeter:</b> {perimeter:.2f} m
            </div>
        """
        folium.GeoJson(
            gdf_4326,
            name="Sempadan Tanah",
            style_function=lambda x: {
                'color': line_color, 
                'weight': line_width, 
                'fillOpacity': 0.2
            },
            highlight_function=lambda x: {'weight': line_width + 3, 'fillOpacity': 0.4, 'color': 'white'},
            tooltip=folium.Tooltip(info_tooltip)
        ).add_to(m)

        # 3. Lapisan Titik Stesen
        for i, row in df.iterrows():
            p_gdf = gpd.GeoDataFrame(index=[0], geometry=[Point(row['E'], row['N'])], crs=f"EPSG:{epsg_input}").to_crs(epsg=4326)
            lat, lon = p_gdf.geometry.iloc[0].y, p_gdf.geometry.iloc[0].x
            
            stn_popup = f"""
                <div style='font-family: Arial; font-size: 10pt; width: 130px;'>
                    <b style='color: blue;'>STESEN {i+1}</b><hr style='margin:3px;'>
                    <b>E:</b> {row['E']:.2f}<br>
                    <b>N:</b> {row['N']:.2f}
                </div>
            """
            folium.CircleMarker(
                [lat, lon], radius=6, color='white', fill=True, fill_color='black', weight=2,
                popup=folium.Popup(stn_popup, max_width=200)
            ).add_to(m)

        # 4. Logic: Bearing & Jarak
        if show_line_labels:
            points_list = list(polygon.exterior.coords)
            for i in range(len(points_list) - 1):
                p1, p2 = points_list[i], points_list[i+1]
                p1_4, p2_4 = coords_4326[i], coords_4326[i+1]
                
                dist = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                bearing_deg = np.degrees(np.arctan2(dx, dy)) % 360
                line_angle_deg = np.degrees(np.arctan2(dy, dx))
                
                rotation = -line_angle_deg 
                if 90 < abs(line_angle_deg) <= 270:
                    rotation += 180

                mid_lat, mid_lon = (p1_4[1] + p2_4[1]) / 2, (p1_4[0] + p2_4[0]) / 2
                
                rotated_html = f"""
                    <div style="transform: rotate({rotation}deg); white-space: nowrap; 
                                font-size: {font_size}pt; 
                                color: {label_color}; font-weight: bold; 
                                text-shadow: 2px 2px 2px black; 
                                text-align: center; width: 110px;">
                        {dist:.2f}m<br>{format_to_dms(bearing_deg)}
                    </div>"""
                folium.Marker([mid_lat, mid_lon], icon=folium.DivIcon(html=rotated_html, icon_anchor=(55,15))).add_to(m)

        # 5. Render Peta
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]], padding=(zoom_margin, zoom_margin))
        st_folium(m, width="100%", height=750)

        # 6. Analisis & Eksport
        st.markdown("---")
        
        combined_gdf = pd.concat([gdf_poly, gdf_points], ignore_index=True)
        geojson_data = combined_gdf.to_json()

        col_a, col_b = st.columns(2)
        col_a.metric("Luas (Ekar)", f"{luas/4046.86:.3f} ekar")
        col_b.download_button(
            label="📥 Muat Turun GeoJSON (Poligon + Titik)",
            data=geojson_data,
            file_name="pelan_tanah_lengkap.geojson",
            mime="application/json"
        )

    else:
        st.error("Ralat: Fail CSV tidak mengandungi lajur 'E' dan 'N'.")
