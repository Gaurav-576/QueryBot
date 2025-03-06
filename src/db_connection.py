import streamlit as st
from sqlalchemy import create_engine, inspect, text

class DatabaseIntegrations:
    def __init__(self):
        self.db_uri = f"mysql+pymysql://{st.secrets['DATABASE']['DB_USER']}:{st.secrets['DATABASE']['DB_PASSWORD']}@{st.secrets['DATABASE']['DB_HOST']}:{st.secrets['DATABASE']['DB_PORT']}/{st.secrets['DATABASE']['DB_DATABASE']}?ssl_ca={st.secrets['DATABASE']['CA']}"
        
        self.db_engine = create_engine(self.db_uri)
        self.db_inspector = inspect(self.db_engine)
    
    def get_schema(self):
        db_schema = {}
        table_names = self.db_inspector.get_table_names()
        for table in table_names:
            columns = self.db_inspector.get_columns(table)
            db_schema[table] = [(col["name"], col["type"]) for col in columns]
        return db_schema            
    
    def set_database(self, user: str, password: str, host: str, port: str, database: str):
        self.db_uri=f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        self.db_engine = create_engine(self.db_uri)
        self.db_inspector = inspect(self.db_engine)

    def run_query(self, query: str):
        with self.db_engine.connect() as connection:
            result = connection.execute(text(query))
            return result.fetchall()