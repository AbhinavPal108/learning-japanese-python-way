"""One durable Pomodoro timer; writes and completion are atomic."""
import json
import math
import time
from datetime import datetime
from uuid import uuid4

MODES = ('focus', 'shortBreak', 'longBreak')
LIMITS = {'focus': 180, 'shortBreak': 60, 'longBreak': 90}

class TimerError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status

def read(db, key, default):
    row = db.execute('SELECT value FROM app_data WHERE key=?', (key,)).fetchone()
    return json.loads(row['value']) if row else default

def write(db, key, value):
    db.execute('INSERT INTO app_data(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, json.dumps(value)))


def _create_focus_session(db, now, status='running', elapsed_seconds=0):
    session_id = str(uuid4())
    segment_started_at = now if status == 'running' else None
    db.execute(
        '''INSERT INTO focus_sessions
            (session_id, started_at, status, elapsed_seconds, segment_started_at)
            VALUES (?, ?, ?, ?, ?)''',
        (session_id, now, status, elapsed_seconds, segment_started_at),
    )
    return session_id


def _update_focus_session(db, session_id, status, now, end_at=None):
    if not session_id:
        return
    row = db.execute(
        '''SELECT status, elapsed_seconds, segment_started_at
           FROM focus_sessions WHERE session_id=?''',
        (session_id,),
    ).fetchone()
    if row is None:
        return

    elapsed_seconds = row['elapsed_seconds']
    if row['status'] == 'running' and row['segment_started_at'] is not None:
        stop_at = min(now, end_at) if end_at is not None else now
        elapsed_seconds += max(0, stop_at - row['segment_started_at'])

    segment_started_at = now if status == 'running' else None
    ended_at = (
        (end_at if end_at is not None else now)
        if status in ('completed', 'cancelled')
        else None
    )
    db.execute(
        '''UPDATE focus_sessions
           SET status=?, elapsed_seconds=?, segment_started_at=?, ended_at=?
           WHERE session_id=?''',
        (status, elapsed_seconds, segment_started_at, ended_at, session_id),
    )


def validate_settings(value):
    if not isinstance(value, dict):
        raise TimerError('Settings must be a JSON object.')
    clean = {}
    for key, maximum in LIMITS.items():
        n = value.get(key)
        if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= maximum:
            raise TimerError(f'{key} must be a whole number from 1 to {maximum} minutes.')
        clean[key] = n
    for key in ('autoStartBreaks', 'autoStartFocus'):
        flag = value.get(key, False)
        if not isinstance(flag, bool):
            raise TimerError(key + ' must be true or false.')
        clean[key] = flag
    return clean

def timer_request(db, defaults, data=None, now=None):
    now = time.time() if now is None else now
    db.execute('BEGIN IMMEDIATE')
    settings = read(db, 'settings', defaults)
    state = read(db, 'shared_timer', {
        'mode': 'focus', 'running': False, 'remaining': settings['focus'] * 60,
        'duration': settings['focus'] * 60, 'deadline': None, 'round': 1,
        'revision': 0, 'completed': 0, 'task_id': None,
        'focus_session_id': None,
    })
    state.setdefault('focus_session_id', None)
    state.pop('deck_id', None)
    if state['running'] and state['deadline'] <= now:
        end = datetime.fromtimestamp(state['deadline'])
        if state['mode'] == 'focus':
            task = db.execute('SELECT t.*, s.name AS subject_name FROM tasks t LEFT JOIN subjects s ON s.id=t.subject_id WHERE t.id=?', (state['task_id'],)).fetchone()
            session_id = state['focus_session_id']
            if session_id:
                _update_focus_session(db, session_id, 'completed', now, state['deadline'])
            db.execute('''INSERT INTO sessions
                (date,time,duration,task_id,subject_id,task_name,subject_name,created_at,focus_session_id)
                VALUES (?,?,?,?,?,?,?,?,?)''', (end.date().isoformat(), end.strftime('%H:%M'),
                state['duration'] // 60, task['id'] if task else None,
                task['subject_id'] if task else None, task['title'] if task else None,
                task['subject_name'] if task else None, end.isoformat(timespec='seconds'),
                session_id))
            state['completed'] += 1
            state['focus_session_id'] = None
            state['mode'] = 'longBreak' if state['round'] == 4 else 'shortBreak'
        else:
            state['round'] = 1 if state['mode'] == 'longBreak' else state['round'] + 1
            state['mode'] = 'focus'
        state['duration'] = settings[state['mode']] * 60
        state['remaining'] = state['duration']
        state['running'] = settings['autoStartFocus' if state['mode'] == 'focus' else 'autoStartBreaks']
        # Reopening after a long absence advances one phase, without inventing completed rounds.
        state['deadline'] = now + state['duration'] if state['running'] else None
        if state['mode'] == 'focus' and state['running']:
            state['focus_session_id'] = _create_focus_session(db, now)
        state['revision'] += 1
    elif state['mode'] == 'focus' and state['focus_session_id'] is None:
        # Adopt an in-flight timer created before lifecycle tracking was added.
        if state['running']:
            segment_start = state['deadline'] - state['remaining']
            state['focus_session_id'] = _create_focus_session(
                db, segment_start, status='running')
        elif state['remaining'] < state['duration']:
            elapsed = state['duration'] - state['remaining']
            state['focus_session_id'] = _create_focus_session(
                db, now - elapsed, status='paused', elapsed_seconds=elapsed)
    error = None
    if data is not None:
        if not isinstance(data, dict):
            error = TimerError('Send a JSON object.')
        elif data.get('revision') != state['revision']:
            error = TimerError('Timer changed in another tab. Synced; try your action again.', 409)
        else:
            try:
                action = data.get('action')
                if action == 'start':
                    if not state['running']:
                        if state['mode'] == 'focus':
                            if state['focus_session_id'] is None:
                                state['focus_session_id'] = _create_focus_session(db, now)
                            _update_focus_session(
                                db, state['focus_session_id'], 'running', now)
                        state['running'] = True
                        state['deadline'] = now + state['remaining']
                elif action == 'pause':
                    if state['running']:
                        if state['mode'] == 'focus':
                            _update_focus_session(
                                db, state['focus_session_id'], 'paused', now)
                        state['remaining'] = max(0, state['deadline'] - now)
                        state['running'] = False
                        state['deadline'] = None
                elif action in ('reset', 'mode', 'settings'):
                    if action == 'mode' and data.get('mode') not in MODES:
                        raise TimerError('Choose focus, shortBreak or longBreak.')
                    if action == 'settings':
                        settings = validate_settings(data.get('settings'))
                    resets_timer = action != 'settings' or not state['running']
                    if resets_timer and state['mode'] == 'focus':
                        _update_focus_session(
                            db, state['focus_session_id'], 'cancelled', now)
                        state['focus_session_id'] = None
                    if action == 'mode':
                        state['mode'] = data['mode']
                    if action == 'settings':
                        write(db, 'settings', settings)
                    if resets_timer:
                        state['duration'] = settings[state['mode']] * 60
                        state['remaining'] = state['duration']
                        state['running'] = False
                        state['deadline'] = None
                elif action == 'task':
                    task_id = data.get('task_id')
                    if task_id is not None and (type(task_id) is not int or not db.execute('SELECT id FROM tasks WHERE id=?', (task_id,)).fetchone()):
                        raise TimerError('Select an existing task.')
                    state['task_id'] = task_id
                else:
                    raise TimerError('Unknown timer action.')
                state['revision'] += 1
            except TimerError as exc:
                error = exc
    write(db, 'shared_timer', state)
    # Commit a genuine completion even if a simultaneous user command was stale.
    db.commit()
    if error:
        raise error
    remaining = max(0, state['deadline'] - now) if state['running'] else state['remaining']
    return {**state, 'remaining_seconds': remaining, 'settings': settings,
            'server_time': now, 'success': True}
