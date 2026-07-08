import streamlit
import folium
import base64
from streamlit_folium import st_folium


def add_background_image(path: str):
    with open(path, "rb") as file:
        encoded_image = base64.b64encode(file.read()).decode()

    # taken from https://stackoverflow.com/questions/72582550/how-do-i-add-background-image-in-streamlit
    html_template = """
    <style>
    .stApp {
    background-image: url("data:image/png;base64,%s");
    background-size: cover;
    }
    </style>
    """ % encoded_image
    streamlit.markdown(html_template, unsafe_allow_html=True)


def create_marker_icon(path: str):
    return folium.CustomIcon(icon_image=path, icon_size=(30, 30))


def create_headings():
    streamlit.title("Foodie Advisor")
    streamlit.markdown("#### Best local cuisine according with your location")


def create_selectbox_list(cities: list, default: int = None):
    """Create a selectbox for city selection.

    Args:
        cities: List of city names to display
        default: Index of the default city to select (optional)

    Returns:
        Selected city name or None
    """
    city = streamlit.selectbox(
        label="Where you at?", options=cities, index=default, placeholder="Select city"
    )
    return city


def displayMapWithMarkers(filtered_df, city_name: str = None, city_coordinates: tuple | None = None):
    if filtered_df is not None and not filtered_df.is_empty():
        latitude, longitude = city_coordinates

        mapa = folium.Map(
            location=[latitude, longitude],
            zoom_start=12,
        )

        for row in filtered_df.iter_rows(named=True):
            folium.Marker(
                location=[row["latitude"], row["longitude"]],
                popup=f"{row['name']} (Rating: {row['rating']})",
                tooltip=row["name"],
                icon=create_marker_icon(path="assets/images/icon.png"),
            ).add_to(mapa)

        map_key = f"restaurant-map-{city_name or 'default'}"
        st_folium(mapa, width=700, height=500, key=map_key)
    else:
        streamlit.subheader("No results founds in this city!")
