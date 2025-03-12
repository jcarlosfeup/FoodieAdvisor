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
    streamlit.markdown(html_template,
                       unsafe_allow_html=True)


def create_marker_icon(path: str):
    return folium.CustomIcon(icon_image=path,
                             icon_size=(30, 30))


def create_headings():
    streamlit.title("Foodie Advisor")
    streamlit.markdown("#### Best local cuisine according with your location")

def create_selectbox_list(cities: list):
    city = streamlit.selectbox(label="Where you at?",
                               options=cities,
                               index=None,
                               placeholder="Select city")
    return city


def displayMapWithMarkers(filtered_df):
    if len(filtered_df.index) > 0:
        mapa = folium.Map(location=[filtered_df["latitude"].mean(), filtered_df["longitude"].mean()],
                        zoom_start=13)

        for _, row in filtered_df.iterrows():
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=f"{row['name']} (Rating: {row['rating']})",
                tooltip=row["name"],
                icon=create_marker_icon(path="assets/images/icon.png")
            ).add_to(mapa)

        st_folium(mapa,
                width=700,
                height=500)
    else:
        streamlit.subheader("No results founds in this city!")
