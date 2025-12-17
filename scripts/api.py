@app.route('/scrape', methods=['POST'])
def scrape():
    """
    Scrape with user context
    POST Body: {
        "url": "...",
        "task_id": "...",
        "user_question": "best laptops under $1000",  # NEW!
        "visual": false
    }
    """
    try:
        data = request.json
        url = data.get('url')
        task_id = data.get('task_id')
        user_question = data.get('user_question', '')  # NEW
        visual = data.get('visual', False)

        if not url or not task_id:
            return jsonify({'error': 'Missing url or task_id', 'status': 'fail'}), 400

        # Build command with context
        cmd = [
            'docker', 'exec', 'camoufox',
            'python3', '/workspace/scrape.py',
            url,
            task_id,
            user_question if user_question else 'general',  # Pass question
            'false' if visual else 'true'  # headless flag
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)

        if result.returncode != 0:
            return jsonify({
                'error': f'Scraper failed: {result.stderr}',
                'status': 'fail'
            }), 500

        try:
            scrape_result = json.loads(result.stdout)
            return jsonify(scrape_result)
        except json.JSONDecodeError:
            return jsonify({
                'error': 'Invalid JSON from scraper',
                'stdout': result.stdout[:500],
                'status': 'fail'
            }), 500

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Scraping timeout', 'status': 'fail'}), 500
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'fail'}), 500
