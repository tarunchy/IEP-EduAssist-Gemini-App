from flask import Blueprint, request, jsonify
from elasticsearch import Elasticsearch
from configparser import ConfigParser
import uuid
import hashlib
from common import validate_session_token, validate_admin_token
from hash_utils import hash_password, check_password

config = ConfigParser()
config.read('config.ini')
es_url = config.get('ElasticSearch', 'url')
es = Elasticsearch([es_url])

user_bp = Blueprint('user_bp', __name__)
index_name = "users"
session_index_name = "session"

def ensure_index_exists():
    if not es.indices.exists(index=index_name):
        es.indices.create(index=index_name, ignore=400)

@user_bp.route('/add_user', methods=['POST'])
@validate_admin_token
def add_user():
    ensure_index_exists()
    user_data = request.json
    user_id = str(uuid.uuid4())
    password = user_data.get("password")

    hashed_password = hash_password(password)


    # Determine student_id based on role
    role = user_data.get("role")
    student_id = user_data.get("student_id", None) if role == "parent" else ("all" if role == "educator" else None)

    user_profile = {
        "username": user_data.get("username"),
        "password": hashed_password,
        "role": role,
        "status": "active",
        "userId": user_id,
        "student_id": student_id
    }

    es.index(index=index_name, id=user_id, body=user_profile)
    return jsonify({'message': 'User added successfully', 'userId': user_id}), 201

@user_bp.route('/update_user', methods=['POST'])
@validate_admin_token
def update_user():
    user_data = request.json
    user_id = user_data.get('userId')
    if not user_id:
        return jsonify({'error': 'Missing user ID'}), 400

    # Hash password if it's being updated
    if 'password' in user_data and user_data['password']:
        user_data['password'] = hash_password(user_data['password'])

    # Update student_id based on role
    role = user_data.get("role")
    if "student_id" not in user_data or role != "parent":
        user_data["student_id"] = "all" if role == "educator" else None

    es.index(index=index_name, id=user_id, body=user_data)
    return jsonify({'message': 'User updated successfully'}), 200



@user_bp.route('/terminate_user', methods=['POST'])
@validate_admin_token
def terminate_user():
    user_data = request.json
    user_id = user_data.get('userId')
    if not user_id:
        return jsonify({'error': 'Missing user ID'}), 400

    user_data['status'] = 'terminated'

    es.index(index=index_name, id=user_id, body=user_data)
    return jsonify({'message': 'User terminated successfully'}), 200

@user_bp.route('/get_user/<user_id>', methods=['GET'])
@validate_admin_token
def get_user(user_id):
    res = es.get(index=index_name, id=user_id, ignore=404)
    if res['found']:
        user = res['_source']
        user.pop('password', None)
        return jsonify(user), 200
    else:
        return jsonify({'error': 'User not found'}), 404

@user_bp.route('/get_users', methods=['GET'])
@validate_admin_token
def get_users():
    query = {
        "query": {
            "match_all": {}
        }
    }
    res = es.search(index=index_name, body=query, size=1000)
    users = [doc['_source'] for doc in res['hits']['hits']]
    for user in users:
        user.pop('password', None)
    return jsonify(users), 200


from flask import jsonify, request, make_response
import uuid
import hashlib

@user_bp.route('/authenticate', methods=['POST'])
def authenticate():
    credentials = request.json
    username = credentials.get("username")
    password = credentials.get("password")

    if not username or not password:
        return jsonify({'error': 'Missing username or password'}), 400

    # Query Elasticsearch for username
    query = {
        "query": {
            "term": {
                "username.keyword": {
                    "value": username
                }
            }
        }
    }

    res = es.search(index=index_name, body=query, size=1)
    if res['hits']['hits']:
        user_data = res['hits']['hits'][0]['_source']
        stored_password = user_data.get("password")
        student_id = user_data.get("student_id")

        # Use bcrypt to check the password
        if check_password(stored_password, password):
            session_token = str(uuid.uuid4())
            user_role = user_data.get("role")

            # Store session token, username, and role in Elasticsearch
            session_data = {
                "username": username,
                "session_token": session_token,
                "role": user_role,
                "student_id": student_id,

            }
            es.index(index=session_index_name, doc_type="_doc", body=session_data)

            # Return session token, role, and username
            return jsonify({'session_token': session_token, 'user_role': user_role, 'username': username,'student_id': student_id}), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
    else:
        return jsonify({'error': 'User not found'}), 404








@user_bp.route('/logout', methods=['GET'])
@validate_session_token
def logout():
    session_token = request.cookies.get('session_token')
    # Delete the session token from Elasticsearch
    es.delete_by_query(index=session_index_name, body={"query": {"term": {"session_token": session_token}}})

    # Clear the session token cookie
    response = make_response(jsonify({'message': 'Logged out successfully'}), 200)
    response.set_cookie('session_token', '', expires=0)
    return response



