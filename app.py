from flask import Flask, request, render_template, jsonify, redirect, url_for


import json
import os
from elasticsearch import Elasticsearch, ElasticsearchException
from configparser import ConfigParser

from flask_cors import CORS
import requests

import logging
logging.basicConfig(level=logging.DEBUG)
import os
from student_routes import student_bp

from user_routes import user_bp
from common import validate_session_token, validate_admin_token, validate_parent_token, validate_educator_token
from flask import Flask, request, jsonify
import PyPDF2
import io
import csv


app = Flask(__name__)

app.config['SESSION_COOKIE_DOMAIN'] = os.getenv('SESSION_COOKIE_DOMAIN', '.dlyog.com')
app.config['SESSION_COOKIE_PATH'] = os.getenv('SESSION_COOKIE_PATH', '/')
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'True') == 'True'
app.config['SESSION_COOKIE_HTTPONLY'] = os.getenv('SESSION_COOKIE_HTTPONLY', 'True') == 'True'
app.config['SESSION_COOKIE_SAMESITE'] = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
CORS(app)


app.register_blueprint(student_bp, url_prefix='/api')
app.register_blueprint(user_bp, url_prefix='/user_api')





# Read OS Environment Variables

# Read configuration
config = ConfigParser()
config.read('config.ini')
datasource = config.get('General', 'datasource')
es_url = config.get('ElasticSearch', 'url') if datasource == 'DB' else None
llm_provider = config.get('LLM', 'llm_provider')

gemini_pro_llm_url = config.get('LLM', 'gemni_url') + os.environ.get('GOOGLE_API_KEY', '')

def call_gemini_pro_llm_api(prompt):
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    response = requests.post(gemini_pro_llm_url, json=payload)
    if response.status_code == 200:
        response_data = response.json()
        return response_data['candidates'][0]['content']['parts'][0]['text'].replace("```json\n", "").replace("\n```", "")
    else:
        raise Exception(f"Failed to get response from LLM API: {response.text}")

if datasource == 'DB':
    es = Elasticsearch([es_url])


@app.route('/educator_view')
@validate_educator_token
def educator_view():
    return render_template('educator_view.html')

@app.route('/admin_view')
@validate_admin_token
def admin_view():
    return render_template('admin_view.html')

@app.route('/parent_view')
@validate_parent_token
def parent_view():
    return render_template('parent_view.html')

@app.route('/assessment')
@validate_educator_token
def index():
    return render_template('index_final.html')

@app.route('/iep_template')
@validate_educator_token
def iep_template():
    return render_template('iep_template.html')

@app.route('/ieps_view')
@validate_educator_token
def ieps_view():
    return render_template('ieps_view.html')

@app.route('/ieps_view_parent')
@validate_parent_token
def ieps_view_parent():
    return render_template('ieps_view_parent.html')

@app.route('/students')
@validate_admin_token
def student_template():
    return render_template('students.html')

@app.route('/users')
@validate_admin_token
def user_template():
    return render_template('users.html')

@app.route('/api/iep_questions', methods=['GET'])
@validate_educator_token
def get_iep_questions():
    with open('iep_template.json', 'r') as f:
        iep_data = json.load(f)
    return jsonify(iep_data)

@app.route('/', methods=['GET'])
def login():
    # Logic for rendering the login page
    return render_template('login.html')

@app.route('/home', methods=['GET'])
@validate_session_token
def home():
    user_role = request.cookies.get('user_role')

    # Redirect based on role
    if user_role == 'educator':
        return render_template('educator_view.html')
    elif user_role == 'parent':
        return render_template('parent_view.html')
    elif user_role == 'admin':
        return render_template('admin_view.html')
    else:
        return render_template('login.html')



@app.route('/get_iep_template', methods=['GET'])
@validate_educator_token
def get_iep_template():
    age = request.args.get('age')
    student_type = request.args.get('student_type')
    doc_id = f"{age}_{student_type}"

    if datasource == 'DB':
        try:
            res = es.get(index="iep_templates", id=doc_id)
            return jsonify(res['_source']), 200
        except Exception as e:
            # Log the exception for debugging
            print(f"Elasticsearch fetch failed: {e}")
            # Fallback to file-based fetch
            print("Falling back to file-based fetch.")

    # File-based fetch (used as fallback if DB fetch fails)
    file_path = f"iep_templates/{age}/{student_type}.json"
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
        return jsonify(data), 200
    else:
        return jsonify({"error": "File not found"}), 404



def save_to_db(age, student_type, updated_data):
    doc_id = f"{age}_{student_type}"
    try:
        es.index(index="iep_templates", id=doc_id, body=updated_data)
        return jsonify({"message": "Successfully updated in DB"}), 200
    except ElasticsearchException as e:
        return str(e), 500

def save_to_file(age, student_type, updated_data):
    file_path = f"iep_templates/{age}/{student_type}.json"
    if os.path.exists(file_path):
        with open(file_path, 'w') as f:
            json.dump(updated_data, f)
        return jsonify({"message": "Successfully updated in file"}), 200
    else:
        return jsonify({"error": "File not found"}), 404

@app.route('/save_iep_template', methods=['POST'])
@validate_educator_token
def save_iep_template():
    content = request.get_json()
    age = content['age']
    student_type = content['student_type']
    updated_data = content['data']

    if datasource == 'DB':
        try:
            return save_to_db(age, student_type, updated_data)
        except Exception as e:
            print(f"DB save failed: {e}")
            return jsonify({"error": "DB update failed, update not supported in file-based storage"}), 500
    else:
        return save_to_file(age, student_type, updated_data)

def convert_palm2_to_llama(palm2_response):
    # Extract the output from the first candidate
    output_text = palm2_response['candidates'][0]['output'].replace("```json\n", "").replace("\n```", "")
    
    # Create the llama JSON structure
    llama_structure = {
        "gpu_temperature": "NA",
        "response": output_text
    }
    
    return llama_structure


@app.route('/get_ai_answer', methods=['POST'])
@validate_educator_token
def get_ai_answer():
    try:
        #logging.basicConfig(level=logging.DEBUG)
        #logging.debug('111111')
        content = request.get_json()
        question = content['question']
        parentAnswer = content['parentAnswer']
        age = content['age']
        student_type = content['student_type']

        
        prompt_str = f"""
        As an AI expert in creating Individualized Education Plans for {age}-year-old students of type {student_type}, your task is to focus on a response from an IEP participant. The participant could be a Teacher, Speech Therapist, Occupational Therapist, Parent, or BCBA. 

        Here's the situation:
        - Question: {question}
        - Participant's Response: {parentAnswer if parentAnswer else 'No response given'}
        
        Please enhance the given response or create a simulated one if none is provided. Your response should:
        - Stick to proper English grammar and spelling.
        - Be generic and not include any student's name.
        - Strictly be an enhanced or simulated answer with no other details or commentary.
        - Exclude the original participant's response if one is provided.
        
        What would be your response in this scenario?
        
        Enhanced or Simulated Response:
        """

        response = {

            "response": call_gemini_pro_llm_api(prompt_str)
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/get_iep_assessment', methods=['POST'])
@validate_educator_token
def get_iep_assessment():
    try:
        #logging.basicConfig(level=logging.DEBUG)
        #logging.debug('111111')
        content = request.get_json()
        if not all(k in content for k in ("question", "parentAnswer")):
            return jsonify({"error": "Missing required fields"}), 400

        question = content['question']
    
        parentAnswer = content['parentAnswer']
        age = content['age']
        student_type = content['student_type']


        #logging.debug('111111')

        # Create the updated prompt string for IEP Assessment with only the score embedded in recommendation
        prompt_str = f"""
            You are an expert educator specialized in creating Individualized Education Plans or IEP for {age}-year-old students of type {student_type}. Provide a recommendation for an IEP Assessment based on the question and the IEP Participant's (Teacher, Speech Therapist,Occupation Therapist, Parent ) answer. Your recommendation should be a single, unbroken paragraph that strictly concludes with a score derived from the ParentAnswer. The score should be a single decimal number. No additional text should follow the score. Use the scoring criteria for internal reference only.

            - Level 1 - 80% respond by name, normal eye contact, they can sit on a chair for more than 5 mins, they can follow simple directions, get social skills and mix with others. Got good fine motor skills. Level kids can answer WH Question.

            - Level 2 - will have behavior issues, anger issues, take more calm down than a typical child, cannot say or understand complex sentences, Less academic skill than L1, Got social skill and mix with others. Got good fine motor skills. Level kids can answer WH Question. 

            - Level 3 -  Level 3 and Level 2 has a lot of gaps in cognitive skill and it's more visible. They cannot stand on line, they have hyper activity and behavior, less social skill than L2 and less intention to mix with others. Less fine motor skill than Level 2. Level cannot answer WH question and got echolalia 
 
            - Level 4 - Severe behavior issue. Need 1-1 attention for each kid in school. Less cognitive skill, fine motor skill, social skill than L3.  Level 4 is mostly nonverbal, zero social skill. Most non compliant or do not follow instructions at all.

            - Level 1: Score should be 0.8 to 1
            - Level 2: Score should be 0.6 to 0.79
            - Level 3: Score should be 0.3 to 0.59
            - Level 4: Score should be below 0.3

            Your recommendation must strictly end with Score= X.X, where X.X is a single decimal number. No text should follow the score.
           

            Question: Does the student have issues with social interactions?
            ParentAnswer: My child struggles with making friends and often prefers to play alone. They don't seem to understand social cues well.
'
            Recommendation: Based on the parent's observations it's evident that the student faces challenges in social interactions and lacks a good understanding of social cues. To close this gap and aim for progressing the student to the next level, the following actions are recommended for implementation in the coming school days: 

            1. Collaborate with a speech and language therapist to focus on social communication skills.
            2. Conduct behavioral observations in multiple social settings to pinpoint specific areas of difficulty.
            3. Introduce tailored interventions like Social Skills Training (SST) and Peer-Mediated Instruction and Intervention (PMII) based on assessment findings.

            These actions will be reviewed and updated regularly to ensure effectiveness and suitability for the student's evolving needs. 

            IEP Participant: {question}
            IEP Participant's Feedback: {parentAnswer}

            Please make sure to provide both score and SMART (Specific, Measurable,Achievable, Relevant and Time-bound) Goal in your response. Response should be formatted as: Score=$score SmartGoals
            

            """
        
        response = {

            "response": call_gemini_pro_llm_api(prompt_str)
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get_iep_services', methods=['POST'])
@validate_educator_token
def get_iep_services():
    try:
        #logging.basicConfig(level=logging.DEBUG)
        #logging.debug('111111')
        content = request.get_json()
        if not all(k in content for k in ("question", "parentAnswer")):
            return jsonify({"error": "Missing required fields"}), 400

        question = content['question']
    
        parentAnswer = content['parentAnswer']
        age = content['age']
        student_type = content['student_type']


        #logging.debug('111111')

        # Create the updated prompt string for IEP Assessment with only the score embedded in recommendation
        prompt_str = f"""
            You are an expert educator specialized in creating Individualized Education Plans or IEP for {age}-year-old students of type {student_type}. Provide a recommendation for an IEP Assessment based on the question and the IEP Participant's (Teacher, Speech Therapist,Occupation Therapist, Parent ) answer. Your recommendation should be a single, unbroken paragraph that strictly concludes with a score derived from the ParentAnswer. The score should be a single decimal number. No additional text should follow the score. Use the scoring criteria for internal reference only.

            - Level 1 - 80% respond by name, normal eye contact, they can sit on a chair for more than 5 mins, they can follow simple directions, get social skills and mix with others. Got good fine motor skills. Level kids can answer WH Question.

            - Level 2 - will have behavior issues, anger issues, take more calm down than a typical child, cannot say or understand complex sentences, Less academic skill than L1, Got social skill and mix with others. Got good fine motor skills. Level kids can answer WH Question. 

            - Level 3 -  Level 3 and Level 2 has a lot of gaps in cognitive skill and it's more visible. They cannot stand on line, they have hyper activity and behavior, less social skill than L2 and less intention to mix with others. Less fine motor skill than Level 2. Level cannot answer WH question and got echolalia 
 
            - Level 4 - Severe behavior issue. Need 1-1 attention for each kid in school. Less cognitive skill, fine motor skill, social skill than L3.  Level 4 is mostly nonverbal, zero social skill. Most non compliant or do not follow instructions at all.

            - Level 1: Score should be 0.8 to 1
            - Level 2: Score should be 0.6 to 0.79
            - Level 3: Score should be 0.3 to 0.59
            - Level 4: Score should be below 0.3

            Your recommendation must strictly end with Score= X.X, where X.X is a single decimal number. No text should follow the score.
           

            Question: Does the student have issues with social interactions?
            ParentAnswer: My child struggles with making friends and often prefers to play alone. They don't seem to understand social cues well.
'
            Recommendation: Based on the parent's observations it's evident that the student faces challenges in social interactions and lacks a good understanding of social cues. To close this gap and aim for progressing the student to the next level, the following actions are recommended for implementation in the coming school days: 

            1. Collaborate with a speech and language therapist to focus on social communication skills.
            2. Conduct behavioral observations in multiple social settings to pinpoint specific areas of difficulty.
            3. Introduce tailored interventions like Social Skills Training (SST) and Peer-Mediated Instruction and Intervention (PMII) based on assessment findings.

            These actions will be reviewed and updated regularly to ensure effectiveness and suitability for the student's evolving needs. 

            IEP Participant: {question}
            IEP Participant's Feedback: {parentAnswer}

            Please make sure to provide both score and Goals. Goals should be SMART (Specific, Measurable,Achievable, Relevant and Time-bound). Please also include recommended services to achieve the goals. For example if student needs minimal speech improvment you can suggest to include 30 min speech threapy every week for 6 months.  Response should be formatted as: Score=$score Goals: Recommended Services:
            

            """
        
        response = {

            "response": call_gemini_pro_llm_api(prompt_str)
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500



def build_formatted_parent_answers(content):
    formatted_parent_answers = ""
    token_count = 0
    token_limit = 4000  # Set the token limit

    for iep in content:
        if 'questions' in iep:
            for question in iep['questions']:
                # Split the answer into words and count them
                words = question['parentAnswer'].split()
                new_token_count = token_count + len(words)

                # Check if adding these words will exceed the token limit
                if new_token_count > token_limit:
                    return formatted_parent_answers

                # Append the answer and update the token count
                formatted_parent_answers += f"- {question['parentAnswer']} "
                token_count = new_token_count

    return formatted_parent_answers





@app.route('/summarize_iep_assessment', methods=['POST'])
@validate_session_token
def summarize_iep_assessment():
    try:
        content = request.get_json()
        globalIeps = content['ieps']
        formatted_parent_answers = build_formatted_parent_answers(globalIeps)
        llm_provider = content['llm_provider']

        focus_area = content['focus_area']

        #logging.debug('111111')

        # Create the updated prompt string for IEP Assessment with only the score embedded in recommendation
        prompt_str = f"""[INST]<<SYS>>
            You are an expert educator specialized in summarizing Individualized Education Plan (IEP) responses for students. Your task is to provide a concise summary of the IEP Participant's (Teacher, Speech Therapist, Occupation Therapist, Parent) answers, focusing on the main concerns, needs, and observations mentioned. Your summary should be a single, coherent paragraph that highlights the key themes across multiple responses.

            Please ensure that the summary is clear and concise, capturing the essence of the participant's perspectives without adding any recommendations or scores. The summary should provide a quick overview for educators to understand the overall needs and concerns of the student as expressed by the IEP participants.

            <<IEPParticipantAnswers>>
            {formatted_parent_answers}

            DO NOT include any other suggestion or note just provide summary as string.
            <</SYS>>[/INST]"""
        
        # Check if 'focus_area' is null or has no value
        if not content.get('focus_area'):
            # Use the default prompt for summarization
            prompt_str = f"""[INST]<<SYS>>
                You are an expert educator specialized in summarizing Individualized Education Plan (IEP) responses for students. Your task is to provide a concise summary of the IEP Participant's (Teacher, Speech Therapist, Occupation Therapist, Parent) answers, focusing on the main concerns, needs, and observations mentioned. Your summary should be a single, coherent paragraph that highlights the key themes across multiple responses.

                Please ensure that the summary is clear and concise, capturing the essence of the participant's perspectives without adding any recommendations or scores. The summary or key points should provide a quick overview for educators to understand the overall needs and concerns of the student as expressed by the IEP participants.

                <<IEPParticipantAnswers>>
                {formatted_parent_answers}

                DO NOT include any other suggestion or note, just provide summary as string.
                <</SYS>>[/INST]"""
        else:
            # Use a different prompt based on the provided 'focus_area'
            prompt_str = f"""[INST]<<SYS>>
                You are an expert educator specialized in responding to queries and summarizing Individualized Education Plan (IEP) responses for students, with a focus on the '{focus_area}' area. You can either provide a concise summary of the IEP Participant's (Teacher, Speech Therapist, Occupation Therapist, Parent) answers or respond to specific questions about the student's abilities and needs in the '{focus_area}' area.

                For summaries, focus on the main concerns, needs, and observations related to the '{focus_area}' area, creating a single, coherent paragraph that highlights key themes across multiple responses. For questions, provide clear and direct answers based on the provided IEP Participant answers.

                If there is insufficient information in the provided responses to accurately summarize or answer a question about the '{focus_area}' area, please indicate this clearly to the user.

                <<IEPParticipantAnswers>>
                {formatted_parent_answers}

                [UserQuery]
                {focus_area}

                DO NOT add any recommendations, scores, or information not present in the responses. Provide either a summary or answer to the query as appropriate.
                <</SYS>>[/INST]"""

        # Now you have 'prompt_str' containing the appropriate prompt based on the condition.


# formatted_parent_answers is a string that contains all parent answers formatted in a way that the LLM can process.


        response = {

            "response": call_gemini_pro_llm_api(prompt_str)
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500



from PyPDF2 import PdfReader

def extract_text_from_pdf(file_stream):
    pdf_reader = PdfReader(file_stream)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text


def extract_text_from_csv(file_stream):
    csv_reader = csv.reader(io.StringIO(file_stream.read().decode('utf-8')))
    text = ' '.join([' '.join(row) for row in csv_reader])
    return text

@app.route('/upload', methods=['POST'])
@validate_educator_token
def upload_file():
    file = request.files['file']
    if file:
        filename = file.filename.lower()
        text = ""
        if filename.endswith('.pdf'):
            text = extract_text_from_pdf(io.BytesIO(file.read()))
        elif filename.endswith('.txt'):
            text = file.stream.read().decode('utf-8')
        elif filename.endswith('.csv'):
            text = extract_text_from_csv(file.stream)
        else:
            # Return a custom message for unsupported file types
            return jsonify({'extractedText': f"{file.content_type} not supported"})
        
        # Limit to 2000 words
        words = text.split()
        if len(words) > 2000:
            text = ' '.join(words[:2000])
        
        return jsonify({'extractedText': text})
    return jsonify({'error': 'No file uploaded'}), 400

app.run(host='0.0.0.0', port=8892, debug=True, use_reloader=True)
