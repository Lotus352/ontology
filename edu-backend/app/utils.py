from neo4j import GraphDatabase
from app.config import Config

db_uri = Config.NEO4J_URI
db_user = Config.NEO4J_USER
db_password = Config.NEO4J_PASSWORD
driver = GraphDatabase.driver(db_uri, auth=(db_user, db_password))
session_config = {'database': Config.NEO4J_DATABASE}

def execute_query(query, params=None):
    with driver.session(**session_config) as session:
        result = session.run(query, params)
        return [record.data() for record in result]