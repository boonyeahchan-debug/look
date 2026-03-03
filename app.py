import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, Point
import folium
from streamlit_folium import st_folium
import numpy as np
from PIL import Image

# ================= 1. CONFIGURATION =================
PASSWORD = "admin123"
TILE_GOOGLE = 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}'

st.set_page_config(layout="wide", page_title="Sistem WebGIS Tanah")

# ================= 2. SIDEBAR & AUTH =================
with st.sidebar:
    try:
        img = Image.open("logo.png") 
        st.image(img, use_container_width=True)
    except:
        st.info("Logo tidak dijumpai.")
    
    st.markdown("### 🏛️ SISTEM MAKLUMAT TANAH")
    st.markdown("---")
    user_password = st.text_input("Kata Laluan", type="password")

if user_password == PASSWORD:
    st.sidebar.success("Akses Diterima")
    
    uploaded_file = st.file_uploader("Muat naik CSV", type=["csv"])

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        
        if {"E", "N"}.issubset(df.columns):
            # --- ADJUSTMENT: ZOOM MARGIN DENGAN STEP 10 ---
            st.sidebar.markdown("---")
            st.sidebar.subheader("Kawalan Paparan")
            
            # Slider dengan step=10
            zoom_step = st.sidebar.slider(
                "Larasan Zoom (Step 10)", 
                min_value=0, 
                max_value=200, 
                value=50, 
                step=10
            )
            
            show_points = st.sidebar.checkbox("Papar Point Stesen", value=True)
            
            # --- Pemprosesan Data ---
            epsg_input = "4390" # Lalai Kertau
            coords = list(zip(df["E"], df["N"]))
            poly_geom = Polygon(coords)
            
            gdf_poly = gpd.GeoDataFrame(index=[0], geometry=[poly_geom], crs=f"EPSG:{epsg_input}")
            gdf_poly_4326 = gdf_poly.to_crs(epsg=4326)
            
            # --- PETA LEAFLET ---
            # Dapatkan Bounds (Sempadan) poligon
            bounds = gdf_poly_4326.total_bounds # [minx, miny, maxx, maxy]
            sw = [bounds[1], bounds[0]]
            ne = [bounds[3], bounds[2]]
            
            # Cipta Peta
            m = folium.Map(control_scale=True)

            # Tambah Google Satellite
            folium.TileLayer(
                tiles=TILE_GOOGLE, attr='Google', name='Google Satellite',
                overlay=False, control=True
            ).add_to(m)

            # Tambah Poligon
            folium.GeoJson(
                gdf_poly_4326,
                style_function=lambda x: {'color': 'red', 'fillOpacity': 0.1}
            ).add_to(m)

            if show_points:
                gdf_points = gpd.GeoDataFrame(
                    df, geometry=[Point(x, y) for x, y in zip(df['E'], df['N'])], 
                    crs=f"EPSG:{epsg_input}"
                ).to_crs(epsg=4326)
                
                for idx, row in gdf_points.iterrows():
                    folium.CircleMarker(
                        location=[row.geometry.y, row.geometry.x],
                        radius=5, color='white', fill=True, fill_color='red'
                    ).add_to(m)

            # --- FIT BOUNDS DENGAN PADDING BERDASARKAN SLIDER ---
            # Nilai zoom_step digunakan sebagai padding (pixel) untuk fit_bounds
            m.fit_bounds([sw, ne], padding=(zoom_step, zoom_step))

            st_folium(m, width="100%", height=600)
            
            st.success(f"Zoom dilaraskan dengan padding: {zoom_step}")
        else:
            st.error("Kolum E & N tidak dijumpai.")
