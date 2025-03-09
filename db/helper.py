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


def insert_into_table(table_name: str, ):
    cursor = connection.execute(f"SELECT * from {table_name}")

    cols_names = [description[0] for description in cursor.description]
    num_cols = len(cols_names)
    cols_names = ', '.join(cols_names)

    fillers = ["?" for i in range(num_cols)]
    fillers = ', '.join(fillers)

    sql_statement = f"INSERT INTO {table_name} ({cols_names}) VALUES ({fillers})", ('John Doe', 'Software Engineer', 80000)
    print(sql_statement)

    cursor.execute(sql_statement)
    connection.commit()


if __name__ == "__main__":
    schema_stat = "(id INTEGER PRIMARY KEY, name TEXT, city TEXT, rating REAL, userRatingCount INTEGER, latitude REAL, longitude REAL, viewport TEXT)"
    create_table(table_name="restaurant",
                 schema=schema_stat)
    
    insert_into_table(table_name="restaurant")



    

    
