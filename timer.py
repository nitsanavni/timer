import yaml
import curses
import time
import threading
import random
import os
import sys
from datetime import datetime
from curses import wrapper

# Default configuration
default_config = {
    'config': {
        'default_turn_duration': 60,
        'positions': ['Position 1', 'Position 2', 'Position 3'],
        'actions': {
            'rotate': 'r',
            'randomize': 'x',
            'start': 's',
            'stop': 't',
            'pause': 'p'
        },
        'keymaps': {},
        'hooks': {},
    },
    'session': {
        'participants': [],
        'state': 'stopped',
        'time_elapsed': 0,
        'turn_duration': 60,
    },
    'live_view': {
        'update_interval': 1,
    }
}

# Load or create configuration
config_file_path = 'config.yml'
if not os.path.exists(config_file_path):
    with open(config_file_path, 'w') as file:
        yaml.dump(default_config, file)
        config_data = default_config
else:
    with open(config_file_path, 'r') as file:
        config_data = yaml.safe_load(file)

config = config_data['config']
session = config_data['session']
live_view = config_data['live_view']

# Global variables
participants = session['participants']
turn_duration = session.get('turn_duration', config['default_turn_duration'])
state = session.get('state', 'stopped')
time_elapsed = session.get('time_elapsed', 0)
timer_paused = False
timer_thread = None
session_id = session.get(
    'session_id', f"session_{datetime.now().strftime('%Y_%m_%d')}")

positions = config.get('positions', [])
actions = config.get('actions', {})
keymaps = config.get('keymaps', {})

# Lock for thread safety
lock = threading.Lock()


def run_hook(hook_name):
    hook_script = config['hooks'].get(hook_name)
    if hook_script:
        os.system(hook_script)


def update_timer():
    global time_elapsed, timer_paused, participants
    while state == 'active':
        time.sleep(1)
        with lock:
            if not timer_paused:
                time_elapsed += 1
                current_participant = participants[0]
                current_participant['time_remaining'] -= 1
                run_hook('timer_update')
                if current_participant['time_remaining'] <= 0:
                    run_hook('timer_expire')
                    rotate_participants()
                    time_elapsed = 0
                save_session()


def rotate_participants():
    global participants
    # Rotate participants list
    participants = participants[1:] + [participants[0]]
    # Assign positions
    assign_positions()
    # Reset time_remaining for the participant in the first position
    if participants:
        participants[0]['time_remaining'] = turn_duration
    save_session()


def assign_positions():
    for idx, participant in enumerate(participants):
        if idx < len(positions):
            participant['position'] = positions[idx]
        else:
            participant['position'] = None


def randomize_participants():
    global participants
    random.shuffle(participants)
    assign_positions()
    save_session()


def start_timer():
    global state, timer_thread
    if state != 'active':
        state = 'active'
        timer_thread = threading.Thread(target=update_timer)
        timer_thread.daemon = True
        timer_thread.start()
        save_session()


def stop_timer():
    global state
    state = 'stopped'
    save_session()


def pause_timer():
    global timer_paused
    timer_paused = not timer_paused
    save_session()


def add_person(name):
    participants.append({
        'name': name,
        'position': None,
        'time_remaining': turn_duration
    })
    assign_positions()
    save_session()


def remove_person(name):
    global participants
    participants = [p for p in participants if p['name'] != name]
    assign_positions()
    save_session()


def edit_turn_length(length):
    global turn_duration
    turn_duration = length
    for participant in participants:
        participant['time_remaining'] = length
    save_session()


def handle_input(key):
    if key == ord(actions.get('rotate', 'r')):
        rotate_participants()
    elif key == ord(actions.get('randomize', 'x')):
        randomize_participants()
    elif key == ord(actions.get('start', 's')):
        start_timer()
    elif key == ord(actions.get('stop', 't')):
        stop_timer()
    elif key == ord(actions.get('pause', 'p')):
        pause_timer()
    elif key == ord('q'):
        stop_timer()
        curses.endwin()
        sys.exit()
    # Add more key handling as needed


def draw_screen(stdscr):
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "Positions and Participants:")
        row = 2
        max_col_width = 20  # Adjust as needed for spacing
        for idx, position in enumerate(positions):
            col = idx * max_col_width
            stdscr.addstr(row, col, f"{position}:")
            participant = next(
                (p for p in participants if p.get('position') == position), None)
            if participant:
                time_remaining = participant.get(
                    'time_remaining', turn_duration)
                stdscr.addstr(row + 1, col, f"  {participant['name']}")
                stdscr.addstr(row + 2, col, f"  Time Left: {time_remaining}s")
            else:
                stdscr.addstr(row + 1, col, "  (None)")
        unassigned = [p for p in participants if p.get('position') is None]
        if unassigned:
            stdscr.addstr(row + 4, 0, "Unassigned Participants:")
            for idx, participant in enumerate(unassigned):
                stdscr.addstr(row + 5 + idx, 0, f"  {participant['name']}")
        stdscr.addstr(row + 7, 0, f"State: {state}")
        stdscr.addstr(row + 8, 0, f"Time Elapsed: {time_elapsed}s")
        stdscr.addstr(row + 10, 0, "Press 'q' to quit.")
        stdscr.refresh()
        time.sleep(live_view['update_interval'])


def save_session():
    session_data = {
        'session_id': session_id,
        'participants': participants,
        'state': state,
        'time_elapsed': time_elapsed,
        'turn_duration': turn_duration
    }
    with open(f'{session_id}.yml', 'w') as file:
        yaml.dump({'session': session_data}, file)


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    assign_positions()
    threading.Thread(target=draw_screen, args=(stdscr,), daemon=True).start()
    while True:
        key = stdscr.getch()
        if key != -1:
            handle_input(key)
        time.sleep(0.1)


if __name__ == '__main__':
    wrapper(main)
