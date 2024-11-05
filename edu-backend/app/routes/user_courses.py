# app/routes/user_courses.py
from flask import Blueprint, jsonify, request
from app.utils import execute_query

# Utility functions
def check_existing_user_course(user_id, course_id):
    query = """
    MATCH (uc:UserCourse) WHERE uc.user_id = $user_id AND uc.course_id = $course_id
    RETURN uc
    """
    params = {
        'user_id': user_id,
        'course_id': course_id
    }
    return execute_query(query, params)

def check_prerequisite_completion(user_id, course_id):
    query = """
    MATCH (courseA)<-[:ns0__tienQuyet]-(courseB)
    MATCH (uc:UserCourse {user_id: $user_id, course_id: elementId(courseA)})
    WHERE elementId(courseB) = $course_id AND uc.status <> 'hoàn thành'
    RETURN uc
    """
    params = {
        'user_id': user_id,
        'course_id': course_id
    }
    return execute_query(query, params)

def create_user_course(data):
    query = """
    CREATE (uc:UserCourse {
        user_id: $user_id,
        course_id: $course_id,
        status: $status
    })
    RETURN elementId(uc) AS user_course_id, uc
    """
    params = {
        'user_id': data.get('user_id'),
        'course_id': data.get('course_id'),
        'status': data.get('status')
    }
    return execute_query(query, params)

def update_user_course(user_course_id, data):
    query = """
    MATCH (uc:UserCourse) WHERE elementId(uc) = $user_course_id
    SET uc.status = coalesce($status, uc.status)
    RETURN elementId(uc) AS user_course_id, uc
    """
    params = {
        'user_course_id': user_course_id,
        'status': data.get('status')
    }
    return execute_query(query, params)

# Blueprint setup
user_courses_bp = Blueprint('user_courses', __name__)

# Route functions
@user_courses_bp.route('/user-courses', methods=['POST'])
def add_user_course():
    data = request.get_json()
    user_id = data.get('user_id')
    course_id = data.get('course_id')

    existing_user_course = check_existing_user_course(user_id, course_id)
    if existing_user_course:
        return jsonify({'error': f'UserCourse with user_id {user_id} and course_id {course_id} already exists.'}), 400

    prerequisite_incomplete = check_prerequisite_completion(user_id, course_id)
    if prerequisite_incomplete:
        return jsonify({'error': 'Cannot add UserCourse: prerequisite course is not completed.'}), 400
    
    user_course = create_user_course(data)
    if not user_course:
        return jsonify({'error': 'Failed to create UserCourse.'}), 500

    user_course_data = {
        'user_course_id': user_course[0]['user_course_id'],
        'user_id': user_course[0]['uc']['user_id'],
        'course_id': user_course[0]['uc']['course_id'],
        'status': user_course[0]['uc']['status']
    }

    return jsonify({'message': 'UserCourse added successfully!', 'user_course': user_course_data}), 201

@user_courses_bp.route('/user-courses/<user_course_id>', methods=['PUT'])
def update_user_course_by_id(user_course_id):
    data = request.get_json()
    status = data.get('status')

    # Check for prerequisite completion if updating to 'hoàn thành'
    if status == 'hoàn thành':
        user_course_query = """
        MATCH (uc:UserCourse) WHERE elementId(uc) = $user_course_id
        RETURN uc.user_id AS user_id, uc.course_id AS course_id
        """
        user_course_params = {'user_course_id': user_course_id}
        user_course_result = execute_query(user_course_query, user_course_params)
        if not user_course_result:
            return jsonify({'error': f'UserCourse with id {user_course_id} not found.'}), 404

        user_id = user_course_result[0]['user_id']
        course_id = user_course_result[0]['course_id']

        prerequisite_incomplete = check_prerequisite_completion(user_id, course_id)
        if prerequisite_incomplete:
            return jsonify({'error': 'Cannot mark as hoàn thành: prerequisite course is not completed.'}), 400

    updated_user_course = update_user_course(user_course_id, data)
    if not updated_user_course:
        return jsonify({'error': 'Failed to update UserCourse.'}), 500

    user_course_data = {
        'user_course_id': updated_user_course[0]['user_course_id'],
        'user_id': updated_user_course[0]['uc']['user_id'],
        'course_id': updated_user_course[0]['uc']['course_id'],
        'status': updated_user_course[0]['uc']['status']
    }

    return jsonify({'message': 'UserCourse updated successfully!', 'user_course': user_course_data}), 200

@user_courses_bp.route('/user-courses/<user_course_id>', methods=['GET'])
def get_user_course_by_id(user_course_id):
    query = """
    MATCH (uc:UserCourse) WHERE elementId(uc) = $user_course_id
    RETURN elementId(uc) AS user_course_id, uc.user_id AS user_id, uc.course_id AS course_id, uc.status AS status
    """
    params = {'user_course_id': user_course_id}
    result = execute_query(query, params)
    user_course = result[0] if result else None

    if not user_course:
        return jsonify({'error': f'UserCourse with id {user_course_id} not found.'}), 404

    return jsonify(user_course), 200

@user_courses_bp.route('/user-courses', methods=['GET'])
def get_all_user_courses():
    query = """
    MATCH (uc:UserCourse)
    RETURN elementId(uc) AS user_course_id, uc.user_id AS user_id, uc.course_id AS course_id, uc.status AS status
    """
    result = execute_query(query, {})
    user_courses = [
        {
            'user_course_id': uc['user_course_id'],
            'user_id': uc['user_id'],
            'course_id': uc['course_id'],
            'status': uc['status']
        } for uc in result
    ]

    return jsonify(user_courses), 200

@user_courses_bp.route('/user-courses/<user_course_id>', methods=['DELETE'])
def delete_user_course(user_course_id):
    query = """
    MATCH (uc:UserCourse) WHERE elementId(uc) = $user_course_id
    DELETE uc
    """
    params = {'user_course_id': user_course_id}
    execute_query(query, params)

    return jsonify({'message': f'UserCourse with id {user_course_id} deleted successfully.'}), 200

