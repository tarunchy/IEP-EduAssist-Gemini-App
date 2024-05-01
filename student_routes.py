from flask import Blueprint, request, jsonify
from elasticsearch import Elasticsearch
from configparser import ConfigParser
import uuid
from datetime import datetime
from common import validate_session_token, validate_admin_token, validate_educator_token


config = ConfigParser()
config.read('config.ini')
es_url = config.get('ElasticSearch', 'url')

es = Elasticsearch([es_url])

student_bp = Blueprint('student_bp', __name__)
index_name = "students"

def ensure_index_exists():
    if not es.indices.exists(index=index_name):
        es.indices.create(index=index_name, ignore=400)

@student_bp.route('/add_student', methods=['POST'])
@validate_admin_token
def add_student():
    ensure_index_exists()
    student_data = request.json
    student_id = str(uuid.uuid4())

    student_profile = {
        "type": "profile",  # Identifier for student profiles
        "firstName": student_data.get("firstName"),
        "lastName": student_data.get("lastName"),
        "dob": student_data.get("dob"),
        "level": student_data.get("level"),
        "studentId": student_id
    }

    es.index(index=index_name, id=student_id, body=student_profile)
    return jsonify({'message': 'Student added successfully', 'studentId': student_id}), 201


@student_bp.route('/save_iep', methods=['POST'])
@validate_educator_token
def save_iep():
    ensure_index_exists()
    iep_data = request.json
    student_id = iep_data.get('studentId')
    if not student_id:
        return jsonify({'error': 'Missing student ID'}), 400

    # Generate a unique ID for the IEP and get the current date
    iep_id = str(uuid.uuid4())
    current_date = datetime.now().strftime("%Y-%m-%d")  # Format the date as YYYY-MM-DD

    # Step 1: Save the IEP with the current date
    iep_data.update({
        'type': "iep",  # Identifier for IEP data
        'iepId': iep_id,
        'iepDate': current_date  # Include the current date
    })
    es.index(index=index_name, id=f"{student_id}_iep_{iep_id}", body=iep_data)

    # Step 2: Update the Student Profile
    try:
        student_profile_res = es.get(index=index_name, id=student_id)
        if student_profile_res['found']:
            student_profile = student_profile_res['_source']
            student_profile['score'] = iep_data.get('assessmentScore')
            student_profile['level'] = iep_data.get('assessedLevel')
            es.index(index=index_name, id=student_id, body=student_profile)
    except Exception as e:
        return jsonify({'error': 'Failed to update student profile', 'details': str(e)}), 500

    return jsonify({'message': 'IEP saved successfully', 'iepId': iep_id}), 201




@student_bp.route('/student_ieps', methods=['POST'])
@validate_session_token
def student_ieps():
    ensure_index_exists()
    student_data = request.json
    student_id = student_data.get('studentId')
    if not student_id:
        return jsonify({'error': 'Missing student ID'}), 400

    query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"studentId": student_id}},
                    {"match": {"type": "iep"}}
                ]
            }
        }
    }
    res = es.search(index=index_name, body=query)
    ieps = [doc['_source'] for doc in res['hits']['hits']]
    return jsonify(ieps), 200




@student_bp.route('/update_student', methods=['POST'])
@validate_admin_token
def update_student():
    student_data = request.json
    student_id = student_data.get('studentId')
    if not student_id:
        return jsonify({'error': 'Missing student ID'}), 400

    es.index(index=index_name, id=student_id, body=student_data)
    return jsonify({'message': 'Student updated successfully'}), 200

@student_bp.route('/delete_student', methods=['POST'])
@validate_admin_token
def delete_student():
    student_data = request.json
    student_id = student_data.get('studentId')
    if not student_id:
        return jsonify({'error': 'Missing student ID'}), 400

    # Delete query to remove all documents associated with the student_id
    query = {
        "query": {
            "match": {
                "studentId": student_id
            }
        }
    }
    es.delete_by_query(index=index_name, body=query)
    return jsonify({'message': 'Student deleted successfully'}), 200

@student_bp.route('/get_students', methods=['GET'])
@validate_session_token
def get_students():
    query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"type": "profile"}}
                ]
            }
        }
    }
    res = es.search(index=index_name, body=query, size=1000)
    students = [doc['_source'] for doc in res['hits']['hits']]
    return jsonify(students), 200


# Add other routes as needed
@student_bp.route('/get_student/<student_id>', methods=['GET'])
@validate_session_token
def get_student(student_id):
    res = es.get(index=index_name, id=student_id, ignore=404)
    if res['found']:
        return jsonify(res['_source']), 200
    else:
        return jsonify({'error': 'Student not found'}), 404
