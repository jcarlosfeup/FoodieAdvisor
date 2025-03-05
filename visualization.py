import streamlit
import folium
import base64
from storage import ReadWriterCSVHandler, FILENAME, BUCKET_NAME
from streamlit_folium import st_folium
from input import get_cities_df


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


def create_selectbox_list(cities: list):
    city = streamlit.selectbox(label="Where you at?",
                               options=cities,
                               index=None,
                               placeholder="Select city")
    return city


if __name__ == "__main__":
    bucket_writer = ReadWriterCSVHandler(filename=FILENAME,
                                         bucket_name=BUCKET_NAME)
    bucket_writer.read_df_from_bucket()
    print(bucket_writer.df)

    city_list = get_cities_df()['name'].unique()

    #city_list = list(filter(lambda k: 'Porto' in k and len(k) == 5, city_list))

    add_background_image(path="assets/images/background.jpg")

    streamlit.title("Foodie Advisor")
    streamlit.markdown("#### Best local cuisine according with your location")
    city = create_selectbox_list(city_list)

    print(f"City is {city}")
    filtered_data = bucket_writer.df[bucket_writer.df['city'] == city]

    if len(filtered_data.index) > 0:
        mapa = folium.Map(location=[filtered_data["latitude"].mean(), filtered_data["longitude"].mean()],
                                    zoom_start=13)

        for _, row in filtered_data.iterrows():
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
