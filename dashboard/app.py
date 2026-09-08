#!/usr/bin/env python3
"""Kangaroo Solver Web Dashboard - Final with time tracking"""

import json
import os
import re
import sqlite3
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kangaroo-dashboard-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

KANGAROO_BIN = Path.home() / 'kangaroo' / 'target' / 'release' / 'kangaroo'
DB_PATH = Path.home() / 'kangaroo' / 'dashboard' / 'solutions.db'
CMD_FILE = Path.home() / 'kangaroo' / 'dashboard' / 'command.json'
STATUS_FILE = Path.home() / 'kangaroo' / 'dashboard' / 'status.json'

solver_state = {
    'status': 'idle',
    'pubkey': '',
    'start_hex': '',
    'range_bits': 0,
    'found_key': None,
    'logs': [],
    'total_ops': 0,
    'speed_ops': 0.0,
    'elapsed_seconds': 0,
    'estimated_remaining_seconds': 0,
    'progress_percent': 0.0,
    'gpu_name': '',
    'start_time': None,
}

state_lock = threading.Lock()
MAX_LOGS = 100


def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS solutions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pubkey TEXT NOT NULL,
        private_key TEXT NOT NULL,
        range_bits INTEGER,
        elapsed_seconds REAL,
        total_ops INTEGER,
        solved_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()


def save_status():
    with state_lock:
        # Calculate times
        if solver_state['start_time'] and solver_state['status'] == 'running':
            solver_state['elapsed_seconds'] = time.time() - solver_state['start_time']
        
        # Calculate estimated remaining time
        if solver_state['speed_ops'] > 0 and solver_state['range_bits'] > 0:
            total_keys = 2 ** solver_state['range_bits']
            remaining_keys = max(0, total_keys - solver_state['total_ops'])
            solver_state['estimated_remaining_seconds'] = remaining_keys / solver_state['speed_ops']
            solver_state['progress_percent'] = min(100.0, (solver_state['total_ops'] / total_keys) * 100)
        else:
            solver_state['estimated_remaining_seconds'] = 0
            solver_state['progress_percent'] = 0
        
        with open(STATUS_FILE, 'w') as f:
            json.dump(solver_state, f, indent=2, default=str)


def load_command():
    if CMD_FILE.exists():
        with open(CMD_FILE, 'r') as f:
            return json.load(f)
    return None


def clear_command():
    if CMD_FILE.exists():
        CMD_FILE.unlink()


def add_log(message):
    with state_lock:
        timestamp = datetime.now().strftime('%H:%M:%S')
        solver_state['logs'].append(f'[{timestamp}] {message}')
        if len(solver_state['logs']) > MAX_LOGS:
            solver_state['logs'] = solver_state['logs'][-MAX_LOGS:]


def format_time(seconds):
    """Format seconds to human readable time."""
    if seconds <= 0 or seconds == float('inf'):
        return "--"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 1000000:
        years = hours // 8760
        return f"{years} anos"
    elif hours > 1000:
        days = hours // 24
        return f"{days} dias"
    elif hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def monitor_output(output_file):
    """Monitor solver output file in real-time."""
    global solver_state
    
    try:
        with open(output_file, 'r') as f:
            f.seek(0)
            last_pos = 0
            
            while True:
                with state_lock:
                    if solver_state['status'] != 'running':
                        break
                
                f.seek(last_pos)
                lines = f.readlines()
                
                if lines:
                    last_pos = f.tell()
                    
                    for line in lines:
                        line = line.strip()
                        if line:
                            add_log(line)
                            
                            with state_lock:
                                # Parse ops
                                ops_match = re.search(r'Ops:\s*([\d,]+[KM]?)', line)
                                if ops_match:
                                    ops_str = ops_match.group(1).replace(',', '')
                                    if 'M' in ops_str:
                                        solver_state['total_ops'] = int(float(ops_str.replace('M', '')) * 1_000_000)
                                    elif 'K' in ops_str:
                                        solver_state['total_ops'] = int(float(ops_str.replace('K', '')) * 1_000)
                                    else:
                                        solver_state['total_ops'] = int(ops_str)
                                    
                                    # Calculate speed
                                    if solver_state['start_time']:
                                        elapsed = time.time() - solver_state['start_time']
                                        if elapsed > 0:
                                            solver_state['speed_ops'] = solver_state['total_ops'] / elapsed
                                
                                # Parse GPU
                                if 'GPU:' in line:
                                    match = re.search(r'GPU:\s*(.+)', line)
                                    if match:
                                        solver_state['gpu_name'] = match.group(1).strip()
                                
                                # Parse found key
                                if 'Private key found:' in line:
                                    match = re.search(r'0x([0-9a-fA-F]+)', line)
                                    if match:
                                        solver_state['found_key'] = match.group(1)
                                        add_log(f'CHAVE ENCONTRADA: {match.group(1)}')
                                        
                                        save_solution(
                                            solver_state['pubkey'],
                                            solver_state['found_key'],
                                            solver_state['range_bits'],
                                            solver_state['elapsed_seconds'],
                                            solver_state['total_ops']
                                        )
                            
                            save_status()
                            socketio.emit('status_update', get_status_dict())
                
                time.sleep(1)
        
        with state_lock:
            if solver_state['status'] == 'running':
                solver_state['status'] = 'stopped'
                add_log('Processo finalizado')
        
        save_status()
        socketio.emit('status_update', get_status_dict())
        
    except Exception as e:
        add_log(f'ERRO monitor: {str(e)}')
        save_status()


def save_solution(pubkey, private_key, range_bits, elapsed_seconds, total_ops):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('''INSERT INTO solutions 
        (pubkey, private_key, range_bits, elapsed_seconds, total_ops, solved_at)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (pubkey, private_key, range_bits, elapsed_seconds, total_ops, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def run_solver():
    """Main solver loop."""
    global solver_state
    
    while True:
        cmd = load_command()
        
        if cmd and solver_state['status'] == 'idle':
            with state_lock:
                solver_state['status'] = 'running'
                solver_state['pubkey'] = cmd.get('pubkey', '')
                solver_state['start_hex'] = cmd.get('start_hex', '')
                solver_state['range_bits'] = cmd.get('range_bits', 0)
                solver_state['found_key'] = None
                solver_state['logs'] = ['Solver iniciado']
                solver_state['total_ops'] = 0
                solver_state['speed_ops'] = 0.0
                solver_state['elapsed_seconds'] = 0
                solver_state['estimated_remaining_seconds'] = 0
                solver_state['progress_percent'] = 0
                solver_state['gpu_name'] = ''
                solver_state['start_time'] = time.time()
            
            save_status()
            clear_command()
            
            output_file = f'/tmp/kangaroo_{int(time.time())}.log'
            
            try:
                kangaroo_cmd = [
                    str(KANGAROO_BIN),
                    '--pubkey', solver_state['pubkey'],
                    '--start', solver_state['start_hex'],
                    '--range', str(solver_state['range_bits']),
                    '--gpu', cmd.get('gpu', '0'),
                    '--backend', cmd.get('backend', 'auto'),
                ]
                
                with open(output_file, 'w') as f:
                    proc = subprocess.Popen(
                        kangaroo_cmd,
                        stdout=f,
                        stderr=subprocess.STDOUT,
                        text=True,
                        cwd=str(Path.home() / 'kangaroo'),
                    )
                    
                    # Start monitor thread
                    monitor_thread = threading.Thread(
                        target=monitor_output,
                        args=(output_file,),
                        daemon=True
                    )
                    monitor_thread.start()
                    
                    proc.wait()
                
                with state_lock:
                    solver_state['elapsed_seconds'] = time.time() - solver_state['start_time']
                
                save_status()
                
            except Exception as e:
                add_log(f'ERRO: {str(e)}')
                save_status()
        
        time.sleep(1)


def get_status_dict():
    with state_lock:
        result = dict(solver_state)
        result['elapsed_formatted'] = format_time(result.get('elapsed_seconds', 0))
        result['estimated_formatted'] = format_time(result.get('estimated_remaining_seconds', 0))
        result['speed_formatted'] = format_speed(result.get('speed_ops', 0))
        return result


def format_speed(ops_per_second):
    if ops_per_second >= 1_000_000:
        return f"{ops_per_second / 1_000_000:.2f} M/s"
    elif ops_per_second >= 1_000:
        return f"{ops_per_second / 1_000:.2f} K/s"
    else:
        return f"{ops_per_second:.0f} /s"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    if STATUS_FILE.exists():
        with open(STATUS_FILE, 'r') as f:
            data = json.load(f)
            data['elapsed_formatted'] = format_time(data.get('elapsed_seconds', 0))
            data['estimated_formatted'] = format_time(data.get('estimated_remaining_seconds', 0))
            data['speed_formatted'] = format_speed(data.get('speed_ops', 0))
            return jsonify(data)
    return jsonify(solver_state)


@app.route('/api/start', methods=['POST'])
def api_start():
    data = request.json or {}
    
    if not data.get('pubkey'):
        return jsonify({'error': 'pubkey required'}), 400
    
    with open(CMD_FILE, 'w') as f:
        json.dump(data, f)
    
    return jsonify({'message': 'Command queued'})


@app.route('/api/stop', methods=['POST'])
def api_stop():
    with state_lock:
        solver_state['status'] = 'stopped'
    save_status()
    return jsonify({'message': 'Stopped'})


@app.route('/api/reset', methods=['POST'])
def api_reset():
    with state_lock:
        solver_state['status'] = 'idle'
        solver_state['found_key'] = None
        solver_state['logs'] = []
        solver_state['total_ops'] = 0
        solver_state['speed_ops'] = 0.0
        solver_state['elapsed_seconds'] = 0
        solver_state['estimated_remaining_seconds'] = 0
        solver_state['progress_percent'] = 0
        solver_state['start_time'] = None
    save_status()
    return jsonify({'message': 'Reset'})


@app.route('/api/solutions')
def api_solutions():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('SELECT * FROM solutions ORDER BY created_at DESC')
    columns = [desc[0] for desc in c.description]
    results = [dict(zip(columns, row)) for row in c.fetchall()]
    conn.close()
    return jsonify(results)


@socketio.on('connect')
def handle_connect():
    if STATUS_FILE.exists():
        with open(STATUS_FILE, 'r') as f:
            data = json.load(f)
            data['elapsed_formatted'] = format_time(data.get('elapsed_seconds', 0))
            data['estimated_formatted'] = format_time(data.get('estimated_remaining_seconds', 0))
            data['speed_formatted'] = format_speed(data.get('speed_ops', 0))
            emit('status_update', data)


if __name__ == '__main__':
    init_db()
    
    solver_thread = threading.Thread(target=run_solver, daemon=True)
    solver_thread.start()
    
    print("Starting Kangaroo Dashboard (Final) on port 10001...")
    socketio.run(app, host='0.0.0.0', port=10001, debug=False, allow_unsafe_werkzeug=True)
