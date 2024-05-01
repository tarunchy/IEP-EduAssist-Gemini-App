import sys
import uuid
import hashlib
from elasticsearch import Elasticsearch
from configparser import ConfigParser
from hash_utils import hash_password

def add_admin_user(es, index_name, username, password):
    # Generate a unique user ID
    user_id = str(uuid.uuid4())

    # Hash the password
    hashed_password = hash_password(password)

    # Check for existing users with the same username
    query = {
        "query": {
            "term": {
                "username.keyword": {
                    "value": username
                }
            }
        }
    }
    res = es.search(index=index_name, body=query)
    user_exists = res['hits']['total']['value'] > 0

    # If a user exists, update the latest one and delete the others
    if user_exists:
        # Assuming the first hit is the latest one
        latest_user_id = res['hits']['hits'][0]['_id']
        for hit in res['hits']['hits']:
            if hit['_id'] != latest_user_id:
                es.delete(index=index_name, id=hit['_id'])

        # Update the latest user with new details
        es.update(index=index_name, id=latest_user_id, body={"doc": {"password": hashed_password}})
        print(f"Updated existing user: {username}")
    else:
        # Create new user
        user_profile = {
            "username": username,
            "password": hashed_password,
            "role": "admin",
            "status": "active",
            "userId": user_id
        }
        es.index(index=index_name, id=user_id, body=user_profile)
        print("User added successfully")

if __name__ == "__main__":
    config = ConfigParser()
    config.read('config.ini')
    es_url = config.get('ElasticSearch', 'url')
    es = Elasticsearch([es_url])
    index_name = "users"

    if len(sys.argv) != 3:
        print("Usage: python add_admin.py <username> <password>")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    add_admin_user(es, index_name, username, password)
