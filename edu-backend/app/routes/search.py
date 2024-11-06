from flask import Blueprint, jsonify, request
from app.utils import execute_query
import re
from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F

# Create a blueprint for search routes
search_bp = Blueprint('search', __name__)

# Bảng từ điển để chuyển đổi viết tắt thành dạng đầy đủ
abbreviation_dict = {
    "PBL": "Project Based Learning",
    "ATTT": "An toàn thông tin",
    "HTTT": "Hệ thống thông tin",
    "CNPM": "Công nghệ phần mềm"
}

# Hàm để mở rộng các từ viết tắt trong văn bản
def expand_abbreviations(text, abbreviation_dict):
    words = text.split()
    expanded_words = [abbreviation_dict.get(word.upper(), word) for word in words]
    return " ".join(expanded_words)

# Hàm tiền xử lý văn bản để mở rộng các từ viết tắt và chuẩn hóa văn bản
def preprocess_text(text):
    text = text.lower()  # Chuyển thành chữ thường
    text = re.sub(r'[^\w\s]', '', text)  # Loại bỏ dấu câu
    return expand_abbreviations(text, abbreviation_dict)  # Mở rộng từ viết tắt

# Khởi tạo PhoBERT để xử lý ngôn ngữ tự nhiên
tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base-v2")
model = AutoModel.from_pretrained("vinai/phobert-base-v2")

# Hàm Mean Pooling để lấy embedding của câu
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output.last_hidden_state  # (batch_size, sequence_length, hidden_size)
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

# Hàm mã hóa câu thành embeddings sử dụng PhoBERT
def encode_sentence(sentence):
    sentence = preprocess_text(sentence)  # Chuyển đổi viết tắt trước khi mã hóa
    inputs = tokenizer(sentence, return_tensors='pt', truncation=True, max_length=128, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
    return mean_pooling(outputs, inputs['attention_mask'])

# Định nghĩa route API cho tìm kiếm
@search_bp.route('/search', methods=['POST'])
def search():
    try:
        # Nhận từ khóa tìm kiếm từ request
        data = request.get_json()
        search_query = data.get('query', '')

        # Truy vấn lấy thông tin các môn học và các quan hệ ngữ nghĩa bổ sung bao gồm rdf__type
        query = """
          MATCH (ancestor:Resource {rdfs__label: 'Môn học'})
          MATCH (n:Resource)-[:rdfs__subClassOf*]->(ancestor)
          MATCH (instance:Resource)-[:rdf__type]->(n)
          OPTIONAL MATCH (instance)-[:ns0__coNoiDung|:ns0__songHanh|:ns0__noiDungCua|:ns0__tienQuyet|:ns0__hocTruoc|:ns0__thuocChuyenNganh]->(relatedInstance)
          RETURN DISTINCT instance.ns0__maMonHoc AS code, instance.rdfs__label AS courseName, elementId(instance) AS elementId,
                          collect(DISTINCT relatedInstance) AS relatedInstances, n.rdfs__label AS rdf_type
        """

        # Chạy truy vấn và lấy kết quả thông qua API
        results = execute_query(query)

        # Mã hóa các tên môn học thành embeddings
        course_embeddings = []
        for result in results:
            course_name = result['courseName']
            expanded_course_name = preprocess_text(course_name)  # Chuyển đổi viết tắt thành dạng đầy đủ
            embedding = encode_sentence(expanded_course_name)
            course_embeddings.append((result, embedding))

        # Mã hóa từ khóa tìm kiếm thành embedding
        expanded_search_query = preprocess_text(search_query)  # Chuyển đổi viết tắt thành dạng đầy đủ
        search_embedding = encode_sentence(expanded_search_query).squeeze(0)

        # Tính toán độ tương đồng cosine giữa từ khóa tìm kiếm và các tên môn học
        similar_results = []
        for result, embedding in course_embeddings:
            embedding = embedding.squeeze(0)
            similarity = F.cosine_similarity(search_embedding, embedding, dim=0).item()
            result['similarity'] = similarity
            similar_results.append(result)

        # Sắp xếp kết quả theo độ tương đồng giảm dần và lấy top 10 kết quả
        sorted_filtered_results = sorted(similar_results, key=lambda x: x['similarity'], reverse=True)[:10]

        # Trả về kết quả dưới dạng JSON, bao gồm cả elementId và courseName
        response = [{
            'elementId': result['elementId'],
            'rdfs__label': result['courseName'],
            'rdf_type': result['rdf_type'],
            'similarity': result['similarity']
        } for result in sorted_filtered_results]

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
