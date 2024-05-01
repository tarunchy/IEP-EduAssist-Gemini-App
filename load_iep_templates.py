from elasticsearch import Elasticsearch
import json
import os
from configparser import ConfigParser

def upload_to_elasticsearch():
    # Read Elasticsearch URL from config.ini
    config = ConfigParser()
    config.read('config.ini')
    es_url = config.get('ElasticSearch', 'url')
    
    es = Elasticsearch([es_url])
    index_name = "iep_templates"

    for age in os.listdir("iep_templates"):
        for student_type in ["special_need", "typical"]:
            file_path = f"iep_templates/{age}/{student_type}.json"
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Assign a unique id for each document
                doc_id = f"{age}_{student_type}"

                # Index the document
                es.index(index=index_name, id=doc_id, body=data)

if __name__ == "__main__":
    upload_to_elasticsearch()
