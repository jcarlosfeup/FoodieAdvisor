import sqlite3
import logging
from sqlalchemy import create_engine

logger = logging.getLogger(__name__)

connection = sqlite3.connect('db/restaurants.db')

cursor = connection.cursor()


def create_db_engine():
    return create_engine('sqlite:///db/restaurants.db',
                         echo=False)
    

def create_table(table_name: str, schema: str):
    """Create a table in the database.
    
    Args:
        table_name: Name of the table to create
        schema: SQL schema definition for the table
    """
    try:
        sql_statement = f"CREATE TABLE IF NOT EXISTS {table_name} {schema}"
        cursor.execute(sql_statement)
        connection.commit()
        logger.info(f"Table '{table_name}' created or already exists")
    except sqlite3.Error as e:
        logger.error(f"Error creating table '{table_name}': {e}")
        raise


def drop_table(table_name: str):
    """Drop a table from the database.
    
    Args:
        table_name: Name of the table to drop
    """
    try:
        sql_statement = f"DROP TABLE IF EXISTS {table_name}"
        cursor.execute(sql_statement)
        connection.commit()
        logger.info(f"Table '{table_name}' dropped")
    except sqlite3.Error as e:
        logger.error(f"Error dropping table '{table_name}': {e}")
        raise


def query_table(table_name: str) -> list:
    """Query all records from a table.
    
    Args:
        table_name: Name of the table to query
        
    Returns:
        List of all records in the table
    """
    try:
        sql_statement = f"SELECT * FROM {table_name}"
        cursor.execute(sql_statement)
        results = cursor.fetchall()
        logger.debug(f"Retrieved {len(results)} records from table '{table_name}'")
        return results
    except sqlite3.Error as e:
        logger.error(f"Error querying table '{table_name}': {e}")
        raise


def is_city_fetched(city_name: str):
    """Check if a city has been fetched and stored in the database.
    
    Args:
        city_name: Name of the city to check
        
    Returns:
        True if the city exists in the database, False otherwise
    """
    try:
        sql_statement = "SELECT * FROM city WHERE name = ?"
        cursor.execute(sql_statement, (city_name,))
        result = len(cursor.fetchall()) > 0
        logger.debug(f"City '{city_name}' fetched status: {result}")
        return result
    except sqlite3.Error as e:
        logger.error(f"Error checking if city '{city_name}' is fetched: {e}")
        raise


def add_city_to_db(name: str):
    """Add a city to the database.
    
    Args:
        name: Name of the city to add
    """
    try:
        sql_statement = "INSERT INTO city (name) VALUES (?)"
        cursor.execute(sql_statement, (name,))
        connection.commit()
        logger.info(f"City '{name}' added to database")
    except sqlite3.IntegrityError as e:
        logger.warning(f"City '{name}' already exists in database: {e}")
    except sqlite3.Error as e:
        logger.error(f"Error adding city '{name}' to database: {e}")
        raise


def fetch_city_restaurants(city_name: str):
    """Fetch all restaurants for a specific city from the database.
    
    Args:
        city_name: Name of the city
        
    Returns:
        List of restaurant records for the city
    """
    try:
        sql_statement = "SELECT * FROM restaurant WHERE city = ?"
        cursor.execute(sql_statement, (city_name,))
        results = cursor.fetchall()
        logger.debug(f"Retrieved {len(results)} restaurants for city '{city_name}'")
        return results
    except sqlite3.Error as e:
        logger.error(f"Error fetching restaurants for city '{city_name}': {e}")
        raise


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



    

    
