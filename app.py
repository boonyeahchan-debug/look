import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, Point
import folium
from streamlit_folium import st_folium
import numpy as np
from PIL import Image

# ================= 1. KONFIGURASI SISTEM =================
PASSWORD = "admin123"
# URL untuk Google Satellite (s=satellite)
TILE_GOOGLE = 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}'

st.set_page_config(layout="wide", page_title="Sistem WebGIS Tanah")

# ================= 2. FUNGSI UTILITI =================
def format_to_dms(deg):
    """Format Decimal ke Darjah Minit Saat (DMS)."""
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return f"{d}°{m:02d}'{sd:02.0f}\""

# ================= 3. SIDEBAR & LOG MASUK =================
with st.sidebar:
    try:
        img = Image.open("logo.png") 
        st.image(img, use_container_width=True)
    except:
        st.info("Logo 'logo.png' tidak dijumpai.")
    
    st.markdown("### 🏛️ SISTEM MAKLUMAT TANAH")
    st.markdown("---")
    user_password = st.text_input("Kata Laluan", type="password")

# ================= 4. PROGRAM UTAMA =================
if user_password == PASSWORD:
    st.sidebar.success("Akses Diterima")
    st.title("🗺️ Visualisasi Poligon & Point Stesen")

    uploaded_file = st.file_uploader("Muat naik CSV (E, N)", type=["csv"])

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        
        if {"E", "N"}.issubset(df.columns):
            # --- TETAPAN ZOOM & LAYER ---
            st.sidebar.markdown("---")
            st.sidebar.subheader("Kawalan Paparan")
            
            # Zoom Margin: Min 0, Max 1000, Step 10
            zoom_margin = st.sidebar.slider(
                "Zoom Margin (Padding Pixel)", 
                min_value=0, 
                max_value=1000, 
                value=50, 
                step=10
            )
            
            epsg_input = st.sidebar.text_input("Kod EPSG Asal", value="4390")
            show_points = st.sidebar.checkbox("Papar Point Stesen", value=True)
            show_poly = st.sidebar.checkbox("Papar Sempadan Poligon", value=True)
            
            # --- PEMPROSESAN GEOSPATIAL ---
            coords = list(zip(df["E"], df["N"]))
            poly_geom = Polygon(coords)
            
            # Reprojeksi ke WGS84 (EPSG:4326) untuk Folium
            gdf_poly = gpd.GeoDataFrame(index=[0], geometry=[poly_geom], crs=f"EPSG:{epsg_input}")
            gdf_poly_4326 = gdf_poly.to_crs(epsg=4326)
            
            gdf_points = gpd.GeoDataFrame(
                df, geometry=[Point(x, y) for x, y in zip(df['E'], df['N'])], 
                crs=f"EPSG:{epsg_input}"
            ).to_crs(epsg=4326)

            # Paparan Metrik
            area_val = gdf_poly.geometry.area[0]
            m1, m2, m3 = st.columns(3)
            m1.metric("Luas Tanah", f"{area_val:.2f} m²")
            m2.metric("Bilangan Point", len(df))
            m3.metric("Sistem", f"EPSG:{epsg_input}")

            # --- PENJANAAN PETA LEAFLET ---
            bounds = gdf_poly_4326.total_bounds
            sw = [bounds[1], bounds[0]]
            ne = [bounds[3], bounds[2]]

            # Hadkan max_zoom=20 untuk elak ralat 404 Google
            m = folium.Map(control_scale=True, max_zoom=20)

            # Lapisan 1: OpenStreetMap (Default)
            folium.TileLayer('openstreetmap', name='OpenStreetMap').add_to(m)

            # Lapisan 2: Google Satellite
            folium.TileLayer(
                tiles=TILE_GOOGLE, 
                attr='Google Satellite', 
                name='Google Satellite',
                overlay=False, 
                control=True
            ).add_to(m)

            # Tambah Poligon
            if show_poly:
                folium.GeoJson(
                    gdf_poly_4326,
                    name="Sempadan Poligon",
                    style_function=lambda x: {'fillColor': 'yellow', 'color': 'red', 'weight': 3, 'fillOpacity': 0.15}
                ).add_to(m)

            # Tambah Point & Label
            if show_points:
                for idx, row in gdf_points.iterrows():
                    folium.CircleMarker(
                        location=[row.geometry.y, row.geometry.x],
                        radius=5, color='white', weight=2, fill=True, fill_color='red', fill_opacity=1
                    ).add_to(m)
                    
                    folium.Marker(
                        location=[row.geometry.y, row.geometry.x],
                        icon=folium.DivIcon(html=f"""<div style="font-family: sans-serif; color: yellow; font-weight: bold; font-size: 10pt; text-shadow: 1px 1px black; width: 100px;">STN {idx+1}</div>""")
                    ).add_to(m)

            # --- LOGIK ZOOM MARGIN (PADDING) ---
            m.fit_bounds([sw, ne], padding=(zoom_margin, zoom_margin))

            folium.LayerControl().add_to(m)
            st_folium(m, width="100%", height=600, returned_objects=[])

            # Eksport
            st.download_button("📥 Eksport GeoJSON", gdf_poly.to_json(), "data.geojson")

        else:
            st.error("Fail CSV tidak sah (Perlu lajur E dan N).")

elif user_password != "":
    st.sidebar.error("Kata laluan salah.")
else:
    st.info("Sila log masuk untuk memulakan sistem.")
