# Dot Feedback
# Client feedback processing for Hunch agency
# 
# PLACEHOLDER - To be implemented
#
# This will:
# - Extract feedback from PDFs (margin comments)
# - Extract feedback from Word docs (tracked changes, comments)
# - Categorise as Clear / Ambiguous / Question
# - Estimate effort required
# - Track feedback rounds

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/feedback', methods=['POST'])
def feedback():
    """Process client feedback - PLACEHOLDER"""
    return jsonify({
        'status': 'placeholder',
        'message': 'Dot Feedback endpoint - coming soon'
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Dot Feedback',
        'version': '0.1-placeholder'
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
