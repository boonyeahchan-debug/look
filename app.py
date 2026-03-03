import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, Point
import folium
from streamlit_folium import st_folium
import numpy as np
from PIL import Image

# ================= 1. CONFIGURATION & SETTINGS =================
PASSWORD = "admin123"
# Provider URL untuk Google Satellite & Esri
TILE_GOOGLE = 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}'
TILE_ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'

st.set_page_config(layout="wide", page_title="Sistem WebGIS Tanah")

# ================= 2. UTILITIES =================
def format_to_dms(deg):
    """Format Decimal ke Darjah Minit Saat (DMS)."""
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return f"{d}°{m:02d}'{sd:02.0f}\""

# ================= 3. SIDEBAR & AUTHENTICATION =================
with st.sidebar:
    try:
        img = Image.open("logo.png") 
        st.image(img, use_container_width=True)
    except:
        st.info("Logo 'logo.png' tidak dijumpai (Sila upload ke direktori).")
    
    st.markdown("### 🏛️ SISTEM MAKLUMAT TANAH")
    st.markdown("---")
    user_password = st.text_input("Kata Laluan", type="password")

# ================= 4. MAIN PROGRAM =================
if user_password == PASSWORD:
    st.sidebar.success("Akses Diterima")
    st.title("🗺️ Visualisasi Poligon & Point Stesen (Leaflet)")

    uploaded_file = st.file_uploader("Muat naik CSV (Kolum: E, N)", type=["csv"])

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        
        if {"E", "N"}.issubset(df.columns):
            # --- Tetapan Layer di Sidebar ---
            st.sidebar.markdown("---")
            st.sidebar.subheader("Kawalan Peta")
            epsg_input = st.sidebar.text_input("Kod EPSG Asal", value="4390")
            
            # --- UPDATE: ZOOM MARGIN SLIDER STEP 10 (MIN 0 MAX 1000) ---
            zoom_margin = st.sidebar.slider(
                "Zoom Margin (Padding)", 
                min_value=0, 
                max_value=1000, 
                value=50, 
                step=10
            )
            
            # Checkbox On/Off Layer
            show_points = st.sidebar.checkbox("Papar Point Stesen", value=True)
            show_poly = st.sidebar.checkbox("Papar Sempadan Poligon", value=True)
            
            # --- Pemprosesan Geospatial ---
            coords = list(zip(df["E"], df["N"]))
            poly_geom = Polygon(coords)
            
            gdf_poly = gpd.GeoDataFrame(index=[0], geometry=[poly_geom], crs=f"EPSG:{epsg_input}")
            gdf_poly_4326 = gdf_poly.to_crs(epsg=4326)
            
            gdf_points = gpd.GeoDataFrame(
                df, 
                geometry=[Point(x, y) for x, y in zip(df['E'], df['N'])], 
                crs=f"EPSG:{epsg_input}"
            ).to_crs(epsg=4326)

            # --- Paparan Metrik ---
            area_val = gdf_poly.geometry.area[0]
            m1, m2, m3 = st.columns(3)
            m1.metric("Luas Tanah", f"{area_val:.2f} m²")
            m2.metric("Bilangan Point", len(df))
            m3.metric("Sistem Koordinat", f"EPSG:{epsg_input}")

            # --- Penjanaan Peta Leaflet (Folium) ---
            # Dapatkan Bounds untuk kegunaan fit_bounds
            bounds = gdf_poly_4326.total_bounds # [minx, miny, maxx, maxy]
            sw = [bounds[1], bounds[0]]
            ne = [bounds[3], bounds[2]]

            m = folium.Map(control_scale=True)

            # Menambah Layer Satelit
            folium.TileLayer(
                tiles=TILE_GOOGLE, attr='Google', name='Google Satellite',
                overlay=False, control=True
            ).add_to(m)
            
            folium.TileLayer(
                tiles=TILE_ESRI, attr='Esri', name='Esri Satellite',
                overlay=False, control=True
            ).add_to(m)

            # Tambah Poligon
            if show_poly:
                folium.GeoJson(
                    gdf_poly_4326,
                    name="Sempadan Poligon",
                    style_function=lambda x: {
                        'fillColor': '#ffff00', 
                        'color': '#ff0000', 
                        'weight': 3, 
                        'fillOpacity': 0.1
                    }
                ).add_to(m)

            # Tambah Point Stesen
            if show_points:
                for idx, row in gdf_points.iterrows():
                    folium.CircleMarker(
                        location=[row.geometry.y, row.geometry.x],
                        radius=4, color='white', weight=2, fill=True, fill_color='red', fill_opacity=1,
                        popup=f"<b>STN {idx+1}</b><br>E: {df.iloc[idx]['E']}<br>N: {df.iloc[idx]['N']}"
                    ).add_to(m)
                    
                    folium.Marker(
                        location=[row.geometry.y, row.geometry.x],
                        icon=folium.DivIcon(html=f"""<div style="font-family: sans-serif; color: yellow; font-weight: bold; font-size: 10pt; width: 100px;">STN {idx+1}</div>""")
                    ).add_to(m)

            # --- PELAKSANAAN ZOOM MARGIN ---
            # Padding menggunakan nilai dari slider
            m.fit_bounds([sw, ne], padding=(zoom_margin, zoom_margin))

            folium.LayerControl().add_to(m)
            st_folium(m, width="100%", height=600, returned_objects=[])

            # --- Eksport Data ---
            st.markdown("---")
            st.subheader("📥 Eksport Data Profesional")
            col_ex1, col_ex2 = st.columns(2)
            
            with col_ex1:
                st.download_button("Eksport GeoJSON (EPSG:4390)", gdf_poly.to_json(), "data_kertau.geojson")
            with col_ex2:
                csv_out = df.to_csv(index=False).encode('utf-8')
                st.download_button("Eksport CSV Koordinat", csv_out, "senarai_koordinat.csv")

        else:
            st.error("Ralat: Fail CSV tidak mempunyai lajur 'E' dan 'N'.")

elif user_password != "":
    st.sidebar.error("Kata laluan salah. Sila hubungi pentadbir.")
else:
    st.info("Sila masukkan kata laluan di sidebar untuk memulakan sistem.")
