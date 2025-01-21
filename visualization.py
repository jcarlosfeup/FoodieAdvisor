import streamlit
import folium
from storage import ReadWriterCSVHandler, FILENAME, BUCKET_NAME
from streamlit_folium import st_folium


def create_marker_icon(path: str):
    return folium.CustomIcon(icon_image=path,
                             icon_size=(30, 30))


if __name__ == "__main__":
    bucket_writer = ReadWriterCSVHandler(filename=FILENAME,
                                         bucket_name=BUCKET_NAME)
    bucket_writer.read_df_from_bucket()

    print(bucket_writer.df)

    streamlit.title("Foodie Advisor - Best Restaurants by location")
    city = streamlit.selectbox("Select a city",
                               bucket_writer.df['city'].unique())
    
    filtered_data = bucket_writer.df[bucket_writer.df['city'] == city]

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
