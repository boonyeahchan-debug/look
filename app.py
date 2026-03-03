import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, Point
import folium
from streamlit_folium import st_folium
import numpy as np
import time

# ================= 1. KONFIGURASI & SESSION STATE =================
st.set_page_config(layout="wide", page_title="Sistem WebGIS Tanah V2 - Ultimate Combine")

TILE_GOOGLE = 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}'

# Database Pemilik Sah
USER_DATABASE = {
    1: "Chan Boon Yeah",
    2: "Wong Yuean Yi",
    3: "Ooi Sue Ann"
}

if 'auth' not in st.session_state: st.session_state['auth'] = False
if 'master_password' not in st.session_state: st.session_state['master_password'] = "admin123"
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
                    st.error("ID atau Kata Laluan Salah!")
            if st.button("Lupa Kata Laluan?"): st.session_state['reset_mode'] = True; st.rerun()
    st.stop()

# ================= 4. INTERFACE KAWALAN SIDEBAR =================
with st.sidebar:
    st.success(f"Log Masuk: {st.session_state['current_user']} ✨")
    st.header("🎮 Kawalan Lapisan (On/Off)")
    
    show_sat = st.checkbox("Peta Satelit (Google)", value=False)
    st.markdown("---")
    show_pts = st.checkbox("Point Stesen (Markers)", value=True)
    show_coords = st.checkbox("Label Koordinat (E, N)", value=True)
    show_line_labels = st.checkbox("Label Bearing & Jarak (Auto-Rotate)", value=True)
    show_area_info = st.checkbox("Detail (Pemilik & Luas)", value=True)
    
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
        # --- Pemprosesan Data Asal ---
        pts = list(zip(df["E"], df["N"]))
        polygon = Polygon(pts)
        luas = polygon.area
        perimeter = polygon.length
        
        # Penukaran Projeksi (Asal -> WGS84 untuk Folium)
        gdf_poly = gpd.GeoDataFrame(index=[0], geometry=[polygon], crs=f"EPSG:{epsg_input}")
        gdf_4326 = gdf_poly.to_crs(epsg=4326)
        bounds = gdf_4326.total_bounds
        centroid_4326 = gdf_4326.geometry.centroid[0]
        coords_4326 = list(gdf_4326.geometry.exterior[0].coords)

        # Inisialisasi Peta
        m = folium.Map(location=[centroid_4326.y, centroid_4326.x], zoom_start=18, control_scale=True, max_zoom=22)

        # 1. Lapisan Satelit
        if show_sat:
            folium.TileLayer(tiles=TILE_GOOGLE, attr='Google', name='Satellite', max_zoom=22, max_native_zoom=20).add_to(m)

        # 2. Lapisan Pelan Teknikal (Boundary Merah)
        folium.GeoJson(gdf_4326, name="Sempadan Tanah", style_function=lambda x: {'color':'red', 'weight':4, 'fillOpacity':0.1}).add_to(m)

        # 3. Lapisan Label Dinamik (Stesen & Koordinat)
        for i, row in df.iterrows():
            p_gdf = gpd.GeoDataFrame(index=[0], geometry=[Point(row['E'], row['N'])], crs=f"EPSG:{epsg_input}").to_crs(epsg=4326)
            lat, lon = p_gdf.geometry.iloc[0].y, p_gdf.geometry.iloc[0].x
            
            if show_pts:
                folium.CircleMarker([lat, lon], radius=5, color='white', fill=True, fill_color='black', weight=2).add_to(m)
            
            if show_coords:
                label_stn = f"""<div style="font-size: 8pt; color: white; background: rgba(0,0,0,0.7); 
                                padding: 3px; border-radius: 4px; width: 90px; border: 1px solid red;">
                                <b>STN {i+1}</b><br>E: {row['E']:.2f}<br>N: {row['N']:.2f}</div>"""
                folium.Marker([lat, lon], icon=folium.DivIcon(html=label_stn, icon_anchor=(-10, 10))).add_to(m)

        # 4. Logic: Bearing & Jarak dengan Auto-Rotation
        if show_line_labels:
            points = list(polygon.exterior.coords)
            for i in range(len(points) - 1):
                p1 = points[i] # Asal (E, N)
                p2 = points[i+1]
                p1_4, p2_4 = coords_4326[i], coords_4326[i+1] # WGS84
                
                # Pengiraan Jarak & Bearing
                dist = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                angle_rad = np.arctan2(p2[0] - p1[0], p2[1] - p1[1])
                bearing_deg = np.degrees(angle_rad) % 360
                bearing_str = format_to_dms(bearing_deg)

                # Pengiraan Rotation (CSS)
                dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                line_angle_deg = np.degrees(np.arctan2(dy, dx))
                
                # Laraskan sudut supaya teks selari dan tidak terbalik
                rotation = -line_angle_deg 
                if 90 < abs(line_angle_deg) <= 270:
                    rotation += 180

                mid_lat, mid_lon = (p1_4[1] + p2_4[1]) / 2, (p1_4[0] + p2_4[0]) / 2
                
                rotated_html = f"""
                <div style="transform: rotate({rotation}deg); white-space: nowrap; font-size: 9pt; 
                            color: yellow; font-weight: bold; text-shadow: 2px 2px 2px black; 
                            text-align: center; width: 110px;">
                    {dist:.2f}m<br>{bearing_str}
                </div>"""
                folium.Marker([mid_lat, mid_lon], icon=folium.DivIcon(html=rotated_html, icon_anchor=(55,15))).add_to(m)

        # 5. Info Poligon (Tengah)
        if show_area_info:
            info_html = f"""<div style="font-size: 10pt; color: white; background: #000; 
                            padding: 10px; border-radius: 8px; border: 2px solid #FFD700; width: 200px; text-align: center;">
                            <b style='color: #FFD700;'>PEMILIK: {st.session_state['current_user']}</b><hr style='margin:5px;'>
                            LUAS: {luas:.2f} m²<br>PERIMETER: {perimeter:.2f} m</div>"""
            folium.Marker([centroid_4326.y, centroid_4326.x], icon=folium.DivIcon(html=info_html, icon_anchor=(100,40))).add_to(m)

        # Final Render
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]], padding=(zoom_margin, zoom_margin))
        st_folium(m, width="100%", height=750)

        # Eksport & Ringkasan
        st.markdown("---")
        col_a, col_b = st.columns(2)
        col_a.metric("Luas (Ekar)", f"{luas/4046.86:.3f} ekar")
        col_b.download_button("Download GeoJSON", gdf_poly.to_json(), "pelan_muktamad.geojson")

    else:
        st.error("Ralat: Fail CSV tidak mengandungi lajur 'E' dan 'N'.")
