# app/routes/contents.py
from flask import Blueprint, jsonify
from app.utils import execute_query

# Create a blueprint for content routes
contents_bp = Blueprint('contents', __name__)

@contents_bp.route('/contents', methods=['GET'])
def get_all_subject_contents():
    # Cypher query to get all 'Nội dung môn học' and its subclasses
    query = """
    MATCH (content:Resource:owl__Class)-[:rdfs__subClassOf*]->(parent:Resource {rdfs__label: 'Nội dung môn học'})
    RETURN elementId(content) AS content_id, content.rdfs__label AS content_label, content.uri AS content_uri
    """
    try:
        # Execute the query
        contents = execute_query(query, {})
        
        # If no content found, return an empty list
        if not contents:
            return jsonify({'contents': []}), 200
        
        # Structure the response
        result = [
            {
                'elementId': content['content_id'],
                'rdfs__label': content['content_label'],
            } for content in contents
        ]
        
        return jsonify({'contents': result}), 200
    
    except Exception as e:
        # Handle any errors that occur
        return jsonify({'error': str(e)}), 500
