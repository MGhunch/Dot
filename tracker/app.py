# Dot Tracker
# Finance/tracker reports for Hunch agency
#
# PLACEHOLDER - To be implemented
#
# This will:
# - Generate quarterly finance reports per client
# - Show budget vs actual spend
# - Track retainer usage
# - Highlight overspend/underspend

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/tracker', methods=['POST'])
def tracker():
    """Generate finance tracker - PLACEHOLDER"""
    return jsonify({
        'status': 'placeholder',
        'message': 'Dot Tracker endpoint - coming soon'
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Dot Tracker',
        'version': '0.1-placeholder'
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
