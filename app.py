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
TILE_GOOGLE = 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}'

st.set_page_config(layout="wide", page_title="Sistem WebGIS Tanah")

# Inisialisasi status log masuk dalam session state
if 'auth' not in st.session_state:
    st.session_state['auth'] = False

# ================= 2. HALAMAN LOG MASUK (SKRIN PENUH) =================
if not st.session_state['auth']:
    # Menggunakan kolum untuk meletakkan kotak login di tengah
    _, col_mid, _ = st.columns([1, 1.5, 1])
    
    with col_mid:
        st.write("#") # Ruang kosong atas
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
                st.error("Kata laluan salah. Sila hubungi Unit GIS.")
    
    # Hentikan proses kod di sini jika belum log masuk
    st.stop()

# ================= 3. PROGRAM UTAMA (SELEPAS AKSES DITERIMA) =================
# Tab password sudah tidak kelihatan lagi di sini

# Butang Log Keluar di Sidebar untuk keselamatan
if st.sidebar.button("Log Keluar 🔓"):
    st.session_state['auth'] = False
    st.rerun()

st.title("🌍 WebGIS Interaktif: Lot Tanah & Stesen")

uploaded_file = st.file_uploader("Muat naik CSV Koordinat (Lajur: E, N)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    if {"E", "N"}.issubset(df.columns):
        # --- Kawalan Sidebar ---
        st.sidebar.header("Tetapan Paparan")
        
        # Slider Zoom Margin (Min 0, Max 1000, Step 10)
        zoom_margin = st.sidebar.slider(
            "Zoom Margin (Padding Pixel)", 
            min_value=0, 
            max_value=1000, 
            value=100, 
            step=10
        )
        
        epsg_input = st.sidebar.text_input("Kod EPSG (Contoh: 4390)", value="4390")
        
        st.sidebar.markdown("---")
        show_points = st.sidebar.toggle("Papar Point Stesen", value=True)
        show_poly = st.sidebar.toggle("Papar Sempadan Poligon", value=True)
        
        # --- Pemprosesan Data Geospatial ---
        coords = list(zip(df["E"], df["N"]))
        poly_geom = Polygon(coords)
        
        # GeoDataFrame untuk Poligon
        gdf_poly = gpd.GeoDataFrame(index=[0], geometry=[poly_geom], crs=f"EPSG:{epsg_input}")
        gdf_poly_4326 = gdf_poly.to_crs(epsg=4326) # Tukar ke Lat/Long untuk peta
        
        # GeoDataFrame untuk Points
        gdf_points = gpd.GeoDataFrame(
            df, 
            geometry=[Point(x, y) for x, y in zip(df['E'], df['N'])], 
            crs=f"EPSG:{epsg_input}"
        ).to_crs(epsg=4326)

        # --- Paparan Metrik ---
        area_val = gdf_poly.geometry.area[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Luas Keseluruhan", f"{area_val:.2f} m²")
        c2.metric("Jumlah Stesen", len(df))
        c3.metric("Sistem Koordinat", f"EPSG:{epsg_input}")

        # --- Konfigurasi Peta Leaflet ---
        bounds = gdf_poly_4326.total_bounds # [minx, miny, maxx, maxy]
        sw = [bounds[1], bounds[0]]
        ne = [bounds[3], bounds[2]]

        # Hadkan max_zoom=20 untuk Google Satellite
        m = folium.Map(control_scale=True, max_zoom=20)

        # Menambah Layer Peta
        folium.TileLayer('openstreetmap', name='OpenStreetMap').add_to(m)
        folium.TileLayer(
            tiles=TILE_GOOGLE, 
            attr='Google Satellite', 
            name='Google Satellite',
            overlay=False, 
            control=True
        ).add_to(m)

        # Lukis Poligon
        if show_poly:
            folium.GeoJson(
                gdf_poly_4326,
                name="Lot Tanah",
                style_function=lambda x: {
                    'fillColor': 'yellow', 
                    'color': 'red', 
                    'weight': 3, 
                    'fillOpacity': 0.1
                }
            ).add_to(m)

        # Lukis Point Stesen & Label
        if show_points:
            for idx, row in gdf_points.iterrows():
                # Marker Bulatan
                folium.CircleMarker(
                    location=[row.geometry.y, row.geometry.x],
                    radius=5, color='white', weight=2, fill=True, 
                    fill_color='red', fill_opacity=1
                ).add_to(m)
                
                # Label Kekal (Kuning)
                folium.Marker(
                    location=[row.geometry.y, row.geometry.x],
                    icon=folium.DivIcon(html=f"""
                        <div style="font-family: sans-serif; color: yellow; font-weight: bold; 
                        font-size: 10pt; text-shadow: 2px 2px #000; width: 100px;">
                        STN {idx+1}
                        </div>""")
                ).add_to(m)

        # Gunakan fit_bounds dengan padding dari slider
        m.fit_bounds([sw, ne], padding=(zoom_margin, zoom_margin))

        # Tambah Layer Control & Papar
        folium.LayerControl().add_to(m)
        st_folium(m, width="100%", height=650, returned_objects=[])

        # --- Eksport ---
        st.markdown("---")
        st.download_button("📥 Muat Turun Data GeoJSON", gdf_poly.to_json(), "lot_tanah.geojson")

    else:
        st.error("Ralat: Fail CSV memerlukan lajur 'E' (Easting) dan 'N' (Northing).")
else:
    st.info("Sila muat naik fail CSV untuk memulakan visualisasi peta.")
