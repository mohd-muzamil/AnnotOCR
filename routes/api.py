import json
from flask import Blueprint, request, jsonify
import os

SUGGESTIONS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'app_suggestions.json')

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/suggestions', methods=['GET', 'POST'])
def handle_suggestions():
    if not os.path.exists(os.path.dirname(SUGGESTIONS_FILE)):
        os.makedirs(os.path.dirname(SUGGESTIONS_FILE))

    if not os.path.exists(SUGGESTIONS_FILE):
        with open(SUGGESTIONS_FILE, 'w') as f:
            json.dump([], f)

    with open(SUGGESTIONS_FILE, 'r') as f:
        suggestions = json.load(f)

    if request.method == 'POST':
        data = request.get_json()
        new_suggestion = data.get('suggestion', '').strip()
        if new_suggestion and new_suggestion not in suggestions:
            suggestions.append(new_suggestion)
            with open(SUGGESTIONS_FILE, 'w') as f:
                json.dump(suggestions, f, indent=2)
            return jsonify({'success': True, 'suggestion': new_suggestion})
        return jsonify({'success': False, 'error': 'Invalid or duplicate suggestion'}), 400

    # GET request logic
    query = request.args.get('q', '').strip().lower()
    if not query or len(query) < 2:
        return jsonify({'suggestions': []})

    filtered_suggestions = [s for s in suggestions if query in s.lower()]
    return jsonify({'suggestions': filtered_suggestions[:10]})
