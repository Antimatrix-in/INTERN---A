import json
from models import db, Question, CodingQuestion, Assessment

# Approved Category Specifications
CATEGORY_CONFIG = {
    'coding': {
        'name': 'Coding',
        'section': 'CODING',
        'target_questions': 4,
        'marks_per_question': 15.0,
        'total_marks': 60.0,
        'template_filename': 'coding_questions_template.json'
    },
    'aptitude': {
        'name': 'Aptitude',
        'section': 'APTITUDE',
        'target_questions': 10,
        'marks_per_question': 2.0,
        'total_marks': 20.0,
        'template_filename': 'aptitude_questions_template.json'
    },
    'mcq': {
        'name': 'Technical MCQ',
        'section': 'MCQ',
        'target_questions': 20,
        'marks_per_question': 1.0,
        'total_marks': 20.0,
        'template_filename': 'mcq_questions_template.json'
    }
}

# -------------------------------------------------------------
# Template Generators
# -------------------------------------------------------------
def get_coding_template():
    """Returns official sample schema for Coding questions."""
    return [
        {
            "title": "Two Sum Target Indices",
            "problem_statement": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.\n\nYou may assume that each input would have exactly one solution, and you may not use the same element twice.",
            "input_description": "First line contains an integer N representing the number of elements and target integer T separated by space.\nSecond line contains N space-separated integers.",
            "output_description": "Print the zero-based indices of the two numbers in ascending order separated by space.",
            "constraints": "2 <= nums.length <= 10^4\n-10^9 <= nums[i] <= 10^9\n-10^9 <= target <= 10^9",
            "sample_input": "4 9\n2 7 11 15",
            "sample_output": "0 1",
            "languages_supported": ["Python", "Java", "C++", "JavaScript", "C"],
            "test_cases": [
                {
                    "input": "4 9\n2 7 11 15",
                    "expected_output": "0 1",
                    "is_hidden": False
                },
                {
                    "input": "3 6\n3 2 4",
                    "expected_output": "1 2",
                    "is_hidden": True
                }
            ],
            "marks": 15,
            "difficulty": "MEDIUM",
            "category": "Algorithms"
        },
        {
            "title": "Valid Parentheses String",
            "problem_statement": "Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.\n\nAn input string is valid if open brackets are closed by the same type of brackets and closed in the correct order.",
            "input_description": "A single line containing the string S of brackets.",
            "output_description": "Print 'true' if the string is valid, otherwise print 'false'.",
            "constraints": "1 <= s.length <= 10^4\ns consists of parentheses only '()[]{}'.",
            "sample_input": "()[]{}",
            "sample_output": "true",
            "languages_supported": ["Python", "Java", "C++"],
            "test_cases": [
                {
                    "input": "()[]{}",
                    "expected_output": "true",
                    "is_hidden": False
                },
                {
                    "input": "(]",
                    "expected_output": "false",
                    "is_hidden": True
                }
            ],
            "marks": 15,
            "difficulty": "EASY",
            "category": "Data Structures"
        }
    ]

def get_aptitude_template():
    """Returns official sample schema for Aptitude questions."""
    return [
        {
            "question_text": "A train running at the speed of 60 km/hr crosses a pole in 9 seconds. What is the length of the train?",
            "options": [
                {"id": "A", "text": "120 metres"},
                {"id": "B", "text": "150 metres"},
                {"id": "C", "text": "180 metres"},
                {"id": "D", "text": "324 metres"}
            ],
            "correct_option": "B",
            "explanation": "Speed = (60 * 5/18) m/sec = 50/3 m/sec. Length of train = (Speed * Time) = (50/3 * 9) = 150 metres.",
            "topic": "Time & Distance",
            "difficulty": "MEDIUM",
            "marks": 2
        },
        {
            "question_text": "If a person sells an article for Rs. 650 and gains 30%, what was the cost price of the article?",
            "options": [
                {"id": "A", "text": "Rs. 450"},
                {"id": "B", "text": "Rs. 480"},
                {"id": "C", "text": "Rs. 500"},
                {"id": "D", "text": "Rs. 520"}
            ],
            "correct_option": "C",
            "explanation": "Cost Price = (Selling Price * 100) / (100 + Gain%) = (650 * 100) / 130 = Rs. 500.",
            "topic": "Profit & Loss",
            "difficulty": "EASY",
            "marks": 2
        }
    ]

def get_mcq_template():
    """Returns official sample schema for Technical MCQ questions."""
    return [
        {
            "question_text": "What is the primary purpose of database indexing in a relational database?",
            "options": [
                {"id": "A", "text": "To increase storage capacity for tables"},
                {"id": "B", "text": "To speed up data retrieval operations without scanning all rows"},
                {"id": "C", "text": "To automatically enforce foreign key cascade deletes"},
                {"id": "D", "text": "To encrypt sensitive text data at rest"}
            ],
            "correct_option": "B",
            "explanation": "Indexes create lookup structures (e.g., B-Trees) allowing the database engine to find records with logarithmic complexity.",
            "category": "Databases",
            "difficulty": "EASY",
            "marks": 1
        },
        {
            "question_text": "In Python, which GIL (Global Interpreter Lock) behavior is true for CPU-bound threads?",
            "options": [
                {"id": "A", "text": "CPU-bound threads run concurrently on multiple CPU cores in CPython"},
                {"id": "B", "text": "The GIL is automatically disabled when using the threading module"},
                {"id": "C", "text": "CPython executes only one thread's bytecode at a time on a single CPU core"},
                {"id": "D", "text": "The GIL only applies to memory allocation and not execution"}
            ],
            "correct_option": "C",
            "explanation": "In standard CPython, the GIL ensures that only one native thread executes Python bytecode at any given moment.",
            "category": "Python Internals",
            "difficulty": "HARD",
            "marks": 1
        }
    ]

def get_sample_json_template(category='mcq'):
    """Returns template based on requested category."""
    cat = (category or 'mcq').lower()
    if cat == 'coding':
        return get_coding_template()
    elif cat == 'aptitude':
        return get_aptitude_template()
    else:
        return get_mcq_template()

# -------------------------------------------------------------
# JSON Validators
# -------------------------------------------------------------
def validate_coding_dict(item, index=0):
    """Validates an individual Coding question dictionary."""
    errors = []
    title = item.get('title')
    if not title or not isinstance(title, str) or len(title.strip()) < 3:
        errors.append(f"Item #{index+1}: 'title' is required and must be at least 3 characters.")

    problem = item.get('problem_statement')
    if not problem or not isinstance(problem, str) or len(problem.strip()) < 10:
        errors.append(f"Item #{index+1}: 'problem_statement' is required and must be at least 10 characters.")

    # Validate test cases
    test_cases = item.get('test_cases')
    if not test_cases or not isinstance(test_cases, list) or len(test_cases) < 1:
        errors.append(f"Item #{index+1}: 'test_cases' must be a list containing at least one test case.")
    else:
        for tc_idx, tc in enumerate(test_cases):
            if not isinstance(tc, dict):
                errors.append(f"Item #{index+1}, Test Case #{tc_idx+1}: Must be an object with 'input' and 'expected_output'.")
                continue
            if 'input' not in tc:
                errors.append(f"Item #{index+1}, Test Case #{tc_idx+1}: Missing 'input'.")
            if 'expected_output' not in tc:
                errors.append(f"Item #{index+1}, Test Case #{tc_idx+1}: Missing 'expected_output'.")

    # Validate marks: Approved configuration is 15 marks per coding problem
    marks = item.get('marks') or item.get('points')
    try:
        marks = float(marks) if marks is not None else 15.0
        if marks != 15.0:
            errors.append(f"Item #{index+1}: Coding questions must be exactly 15 marks (got {marks}).")
    except (ValueError, TypeError):
        errors.append(f"Item #{index+1}: 'marks' must be a valid number (15).")

    difficulty = str(item.get('difficulty', 'MEDIUM')).upper()
    if difficulty not in ['EASY', 'MEDIUM', 'HARD']:
        errors.append(f"Item #{index+1}: 'difficulty' must be EASY, MEDIUM, or HARD.")

    return errors

def validate_mcq_or_aptitude_dict(item, index=0, is_aptitude=False):
    """Validates an MCQ or Aptitude question dictionary."""
    errors = []
    question_text = item.get('question_text')
    if not question_text or not isinstance(question_text, str) or len(question_text.strip()) < 5:
        errors.append(f"Item #{index+1}: 'question_text' is required and must be at least 5 characters.")

    # Accept either 'options': [{'id':'A','text':'...'}] OR separate 'option_a', 'option_b', etc.
    options = item.get('options')
    if options and isinstance(options, list):
        if len(options) != 4:
            errors.append(f"Item #{index+1}: Exactly 4 answer options (A, B, C, D) are required.")
        else:
            ids = set()
            for opt in options:
                if not isinstance(opt, dict) or not opt.get('id') or not opt.get('text'):
                    errors.append(f"Item #{index+1}: Each option must be an object with 'id' and 'text'.")
                else:
                    ids.add(opt['id'].upper())
            if ids != {'A', 'B', 'C', 'D'}:
                errors.append(f"Item #{index+1}: Options must contain ids 'A', 'B', 'C', and 'D'.")
    elif all(k in item for k in ['option_a', 'option_b', 'option_c', 'option_d']):
        # Auto-convert flat option format
        options = [
            {"id": "A", "text": str(item['option_a']).strip()},
            {"id": "B", "text": str(item['option_b']).strip()},
            {"id": "C", "text": str(item['option_c']).strip()},
            {"id": "D", "text": str(item['option_d']).strip()}
        ]
        item['options'] = options
    else:
        errors.append(f"Item #{index+1}: Four options (A, B, C, D) are required.")

    # Validate correct_option
    raw_corr = item.get('correct_option')
    if not raw_corr:
        errors.append(f"Item #{index+1}: 'correct_option' is required and must be one of 'A', 'B', 'C', or 'D'.")
    else:
        correct_option = str(raw_corr).strip().upper()
        if correct_option not in ['A', 'B', 'C', 'D']:
            errors.append(f"Item #{index+1}: 'correct_option' must be one of 'A', 'B', 'C', or 'D'.")

        if options and isinstance(options, list):
            opt_ids = {opt.get('id', '').upper() for opt in options if isinstance(opt, dict)}
            if opt_ids and correct_option not in opt_ids:
                errors.append(f"Item #{index+1}: Correct option '{correct_option}' does not match any option id.")

    # Validate marks
    expected_marks = 2.0 if is_aptitude else 1.0
    marks = item.get('marks') or item.get('points')
    try:
        marks = float(marks) if marks is not None else expected_marks
        if marks != expected_marks:
            cat_name = "Aptitude" if is_aptitude else "Technical MCQ"
            errors.append(f"Item #{index+1}: {cat_name} questions must be exactly {int(expected_marks)} mark(s) (got {marks}).")
    except (ValueError, TypeError):
        errors.append(f"Item #{index+1}: 'marks' must be a valid number.")

    difficulty = str(item.get('difficulty', 'MEDIUM')).upper()
    if difficulty not in ['EASY', 'MEDIUM', 'HARD']:
        errors.append(f"Item #{index+1}: 'difficulty' must be EASY, MEDIUM, or HARD.")

    return errors

def parse_and_validate_question_json(json_content_or_str, category='mcq'):
    """
    Parses JSON data and validates against category schema ('coding', 'aptitude', 'mcq').
    Returns (sanitized_questions, errors).
    """
    cat = (category or 'mcq').lower()
    if isinstance(json_content_or_str, (bytes, bytearray)):
        json_content_or_str = json_content_or_str.decode('utf-8')

    try:
        data = json.loads(json_content_or_str)
    except Exception as e:
        return None, [f"Invalid JSON syntax: {str(e)}"]

    if not isinstance(data, list):
        if isinstance(data, dict):
            data = [data]
        else:
            return None, ["Root element must be a JSON array of question objects."]

    if len(data) == 0:
        return None, ["Uploaded JSON array contains no questions."]

    all_errors = []
    sanitized = []
    seen_identifiers = set()

    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            all_errors.append(f"Item #{idx+1} is not a valid JSON object.")
            continue

        if cat == 'coding':
            errs = validate_coding_dict(item, idx)
            if errs:
                all_errors.extend(errs)
            else:
                title = item['title'].strip()
                if title.lower() in seen_identifiers:
                    all_errors.append(f"Item #{idx+1}: Duplicate question title '{title}' within the uploaded file.")
                else:
                    seen_identifiers.add(title.lower())
                    sanitized.append({
                        'title': title,
                        'problem_statement': item['problem_statement'].strip(),
                        'input_description': item.get('input_description', '').strip(),
                        'output_description': item.get('output_description', '').strip(),
                        'constraints': item.get('constraints', '').strip(),
                        'sample_input': item.get('sample_input', '').strip(),
                        'sample_output': item.get('sample_output', '').strip(),
                        'languages_supported': item.get('languages_supported') or ["Python", "Java", "C++", "JavaScript"],
                        'test_cases': item.get('test_cases') or [],
                        'points': 15.0, # Fixed 15 marks
                        'difficulty': str(item.get('difficulty', 'MEDIUM')).upper(),
                        'category': item.get('category', 'Algorithms').strip(),
                        'section': 'CODING'
                    })
        else:
            is_apt = (cat == 'aptitude')
            errs = validate_mcq_or_aptitude_dict(item, idx, is_aptitude=is_apt)
            if errs:
                all_errors.extend(errs)
            else:
                q_text = item['question_text'].strip()
                if q_text.lower() in seen_identifiers:
                    all_errors.append(f"Item #{idx+1}: Duplicate question text within the uploaded file.")
                else:
                    seen_identifiers.add(q_text.lower())
                    # For aptitude, 'topic' is used; for MCQ, 'category' is used
                    topic_or_cat = item.get('topic') if is_apt else item.get('category')
                    if not topic_or_cat:
                        topic_or_cat = 'General Aptitude' if is_apt else 'General'

                    sanitized.append({
                        'question_text': q_text,
                        'options': item['options'],
                        'correct_option': str(item['correct_option']).strip().upper(),
                        'explanation': item.get('explanation', '').strip(),
                        'points': 2.0 if is_apt else 1.0,
                        'difficulty': str(item.get('difficulty', 'MEDIUM')).upper(),
                        'category': str(topic_or_cat).strip(),
                        'section': 'APTITUDE' if is_apt else 'MCQ'
                    })

    if all_errors:
        return None, all_errors

    return sanitized, None

# -------------------------------------------------------------
# Database Persistence
# -------------------------------------------------------------
def save_imported_questions(questions_list, category='mcq', assessment_id=None):
    """
    Persists reviewed and validated questions to database according to category.
    Prevents duplicates if same question already exists for the assessment.
    """
    cat = (category or 'mcq').lower()
    if assessment_id:
        assessment = db.session.get(Assessment, assessment_id)
        if not assessment:
            return 0, "Selected assessment does not exist."

    created_count = 0
    try:
        if cat == 'coding':
            for q_data in questions_list:
                # Check duplicate
                existing = CodingQuestion.query.filter_by(
                    title=q_data['title'],
                    assessment_id=assessment_id
                ).first()
                if existing:
                    continue

                cq = CodingQuestion(
                    assessment_id=assessment_id,
                    title=q_data['title'],
                    problem_statement=q_data['problem_statement'],
                    input_description=q_data.get('input_description', ''),
                    output_description=q_data.get('output_description', ''),
                    constraints=q_data.get('constraints', ''),
                    sample_input=q_data.get('sample_input', ''),
                    sample_output=q_data.get('sample_output', ''),
                    languages_supported=q_data.get('languages_supported', ["Python", "Java", "C++"]),
                    test_cases=q_data.get('test_cases', []),
                    points=15.0, # 15 marks
                    difficulty=q_data.get('difficulty', 'MEDIUM'),
                    category=q_data.get('category', 'Algorithms'),
                    section='CODING',
                    is_active=True
                )
                db.session.add(cq)
                created_count += 1
        else:
            section_val = 'APTITUDE' if cat == 'aptitude' else 'MCQ'
            expected_pts = 2.0 if cat == 'aptitude' else 1.0

            for q_data in questions_list:
                # Check duplicate
                existing = Question.query.filter_by(
                    question_text=q_data['question_text'],
                    section=section_val,
                    assessment_id=assessment_id
                ).first()
                if existing:
                    continue

                q = Question(
                    assessment_id=assessment_id,
                    question_text=q_data['question_text'],
                    question_type='MCQ',
                    section=section_val,
                    options=q_data['options'],
                    correct_option=q_data['correct_option'],
                    explanation=q_data.get('explanation', ''),
                    points=expected_pts,
                    difficulty=q_data.get('difficulty', 'MEDIUM'),
                    category=q_data.get('category', 'General'),
                    is_active=True
                )
                db.session.add(q)
                created_count += 1

        db.session.commit()
        return created_count, None
    except Exception as e:
        db.session.rollback()
        return 0, f"Error saving questions: {str(e)}"

# -------------------------------------------------------------
# Query & Stats Helpers
# -------------------------------------------------------------
def get_question_bank_stats(assessment_id=None):
    """
    Computes real-time counts and approved mark allocations for each category card.
    """
    coding_q = CodingQuestion.query.filter_by(is_active=True)
    aptitude_q = Question.query.filter_by(section='APTITUDE', is_active=True)
    mcq_q = Question.query.filter_by(section='MCQ', is_active=True)

    if assessment_id:
        coding_q = coding_q.filter_by(assessment_id=assessment_id)
        aptitude_q = aptitude_q.filter_by(assessment_id=assessment_id)
        mcq_q = mcq_q.filter_by(assessment_id=assessment_id)

    coding_count = coding_q.count()
    aptitude_count = aptitude_q.count()
    mcq_count = mcq_q.count()

    return {
        'coding': {
            'count': coding_count,
            'target_questions': 4,
            'marks_per_question': 15,
            'total_marks': 60
        },
        'aptitude': {
            'count': aptitude_count,
            'target_questions': 10,
            'marks_per_question': 2,
            'total_marks': 20
        },
        'mcq': {
            'count': mcq_count,
            'target_questions': 20,
            'marks_per_question': 1,
            'total_marks': 20
        },
        'overall': {
            'total_target_questions': 34,
            'total_target_marks': 100,
            'total_actual_questions': coding_count + aptitude_count + mcq_count,
            'total_actual_marks': (coding_count * 15) + (aptitude_count * 2) + (mcq_count * 1)
        }
    }

def get_coding_questions_query(assessment_id=None, category=None, difficulty=None, search=None):
    """Builds filtered query for Coding questions."""
    query = CodingQuestion.query
    if assessment_id:
        query = query.filter_by(assessment_id=assessment_id)
    if category:
        query = query.filter_by(category=category)
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            (CodingQuestion.title.ilike(search_term)) |
            (CodingQuestion.problem_statement.ilike(search_term))
        )
    return query.order_by(CodingQuestion.created_at.desc())

def get_mcq_questions_query(section='MCQ', assessment_id=None, category=None, difficulty=None, search=None):
    """Builds filtered query for Aptitude or Technical MCQ questions."""
    query = Question.query.filter_by(section=section)
    if assessment_id:
        query = query.filter_by(assessment_id=assessment_id)
    if category:
        query = query.filter_by(category=category)
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    if search:
        query = query.filter(Question.question_text.ilike(f"%{search.strip()}%"))
    return query.order_by(Question.created_at.desc())
