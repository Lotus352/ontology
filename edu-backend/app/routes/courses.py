# app/routes/courses.py
from flask import Blueprint, jsonify, request
from app.utils import execute_query

def check_existing_course(course_id):
    query = """
    MATCH (course) WHERE elementId(course) = $course_id
    RETURN course
    """
    params = {'course_id': course_id}
    return execute_query(query, params)

def check_existing_target(target_id):
    query = """
    MATCH (target) WHERE elementId(target) = $target_id
    RETURN target
    """
    params = {'target_id': target_id}
    return execute_query(query, params)

def check_existing_relation(course_id, target_id, relation_type):
    query = """
    MATCH (course) WHERE elementId(course) = $course_id
    MATCH (target) WHERE elementId(target) = $target_id
    OPTIONAL MATCH (course)-[rel:`""" + relation_type + """`]->(target)
    RETURN rel
    """
    params = {
        'course_id': course_id,
        'target_id': target_id
    }
    return execute_query(query, params)

def create_course(data):
    query = """
    CREATE (course:Resource:owl__NamedIndividual {
        ns0__hocKy: $ns0__hocKy,
        ns0__laMonTuChon: coalesce($ns0__laMonTuChon, false),
        ns0__maMonHoc: $ns0__maMonHoc,
        ns0__soTinChi: $ns0__soTinChi,
        rdfs__label: $rdfs__label
    })
    RETURN elementId(course) AS course_id, course
    """
    params = {
        'ns0__hocKy': data.get('ns0__hocKy'),
        'ns0__laMonTuChon': data.get('ns0__laMonTuChon'),
        'ns0__maMonHoc': data.get('ns0__maMonHoc'),
        'ns0__soTinChi': data.get('ns0__soTinChi'),
        'rdfs__label': data.get('rdfs__label')
    }
    return execute_query(query, params)

def create_relation(course_id, relation):
    query = """
    MATCH (course) WHERE elementId(course) = $course_id
    MATCH (target) WHERE elementId(target) = $target_id
    CREATE (course)-[:`""" + relation['relation_type'] + """`]->(target)
    """
    params = {
        'course_id': course_id,
        'target_id': relation['target_id']
    }
    execute_query(query, params)

def update_course(course_id, data):
    query = """
    MATCH (course) WHERE elementId(course) = $course_id
    SET course.ns0__hocKy = coalesce($ns0__hocKy, course.ns0__hocKy),
        course.ns0__laMonTuChon = coalesce($ns0__laMonTuChon, course.ns0__laMonTuChon),
        course.ns0__soTinChi = coalesce($ns0__soTinChi, course.ns0__soTinChi),
        course.rdfs__label = coalesce($rdfs__label, course.rdfs__label)
    RETURN elementId(course) AS course_id, course
    """
    params = {
        'course_id': course_id,
        'ns0__hocKy': data.get('ns0__hocKy'),
        'ns0__laMonTuChon': data.get('ns0__laMonTuChon'),
        'ns0__soTinChi': data.get('ns0__soTinChi'),
        'rdfs__label': data.get('rdfs__label')
    }
    return execute_query(query, params)

def update_relation(relation_id, relation_type, target_id):
    query = """
    MATCH ()-[rel]->(target) WHERE elementId(rel) = $relation_id AND elementId(target) = $target_id
    SET rel.relation_type = $relation_type
    RETURN elementId(rel) AS relation_id, type(rel) AS relation_type, elementId(target) AS target_id
    """
    params = {
        'relation_id': relation_id,
        'relation_type': relation_type,
        'target_id': target_id
    }
    return execute_query(query, params)

courses_bp = Blueprint('courses', __name__)

@courses_bp.route('/courses', methods=['POST'])
def add_course():
    data = request.get_json()
    ns0__maMonHoc = data.get('ns0__maMonHoc')

    existing_course = check_existing_course(ns0__maMonHoc)
    if existing_course:
        return jsonify({'error': f'Course with code {ns0__maMonHoc} already exists.'}), 400

    course = create_course(data)
    if not course:
        return jsonify({'error': 'Failed to create course.'}), 500

    course_data = {
        'course_id': course[0]['course_id'],
        'ns0__hocKy': course[0]['course']['ns0__hocKy'],
        'ns0__laMonTuChon': course[0]['course']['ns0__laMonTuChon'],
        'ns0__maMonHoc': course[0]['course']['ns0__maMonHoc'],
        'ns0__soTinChi': course[0]['course']['ns0__soTinChi'],
        'rdfs__label': course[0]['course']['rdfs__label']
    }

    return jsonify({'message': 'Course added successfully!', 'course': course_data}), 201

@courses_bp.route('/courses/<course_id>/relations', methods=['POST'])
def add_course_relations(course_id):
    data = request.get_json()
    relations = data.get('relations', [])
    
    for relation in relations:
        relation_type = relation.get('relation_type')
        target_id = relation.get('target_id')
        if relation_type and target_id:
            existing_target = check_existing_target(target_id)
            if not existing_target:
                return jsonify({'error': f'Target with id {target_id} does not exist.'}), 400

            existing_relation = check_existing_relation(course_id, target_id, relation_type)
            if existing_relation and existing_relation[0]['rel']:
                return jsonify({'error': f'Relation {relation_type} between course {course_id} and target {target_id} already exists.'}), 400

            create_relation(course_id, relation)
    return jsonify({'message': 'Relations added successfully!'}), 201

@courses_bp.route('/courses', methods=['GET'])
def get_courses():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    filter_relation = request.args.get('relation', None)
    
    query = """
    MATCH (ancestor:Resource {rdfs__label: 'Môn học'})
    MATCH (n:Resource)-[:rdfs__subClassOf*]->(ancestor)
    MATCH (instance:Resource)-[:rdf__type]->(n)
    OPTIONAL MATCH (instance)-[rel]->(related)
    WITH instance, collect({relation_id: elementId(rel), relation_type: type(rel), target_id: elementId(related), rdfs__label: related.rdfs__label}) AS all_relations
    WHERE ($filter_relation IS NULL OR all(r IN $filter_relation WHERE any(rel IN all_relations WHERE rel.relation_type = r)))
    RETURN DISTINCT elementId(instance) AS course_id, instance.ns0__hocKy AS ns0__hocKy, instance.ns0__laMonTuChon AS ns0__laMonTuChon, instance.ns0__maMonHoc AS ns0__maMonHoc, instance.ns0__soTinChi AS ns0__soTinChi, instance.rdfs__label AS rdfs__label, [rel IN all_relations WHERE rel.rdfs__label IS NOT NULL] AS relations
    SKIP $skip
    LIMIT $limit
    """
    params = {
        'filter_relation': filter_relation.split(',') if filter_relation else None,
        'skip': (page - 1) * limit,
        'limit': limit
    }
    courses = execute_query(query, params)
    return jsonify(courses)

@courses_bp.route('/courses/<course_id>', methods=['GET'])
def get_course_by_code(course_id):
    query = """
    MATCH (course) WHERE elementId(course) = $course_id
    OPTIONAL MATCH (course)-[rel]->(related)
    WITH course, collect({relation_id: elementId(rel), relation_type: type(rel), target_id: elementId(related), rdfs__label: related.rdfs__label}) AS relations
    RETURN elementId(course) AS course_id, course.ns0__hocKy AS ns0__hocKy, course.ns0__laMonTuChon AS ns0__laMonTuChon, course.ns0__maMonHoc AS ns0__maMonHoc, course.ns0__soTinChi AS ns0__soTinChi, course.rdfs__label AS rdfs__label, [rel IN relations WHERE rel.rdfs__label IS NOT NULL] AS relations
    """
    params = {'course_id': course_id}
    result = execute_query(query, params)
    course = result[0] if result else None

    if not course:
        return jsonify({'error': f'Course with id {course_id} not found.'}), 404

    return jsonify(course)

@courses_bp.route('/courses/<course_id>', methods=['PUT'])
def update_course_by_code(course_id):
    data = request.get_json()
    
    existing_course = check_existing_course(course_id)
    if not existing_course:
        return jsonify({'error': f'Course with id {course_id} does not exist.'}), 404

    updated_course = update_course(course_id, data)
    if not updated_course:
        return jsonify({'error': 'Failed to update course.'}), 500

    updated_course_data = {
        'course_id': updated_course[0]['course_id'],
        'ns0__hocKy': updated_course[0]['course']['ns0__hocKy'],
        'ns0__laMonTuChon': updated_course[0]['course']['ns0__laMonTuChon'],
        'ns0__maMonHoc': updated_course[0]['course']['ns0__maMonHoc'],
        'ns0__soTinChi': updated_course[0]['course']['ns0__soTinChi'],
        'rdfs__label': updated_course[0]['course']['rdfs__label']
    }

    return jsonify({'message': 'Course updated successfully!', 'course': updated_course_data}), 200
