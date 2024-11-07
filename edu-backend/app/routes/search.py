from flask import Blueprint, jsonify, request 
from app.utils import execute_query
import re
from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F

search_bp = Blueprint('search', __name__)

abbreviation_dict = {
    "PBL": "Project Based Learning",
    "ATTT": "An toàn thông tin",
    "HTTT": "Hệ thống thông tin",
    "CNPM": "Công nghệ phần mềm"
}

def expand_abbreviations(text, abbreviation_dict):
    words = text.split()
    expanded_words = [abbreviation_dict.get(word.upper(), word) for word in words]
    return " ".join(expanded_words)

def preprocess_text(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    return expand_abbreviations(text, abbreviation_dict)

tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base-v2")
model = AutoModel.from_pretrained("vinai/phobert-base-v2")

def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output.last_hidden_state
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

def encode_sentence(sentence):
    sentence = preprocess_text(sentence)
    inputs = tokenizer(sentence, return_tensors='pt', truncation=True, max_length=128, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
    return mean_pooling(outputs, inputs['attention_mask'])

@search_bp.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        search_query = data.get('query', '')

        query = """
          MATCH (ancestor:Resource {rdfs__label: 'Môn học'})
          MATCH (n:Resource)-[:rdfs__subClassOf*]->(ancestor)
          MATCH (instance:Resource)-[:rdf__type]->(n)
          OPTIONAL MATCH (instance)-[:ns0__coNoiDung|:ns0__songHanh|:ns0__noiDungCua|:ns0__tienQuyet|:ns0__hocTruoc|:ns0__thuocChuyenNganh]->(relatedInstance)
          RETURN DISTINCT instance.ns0__maMonHoc AS code, instance.rdfs__label AS courseName, elementId(instance) AS elementId,
                          collect(DISTINCT relatedInstance) AS relatedInstances, n.rdfs__label AS rdf_type
        """

        results = execute_query(query)

        course_embeddings = []
        for result in results:
            course_name = result['courseName']
            expanded_course_name = preprocess_text(course_name)
            embedding = encode_sentence(expanded_course_name)
            course_embeddings.append((result, embedding))

        expanded_search_query = preprocess_text(search_query)
        search_embedding = encode_sentence(expanded_search_query).squeeze(0)

        similar_results = []
        for result, embedding in course_embeddings:
            embedding = embedding.squeeze(0)
            similarity = F.cosine_similarity(search_embedding, embedding, dim=0).item()
            result['similarity'] = similarity
            similar_results.append(result)

        sorted_filtered_results = sorted(similar_results, key=lambda x: x['similarity'], reverse=True)[:10]

        response = [{
            'elementId': result['elementId'],
            'rdfs__label': result['courseName'],
            'rdf_type': result['rdf_type'],
            'similarity': result['similarity']
        } for result in sorted_filtered_results]

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
