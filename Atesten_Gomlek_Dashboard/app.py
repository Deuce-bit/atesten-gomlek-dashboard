"""
pass_12_streamlit_codex_map.py — Multi-Pass Architecture: Pass 12 (Codex Dashboard)
═══════════════════════════════════════════════════════════════════════════════════
Interactive web dashboard that seamlessly filters the geographic map by Character, Chapter, 
and Narrative Theme simultaneously, while displaying rich LLM-generated literary codices 
for selected characters.
"""

import streamlit as st
import pandas as pd
import folium
import streamlit.components.v1 as components
import os
import re
import math
import csv

# Configure the Streamlit page
st.set_page_config(page_title="Ateşten Gömlek: Master Dashboard", layout="wide")

# File Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GEO_CSV = os.path.join(BASE_DIR, "Final", "scenes_geocoded.csv")
OCC_CSV = os.path.join(BASE_DIR, "Final", "occurrences_final.csv")
THEME_CSV = os.path.join(BASE_DIR, "Final", "scenes_thematic.csv")
CHARS_CSV = os.path.join(BASE_DIR, "characters_master.csv")
ENRICHED_CHARS_CSV = os.path.join(BASE_DIR, "Final", "characters_enriched.csv")

ALL_THEMES = ['Ideology & Politics', 'Combat & Violence', 'Romance & Tragedy', 'Logistics & Movement']

# Chapter Colors
COLORS = [
    'red', 'blue', 'green', 'purple', 'orange', 
    'darkred', 'lightred', 'darkblue', 'darkgreen', 'cadetblue', 
    'darkpurple', 'pink', 'lightblue', 'lightgreen', 'gray', 'black'
]

# Thematic Colors
THEME_COLORS = {
    'Combat & Violence': 'darkred',
    'Ideology & Politics': 'darkblue',
    'Romance & Tragedy': 'purple',
    'Logistics & Movement': 'gray',
    'Unknown': 'black'
}

def extract_chapter_num(scene_id):
    """Extracts integer chapter number from 'Ch01_...' to use for color coding and sorting."""
    match = re.search(r'Ch(\d+)', str(scene_id))
    return int(match.group(1)) if match else 99

def normalize_scene_id(sid):
    """Normalize scene IDs for perfect merging between passes."""
    match = re.match(r'Ch(\d+)_(.*)', str(sid).strip())
    if match:
        num = int(match.group(1))
        return f"Ch{num:02d}_{match.group(2)}"
    return str(sid).strip()

def load_master_data():
    """Load and perfectly merge all geocoding, occurrence, and thematic data."""
    if not os.path.exists(GEO_CSV) or not os.path.exists(OCC_CSV):
        return pd.DataFrame(), pd.DataFrame()
        
    geo_df = pd.read_csv(GEO_CSV)
    occ_df = pd.read_csv(OCC_CSV)
    
    geo_df["Scene ID"] = geo_df["Scene ID"].apply(normalize_scene_id)
    occ_df["Scene ID"] = occ_df["Scene ID"].apply(normalize_scene_id)
    
    merged_df = pd.merge(occ_df, geo_df, on="Scene ID", how="inner")
    
    # Merge Thematic Data
    if os.path.exists(THEME_CSV):
        theme_df = pd.read_csv(THEME_CSV)
        theme_df["Scene ID"] = theme_df["Scene ID"].apply(normalize_scene_id)
        theme_sub = theme_df[["Scene ID", "Primary Theme", "Theme Justification"]]
        merged_df = pd.merge(merged_df, theme_sub, on="Scene ID", how="left")
        
        merged_df["Primary Theme"] = merged_df["Primary Theme"].fillna("Unknown")
        merged_df["Theme Justification"] = merged_df["Theme Justification"].fillna("")
        
    merged_df = merged_df.dropna(subset=["Latitude", "Longitude"])
    
    char_ranks = {}
    if os.path.exists(CHARS_CSV):
        with open(CHARS_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    char_ranks[row["Name"].strip()] = int(row["Importance Rank"])
                except:
                    pass
    merged_df["Rank"] = merged_df["Character Name"].map(lambda x: char_ranks.get(x, 1))
    
    # Load Enriched Character Codex Data
    codex_df = pd.DataFrame()
    if os.path.exists(ENRICHED_CHARS_CSV):
        codex_df = pd.read_csv(ENRICHED_CHARS_CSV)
    
    return merged_df, codex_df

df, codex_df = load_master_data()

# ═══════════════════════════════════════════════════════════════════
# UI & SIDEBAR LOGIC
# ═══════════════════════════════════════════════════════════════════

st.sidebar.title("Ateşten Gömlek Dashboard")
st.sidebar.markdown("Filter the map by Character, Chapter, and Theme simultaneously.")

st.sidebar.markdown("### Visualization Style")
color_mode = st.sidebar.radio("Color Markers By:", ["Narrative Theme", "Chapter"])

st.sidebar.markdown("---")

if not df.empty:
    # 1. CHARACTER FILTER
    unique_chars = df[["Character Name", "Rank"]].drop_duplicates()
    main_chars = sorted(unique_chars[unique_chars["Rank"] == 5]["Character Name"].tolist())
    side_chars = sorted(unique_chars[unique_chars["Rank"] == 4]["Character Name"].tolist())
    other_chars = sorted(unique_chars[unique_chars["Rank"] <= 3]["Character Name"].tolist())
    
    char_options = ["All Characters"]
    if main_chars:
        char_options += ["--- MAIN CHARACTERS ---"] + main_chars
    if side_chars:
        char_options += ["--- SIDE CHARACTERS ---"] + side_chars
    if other_chars:
        char_options += ["--- OTHER CHARACTERS ---"] + other_chars

    selected_char = st.sidebar.selectbox("Filter by Character", char_options)

    if selected_char.startswith("---"):
        st.warning("Please select a valid character from the list above or below the divider.")
        st.stop()

    # 2. CHAPTER FILTER
    df["Chapter Num"] = df["Scene ID"].apply(extract_chapter_num)
    unique_chapters = sorted(df["Chapter Num"].unique().tolist())
    chapter_options = ["All Chapters"] + [f"Chapter {c}" for c in unique_chapters if c != 99]
    selected_chapter = st.sidebar.selectbox("Filter by Chapter", chapter_options)

    # 3. THEMATIC FILTER
    selected_themes = st.sidebar.multiselect("Filter by Narrative Theme", ALL_THEMES, default=ALL_THEMES)

    # ═══════════════════════════════════════════════════════════════════
    # APPLYING SIMULTANEOUS FILTERS
    # ═══════════════════════════════════════════════════════════════════
    filtered_df = df.copy()
    
    if selected_char != "All Characters":
        filtered_df = filtered_df[filtered_df["Character Name"] == selected_char]
        
    if selected_chapter != "All Chapters":
        ch_target = int(selected_chapter.replace("Chapter ", ""))
        filtered_df = filtered_df[filtered_df["Chapter Num"] == ch_target]

    filtered_df = filtered_df[filtered_df["Primary Theme"].isin(selected_themes)]
    filtered_df = filtered_df.sort_values(by="Scene ID")

    st.sidebar.markdown(f"**Total Events Found:** {len(filtered_df)}")

    # ═══════════════════════════════════════════════════════════════════
    # CHARACTER CODEX INJECTION (ELEGANT EXPANDER)
    # ═══════════════════════════════════════════════════════════════════
    if selected_char == "All Characters":
        st.subheader(f"Geographical Overview")
        st.info("💡 Select a specific character from the sidebar to view their Literary Codex and Analysis.")
    else:
        st.subheader(f"Geographical Journey: {selected_char}")
        
        # Display the Codex inside an elegant, non-intrusive expander above the map
        if not codex_df.empty:
            char_row = codex_df[codex_df["Name"] == selected_char]
            if not char_row.empty:
                char_data = char_row.iloc[0]
                eth = char_data.get("Ethnicity", "Unknown Ethnicity")
                stance = char_data.get("Political Stance", "Unknown Stance")
                desc = char_data.get("Description", "No description available.")
                analysis = char_data.get("literary_analysis", "No analysis available.")
                
                with st.expander(f"📖 Literary Codex: {selected_char}", expanded=False):
                    st.markdown(f"*{eth} | {stance}*")
                    st.markdown("##### Factual Summary")
                    st.write(desc)
                    st.markdown("##### Literary Analysis")
                    st.write(analysis)
    
    # ═══════════════════════════════════════════════════════════════════
    # MAP GENERATION
    # ═══════════════════════════════════════════════════════════════════
    m = folium.Map(location=[39.9, 31.0], zoom_start=6)

    # Build Thematic/Chapter Legend
    legend_html = '''
     <div style="
     position: fixed; 
     bottom: 50px; left: 50px; width: 220px; height: auto; 
     background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
     padding: 10px; border-radius: 5px; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">
     '''
     
    added_to_chapter_legend = set()
    coord_counts = {}
    js_nodes = []

    for _, row in filtered_df.iterrows():
        base_lat = float(row["Latitude"])
        base_lon = float(row["Longitude"])
        ch_num = extract_chapter_num(row["Scene ID"])
        
        # Spiral Jitter for overlapping points
        coord_key = (round(base_lat, 3), round(base_lon, 3))
        count = coord_counts.get(coord_key, 0)
        coord_counts[coord_key] = count + 1
        
        lat = base_lat
        lon = base_lon
        
        if count > 0:
            golden_angle = math.pi * (3 - math.sqrt(5))
            angle = count * golden_angle
            radius = 0.0001 * math.sqrt(count)
            lat += radius * math.sin(angle)
            lon += radius * math.cos(angle)
            
        chapter_str = f"Chapter {ch_num}"
        setting_name = row.get("Setting Name (Location)", row.get("Hierarchical Name", "Unknown Location"))
        action = row.get("Action Summary", "No action summary available.")
        theme = row.get("Primary Theme", "Unknown")
        justification = row.get("Theme Justification", "")
        
        # Color Toggling Logic
        if color_mode == "Chapter":
            color_idx = (ch_num - 1) % len(COLORS)
            marker_color = COLORS[color_idx]
            added_to_chapter_legend.add((ch_num, marker_color))
        else:
            marker_color = THEME_COLORS.get(theme, "black")

        clean_action = str(action).replace('"', '&quot;').replace("'", "&#39;")
        clean_just = str(justification).replace('"', '&quot;').replace("'", "&#39;")
        
        popup_html = f"""
        <div style="width: 320px; font-family: sans-serif;">
            <h4 style="margin-top: 0; color: {marker_color};">{chapter_str} | {theme}</h4>
            <b>Location:</b> {setting_name}<br><br>
            <p style="font-size: 13px;"><b>Action:</b> {clean_action}</p>
            <p style="font-size: 12px; color: #555;"><b>Analysis:</b> {clean_just}</p>
        </div>
        """
        
        safe_popup_html = popup_html.replace('`', '\\`').replace('$', '\\$').replace('\n', '')
        js_nodes.append((lat, lon, safe_popup_html))
        
        html_icon = f"""
            <div style="
                background-color: {marker_color};
                width: 24px;
                height: 24px;
                border-radius: 50%;
                border: 2px solid white;
                color: white;
                text-align: center;
                line-height: 20px;
                font-weight: bold;
                font-size: 12px;
                box-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            ">
                {ch_num}
            </div>
        """

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=400),
            tooltip=f"Ch{ch_num}: {theme} at {setting_name}",
            icon=folium.DivIcon(html=html_icon)
        ).add_to(m)

    # ═══════════════════════════════════════════════════════════════════
    # LEGEND INJECTION
    # ═══════════════════════════════════════════════════════════════════
    if color_mode == "Chapter":
        legend_html += "<b>Chapter Legend</b><br>"
        for ch, color in sorted(list(added_to_chapter_legend)):
            legend_html += f'<i class="fa fa-circle" style="color:{color}"></i> Chapter {ch}<br>'
    else:
        legend_html += "<b>Thematic Legend</b><br>"
        for t in ALL_THEMES:
            t_col = THEME_COLORS.get(t, 'black')
            legend_html += f'<i class="fa fa-circle" style="color:{t_col}"></i> {t}<br>'
            
    legend_html += '</div>'
    m.get_root().html.add_child(folium.Element(legend_html))

    # ═══════════════════════════════════════════════════════════════════
    # INJECT JS STORY NAVIGATOR
    # ═══════════════════════════════════════════════════════════════════
    nav_desc = f"Follow {selected_char}'s journey." if selected_char != "All Characters" else "Follow the chronological sequence."

    story_data_js = ",\n".join([
        f"{{ lat: {lat}, lon: {lon}, html: `{html}` }}"
        for lat, lon, html in js_nodes
    ])

    navigator_html = f'''
    <div style="
        position: fixed; 
        top: 20px; right: 20px; width: 300px; 
        background-color: white; border:2px solid grey; 
        z-index:9999; font-size:14px; padding: 15px; border-radius: 8px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
        font-family: sans-serif;
    ">
        <h3 style="margin-top:0; margin-bottom: 5px;">Story Navigator</h3>
        <p style="margin-top:0; font-size: 12px; color: #555;">{nav_desc}</p>
        <div style="display: flex; justify-content: space-between; margin-top: 15px;">
            <button id="btn-prev" onclick="changeStory(-1)" style="padding: 6px 12px; cursor:pointer; font-weight: bold;">&laquo; Prev</button>
            <span id="story-counter" style="line-height: 28px; font-weight: bold;">1 / {max(1, len(js_nodes))}</span>
            <button id="btn-next" onclick="changeStory(1)" style="padding: 6px 12px; cursor:pointer; font-weight: bold;">Next &raquo;</button>
        </div>
    </div>
    
    <script>
        var storyData = [
            {story_data_js}
        ];
        var currentStoryIdx = 0;
        var mapInstance = null;
        var activePopup = null;

        setTimeout(function() {{
            for (var key in window) {{
                if (window[key] && window[key].flyTo) {{
                    mapInstance = window[key];
                    break;
                }}
            }}
            if (mapInstance && storyData.length > 0) {{
                goToStory(0);
            }}
        }}, 1000);

        function changeStory(dir) {{
            var newIdx = currentStoryIdx + dir;
            if (newIdx >= 0 && newIdx < storyData.length) {{
                goToStory(newIdx);
            }}
        }}

        function goToStory(idx) {{
            currentStoryIdx = idx;
            var node = storyData[idx];
            
            document.getElementById('story-counter').innerText = (idx + 1) + ' / ' + storyData.length;
            document.getElementById('btn-prev').disabled = (idx === 0);
            document.getElementById('btn-next').disabled = (idx === storyData.length - 1);

            mapInstance.flyTo([node.lat, node.lon], 13, {{
                animate: true,
                duration: 1.5
            }});

            setTimeout(function() {{
                if (activePopup) {{
                    mapInstance.closePopup(activePopup);
                }}
                activePopup = L.popup({{offset: [0, -10]}})
                    .setLatLng([node.lat, node.lon])
                    .setContent(node.html)
                    .openOn(mapInstance);
            }}, 500);
        }}
    </script>
    '''
    
    if js_nodes:
        m.get_root().html.add_child(folium.Element(navigator_html))

    components.html(m.get_root().render(), height=650)
else:
    st.warning("No valid data found. Ensure passing scripts have been run.")
