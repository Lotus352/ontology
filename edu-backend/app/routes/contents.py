from flask import Blueprint, jsonify, request
from app.utils import execute_query

# Tạo blueprint cho các route liên quan đến content
contents_bp = Blueprint('contents', __name__)

@contents_bp.route('/contents', methods=['GET'])
def get_subclass_entities():
    # Truy vấn để lấy toàn bộ các thực thể thuộc các class con của 'Nội dung môn học'
    query = """
    MATCH (parent:Resource {rdfs__label: "Nội dung môn học"})
    MATCH (subclass)-[:rdfs__subClassOf*]->(parent)
    MATCH (entity)-[:rdf__type]->(subclass)
    RETURN elementId(entity) AS entity_id, entity.rdfs__label AS entity_label, labels(entity) AS rdf__type, subclass.rdfs__label AS rdfs__label_parent
    """
    entities = execute_query(query, {})

    if not entities:
        return jsonify({'error': 'No entities found in the subclasses of Nội dung môn học.'}), 404

    # Định dạng kết quả trả về theo yêu cầu
    result = [
        {
            'elementId': entity['entity_id'],
            'rdfs__label': entity['entity_label'],
            'rdfs__label_parent': entity['rdfs__label_parent']
        } for entity in entities
    ]

    return jsonify({'entities': result}), 200


@contents_bp.route('/contents/add-content', methods=['POST'])
def add_subclass_entity():
    data = request.get_json()
    rdfs__label = data.get('rdfs__label')
    rdfs__label_parent = data.get('rdfs__label_parent')

    if not rdfs__label or not rdfs__label_parent:
        return jsonify({'error': 'Both rdfs__label and rdfs__label_parent are required.'}), 400

    # Tìm lớp cha dựa trên rdfs__label_parent
    parent_query = """
    MATCH (parent:Resource {rdfs__label: $rdfs__label_parent})
    RETURN parent
    """
    parent_params = {'rdfs__label_parent': rdfs__label_parent}
    parent_result = execute_query(parent_query, parent_params)

    if not parent_result:
        return jsonify({'error': f'Parent class with label {rdfs__label_parent} not found.'}), 404

    # Tạo thực thể mới thuộc lớp con của rdfs__label_parent
    create_entity_query = """
    MATCH (parent:Resource {rdfs__label: $rdfs__label_parent})
    CREATE (new_entity:Resource:owl__NamedIndividual {
        rdfs__label: $rdfs__label
    })-[:rdf__type]->(parent)
    RETURN elementId(new_entity) AS entity_id, new_entity.rdfs__label AS entity_label
    """
    create_entity_params = {
        'rdfs__label': rdfs__label,
        'rdfs__label_parent': rdfs__label_parent
    }
    new_entity = execute_query(create_entity_query, create_entity_params)

    if not new_entity:
        return jsonify({'error': 'Failed to create new subclass entity.'}), 500

    return jsonify({
        'message': 'New subclass entity created successfully!',
        'entity': {
            'elementId': new_entity[0]['entity_id'],
            'rdfs__label': new_entity[0]['entity_label'],
            'rdfs__label_parent': rdfs__label_parent
        }
    }), 201