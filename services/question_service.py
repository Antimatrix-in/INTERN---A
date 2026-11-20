import json
from models import db, Question, Assessment

# Documented JSON Schema Specification for Question Bank:
# [
#   {
#     "question_text": "Required. String describing the question.",
#     "options": [
#       {"id": "A", "text": "Option text A"},
#       {"id": "B", "text": "Option text B"},
#       {"id": "C", "text": "Option text C"},
#       {"id": "D", "text": "Option text D"}
#     ],
#     "correct_option": "Required. Matches an option id (e.g. 'A')",
#     "explanation": "Optional string providing rationale.",
#     "points": 1.0,  // Float, defaults to 1.0
#     "difficulty": "EASY" | "MEDIUM" | "HARD", // Defaults to MEDIUM
#     "category": "String category name" // Defaults to General
#   }
# ]

def get_sample_json_template():
    """Returns a valid sample JSON schema document."""
    return [
        {
            "question_text": "What is the time complexity of searching for a key in a Python dictionary on average?",
            "options": [
                {"id": "A", "text": "O(1)"},
                {"id": "B", "text": "O(n)"},
                {"id": "C", "text": "O(log n)"},
                {"id": "D", "text": "O(n log n)"}
            ],
            "correct_option": "A",
            "explanation": "Python dictionaries use hash tables, giving average O(1) lookup time.",
            "points": 1.0,
            "difficulty": "EASY",
            "category": "Data Structures"
        },
        {
            "question_text": "In PostgreSQL, which transaction isolation level prevents phantom reads?",
            "options": [
                {"id": "A", "text": "Read Committed"},
                {"id": "B", "text": "Read Uncommitted"},
                {"id": "C", "text": "Repeatable Read / Serializable"},
                {"id": "D", "text": "Snapshot None"}
            ],
            "correct_option": "C",
            "explanation": "Serializable and Repeatable Read (in PostgreSQL implementation) eliminate phantom reads.",
            "points": 2.0,
            "difficulty": "HARD",
            "category": "Databases"
        }
    ]

def validate_question_dict(item, index=0):
    """Validates an individual question data dictionary."""
    errors = []
    
    question_text = item.get('question_text')
    if not question_text or not isinstance(question_text, str) or len(question_text.strip()) < 5:
        errors.append(f"Item #{index+1}: 'question_text' is required and must be at least 5 characters.")

    options = item.get('options')
    if not options or not isinstance(options, list) or len(options) < 2:
        errors.append(f"Item #{index+1}: 'options' must be a list containing at least 2 options.")
    else:
        option_ids = set()
        for opt_idx, opt in enumerate(options):
            if not isinstance(opt, dict):
                errors.append(f"Item #{index+1}, Option #{opt_idx+1}: Option must be an object with 'id' and 'text'.")
                continue
            opt_id = opt.get('id')
            opt_text = opt.get('text')
            if not opt_id or not isinstance(opt_id, str):
                errors.append(f"Item #{index+1}, Option #{opt_idx+1}: Missing or invalid 'id'.")
            elif opt_id in option_ids:
                errors.append(f"Item #{index+1}: Duplicate option id '{opt_id}'.")
            else:
                option_ids.add(opt_id)

            if not opt_text or not isinstance(opt_text, str) or not opt_text.strip():
                errors.append(f"Item #{index+1}, Option '{opt_id}': 'text' is required.")

    correct_option = item.get('correct_option')
    if not correct_option or not isinstance(correct_option, str):
        errors.append(f"Item #{index+1}: 'correct_option' is required.")
    elif options and isinstance(options, list):
        valid_ids = [opt.get('id') for opt in options if isinstance(opt, dict)]
        if correct_option not in valid_ids:
            errors.append(f"Item #{index+1}: 'correct_option' ('{correct_option}') does not match any option id ({valid_ids}).")

    difficulty = item.get('difficulty', 'MEDIUM').upper()
    if difficulty not in ['EASY', 'MEDIUM', 'HARD']:
        errors.append(f"Item #{index+1}: 'difficulty' must be EASY, MEDIUM, or HARD.")

    try:
        points = float(item.get('points', 1.0))
        if points <= 0:
            errors.append(f"Item #{index+1}: 'points' must be greater than 0.")
    except (ValueError, TypeError):
        errors.append(f"Item #{index+1}: 'points' must be a valid number.")

    return errors

def parse_and_validate_question_json(json_content_or_str):
    """
    Parses JSON data and returns (valid_questions, errors).
    """
    if isinstance(json_content_or_str, (bytes, bytearray)):
        json_content_or_str = json_content_or_str.decode('utf-8')

    try:
        data = json.loads(json_content_or_str)
    except Exception as e:
        return None, [f"Invalid JSON format: {str(e)}"]

    if not isinstance(data, list):
        # Allow single question object as a 1-item list
        if isinstance(data, dict):
            data = [data]
        else:
            return None, ["Root element must be a JSON array of question objects."]

    if len(data) == 0:
        return None, ["JSON array contains no questions."]

    all_errors = []
    sanitized_questions = []

    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            all_errors.append(f"Item #{idx+1} is not a valid JSON object.")
            continue
        errors = validate_question_dict(item, idx)
        if errors:
            all_errors.extend(errors)
        else:
            sanitized_questions.append({
                'question_text': item['question_text'].strip(),
                'options': item['options'],
                'correct_option': str(item['correct_option']).strip(),
                'explanation': item.get('explanation', '').strip(),
                'points': float(item.get('points', 1.0)),
                'difficulty': item.get('difficulty', 'MEDIUM').upper(),
                'category': item.get('category', 'General').strip()
            })

    if all_errors:
        return None, all_errors

    return sanitized_questions, None

def save_imported_questions(questions_list, assessment_id=None):
    """
    Persists reviewed and validated questions to the database.
    """
    if assessment_id:
        assessment = db.session.get(Assessment, assessment_id)
        if not assessment:
            return 0, "Selected assessment does not exist."

    created_questions = []
    try:
        for q_data in questions_list:
            q = Question(
                assessment_id=assessment_id,
                question_text=q_data['question_text'],
                question_type='MCQ',
                options=q_data['options'],
                correct_option=q_data['correct_option'],
                explanation=q_data.get('explanation', ''),
                points=q_data.get('points', 1.0),
                difficulty=q_data.get('difficulty', 'MEDIUM'),
                category=q_data.get('category', 'General'),
                is_active=True
            )
            db.session.add(q)
            created_questions.append(q)

        db.session.commit()
        return len(created_questions), None
    except Exception as e:
        db.session.rollback()
        return 0, f"Error saving questions: {str(e)}"

def get_questions_query(assessment_id=None, category=None, difficulty=None, search=None):
    """Builds filtered query for questions."""
    query = Question.query
    if assessment_id:
        query = query.filter_by(assessment_id=assessment_id)
    if category:
        query = query.filter_by(category=category)
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    if search:
        query = query.filter(Question.question_text.ilike(f"%{search.strip()}%"))
    return query.order_by(Question.created_at.desc())
