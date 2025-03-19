import sqlite3
from sqlalchemy import create_engine

connection = sqlite3.connect('db/restaurants.db')

cursor = connection.cursor()


def create_db_engine():
    return create_engine('sqlite:///db/restaurants.db',
                         echo=False)
    

def create_table(table_name: str, schema: str):
    sql_statement = f"CREATE TABLE IF NOT EXISTS {table_name} {schema}"
    cursor.execute(sql_statement)
    connection.commit()


def drop_table(table_name: str):
    sql_statement = f"DROP TABLE IF EXISTS {table_name}"
    cursor.execute(sql_statement)
    connection.commit()


def query_table(table_name: str) -> list:
    sql_statement = f"SELECT * FROM {table_name}"
    cursor.execute(sql_statement)

    return cursor.fetchall()


def is_city_fetched(city_name: str):
    sql_statement = f"SELECT * FROM city WHERE name = {city_name}"
    cursor.execute(sql_statement)

    return len(cursor.fetchall()) == 0


def add_city_to_db(name: str):
    cursor.execute(f"INSERT INTO city (name) VALUES ('{name}')")
    connection.commit()


def fetch_city_restaurants(city_name: str):
    sql_statement = f"SELECT * FROM restaurant WHERE city = {city_name}"
    cursor.execute(sql_statement)

    return cursor.fetchall()


if __name__ == "__main__":
    """ schema_stat = "(id INTEGER PRIMARY KEY, name TEXT, city TEXT, rating REAL, price_level TEXT, ratings_count INTEGER, latitude REAL, longitude REAL)"

    create_table(table_name="restaurant",
                 schema=schema_stat)

    #drop_table(table_name="restaurant") """

    schema_stat = "(id INTEGER PRIMARY KEY, name TEXT)"

    #create_table(table_name="city",
    #             schema=schema_stat)

    add_city_to_db(name="Porto")

    result = query_table(table_name="city")
    print(result)



    

    
