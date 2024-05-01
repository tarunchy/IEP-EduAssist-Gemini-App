from flask import jsonify, request
from functools import wraps
from elasticsearch import Elasticsearch
from configparser import ConfigParser
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


config = ConfigParser()
config.read('config.ini')
es_url = config.get('ElasticSearch', 'url')
es = Elasticsearch([es_url])

session_index_name = "session"

def validate_session_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = request.cookies.get('session_token')
        user_role = request.cookies.get('user_role')
        username = request.cookies.get('username')

        if not all([session_token, user_role, username]):
            return jsonify({'error': 'Session token, user role, or username is missing'}), 401

        # Check if the session token, user role, and username are valid
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"session_token.keyword": session_token}},
                        {"term": {"role.keyword": user_role}},
                        {"term": {"username.keyword": username}}
                    ]
                }
            }
        }
        res = es.search(index=session_index_name, body=query, size=1)
        if not res['hits']['hits']:
            return jsonify({'error': 'Invalid session token, role, or username'}), 401

        return f(*args, **kwargs)
    return decorated_function

def validate_admin_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = request.cookies.get('session_token')
        user_role = request.cookies.get('user_role')
        username = request.cookies.get('username')

        if not all([session_token, user_role, username]):
            return jsonify({'error': 'Session token, user role, or username is missing'}), 401

        # Check if the session token, user role, and username are valid
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"session_token.keyword": session_token}},
                        {"term": {"role.keyword": "admin"}},
                        {"term": {"username.keyword": username}}
                    ]
                }
            }
        }
        res = es.search(index=session_index_name, body=query, size=1)
        if not res['hits']['hits']:
            return jsonify({'error': 'Invalid session token, role, or username'}), 401

        return f(*args, **kwargs)
    return decorated_function

def validate_parent_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = request.cookies.get('session_token')
        user_role = request.cookies.get('user_role')
        username = request.cookies.get('username')

        if not all([session_token, user_role, username]):
            return jsonify({'error': 'Session token, user role, or username is missing'}), 401

        # Check if the session token, user role, and username are valid
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"session_token.keyword": session_token}},
                        {"term": {"role.keyword": "parent"}},
                        {"term": {"username.keyword": username}}
                    ]
                }
            }
        }
        res = es.search(index=session_index_name, body=query, size=1)
        if not res['hits']['hits']:
            return jsonify({'error': 'Invalid session token, role, or username'}), 401

        return f(*args, **kwargs)
    return decorated_function

def validate_educator_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = request.cookies.get('session_token')
        user_role = request.cookies.get('user_role')
        username = request.cookies.get('username')

        if not all([session_token, user_role, username]):
            return jsonify({'error': 'Session token, user role, or username is missing'}), 401

        # Check if the session token, user role, and username are valid
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"session_token.keyword": session_token}},
                        {"term": {"role.keyword": "educator"}},
                        {"term": {"username.keyword": username}}
                    ]
                }
            }
        }
        res = es.search(index=session_index_name, body=query, size=1)
        if not res['hits']['hits']:
            return jsonify({'error': 'Invalid session token, role, or username'}), 401

        return f(*args, **kwargs)
    return decorated_function