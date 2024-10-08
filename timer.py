import yaml
import curses
import time
import threading
import random
import os
import sys
from datetime import datetime
from curses import wrapper, textpad

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
            'pause': 'p',
            'add': 'a',
            'edit_duration': 'd',
            'edit_position': 'e',
            'delete_position': 'd',
            'add_position': 'a'
        },
        'keymaps': {},
        'hooks': {},
    },
    'session': {
        'participants': [],
        'positions': ['Position 1', 'Position 2', 'Position 3'],
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

# Load session from file if it exists
session_file_path = f"session_{datetime.now().strftime('%Y_%m_%d')}.yml"
if os.path.exists(session_file_path):
    with open(session_file_path, 'r') as file:
        session_data = yaml.safe_load(file).get('session', {})
        participants = session_data.get(
            'participants', session['participants'])
        positions = session_data.get('positions', session['positions'])
        state = session_data.get('state', session['state'])
        time_elapsed = session_data.get(
            'time_elapsed', session['time_elapsed'])
        turn_duration = session_data.get(
            'turn_duration', session['turn_duration'])
else:
    participants = session['participants']
    positions = session.get('positions', [])
    turn_duration = session['turn_duration']
    state = session['state']
    time_elapsed = session.get('time_elapsed', 0)

timer_paused = False
timer_thread = None
session_id = session.get(
    'session_id', f"session_{datetime.now().strftime('%Y_%m_%d')}")

actions = config.get('actions', {})
keymaps = config.get('keymaps', {})

# Lock for thread safety
lock = threading.Lock()
position_edit_mode = False
participants_edit_mode = False
selected_position_index = -1
selected_participant_index = -1


def run_hook(hook_name):
    hook_script = config['hooks'].get(hook_name)
    if hook_script:
        os.system(hook_script)


def update_timer():
    global time_elapsed, timer_paused, state
    while state == 'active' and not timer_paused:
        time.sleep(1)
        with lock:
            time_elapsed += 1
            if time_elapsed >= turn_duration and participants:
                run_hook('timer_expire')
                stop_timer()
                rotate_participants()
            save_session()


def rotate_participants():
    global participants
    if participants:
        first_participant = participants.pop(0)
        participants.append(first_participant)
    save_session()


def randomize_participants():
    global participants
    random.shuffle(participants)
    save_session()


def start_timer():
    global state, timer_thread, timer_paused
    if state != 'active':
        state = 'active'
        timer_paused = False
        if not timer_thread or not timer_thread.is_alive():
            timer_thread = threading.Thread(target=update_timer)
            timer_thread.daemon = True
            timer_thread.start()
        save_session()


def stop_timer():
    global state, time_elapsed
    state = 'stopped'
    time_elapsed = 0
    save_session()


def pause_timer():
    global timer_paused
    timer_paused = not timer_paused
    save_session()


def add_person(name):
    participants.append(name)
    save_session()


def remove_person(name):
    global participants
    participants = [p for p in participants if p != name]
    save_session()


def edit_person(index, new_name):
    global participants
    if 0 <= index < len(participants):
        participants[index] = new_name
    save_session()


def edit_turn_length(length):
    global turn_duration
    turn_duration = length
    save_session()


def edit_position(index, new_name):
    global positions
    if 0 <= index < len(positions):
        positions[index] = new_name
    save_session()


def delete_position(index):
    global positions
    if 0 <= index < len(positions):
        del positions[index]
    save_session()


def add_position(name):
    global positions
    positions.append(name)
    save_session()


def handle_input(key, stdscr):
    global position_edit_mode, participants_edit_mode, selected_position_index, selected_participant_index

    if key == ord('p'):
        position_edit_mode = not position_edit_mode
        participants_edit_mode = False

    if key == ord('m'):
        participants_edit_mode = not participants_edit_mode
        position_edit_mode = False

    if not position_edit_mode and not participants_edit_mode:
        if key == ord(actions.get('rotate', 'r')):
            stop_timer()
            rotate_participants()
        elif key == ord(actions.get('randomize', 'x')):
            randomize_participants()
        elif key == ord(actions.get('start', 's')):
            start_timer()
        elif key == ord(actions.get('stop', 't')):
            stop_timer()
        elif key == ord(actions.get('pause', 'p')):
            pause_timer()
        elif key == ord(actions.get('add', 'a')):
            stdscr.addstr(12, 0, "Enter name: ")
            textwin = curses.newwin(1, 20, 12, 12)
            textpad_obj = textpad.Textbox(textwin)
            stdscr.refresh()
            name = textpad_obj.edit().strip()
            add_person(name)
        elif key == ord(actions.get('edit_duration', 'd')):
            stdscr.addstr(14, 0, "Enter new duration: ")
            textwin = curses.newwin(1, 5, 14, 20)
            textpad_obj = textpad.Textbox(textwin)
            stdscr.refresh()
            new_duration = int(textpad_obj.edit().strip())
            edit_turn_length(new_duration)
        elif key == ord('q'):
            stop_timer()
            curses.endwin()
            sys.exit()
    elif position_edit_mode:
        if key >= ord('1') and key <= ord('9'):
            selected_position_index = key - ord('1')
        elif key == ord('a'):
            stdscr.addstr(15, 0, "Enter new position name: ")
            textwin = curses.newwin(1, 20, 15, 25)
            textpad_obj = textpad.Textbox(textwin)
            stdscr.refresh()
            new_position_name = textpad_obj.edit().strip()
            add_position(new_position_name)
        elif key == ord('e') and selected_position_index != -1:
            stdscr.addstr(
                16, 0, f"Enter new name for position {selected_position_index + 1}: ")
            textwin = curses.newwin(1, 20, 16, 35)
            textpad_obj = textpad.Textbox(textwin)
            stdscr.refresh()
            new_name = textpad_obj.edit().strip()
            edit_position(selected_position_index, new_name)
        elif key == ord('d') and selected_position_index != -1:
            delete_position(selected_position_index)
    elif participants_edit_mode:
        if key >= ord('1') and key <= ord('9'):
            selected_participant_index = key - ord('1')
        elif key == ord('a'):
            stdscr.addstr(15, 0, "Enter new participant name: ")
            textwin = curses.newwin(1, 20, 15, 28)
            textpad_obj = textpad.Textbox(textwin)
            stdscr.refresh()
            new_name = textpad_obj.edit().strip()
            add_person(new_name)
        elif key == ord('e') and selected_participant_index != -1:
            stdscr.addstr(
                16, 0, f"Enter new name for participant {selected_participant_index + 1}: ")
            textwin = curses.newwin(1, 20, 16, 42)
            textpad_obj = textpad.Textbox(textwin)
            stdscr.refresh()
            new_name = textpad_obj.edit().strip()
            edit_person(selected_participant_index, new_name)
        elif key == ord('d') and selected_participant_index != -1:
            remove_person(participants[selected_participant_index])


def draw_screen(stdscr):
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "Positions and Participants:")
        row = 2
        max_col_width = 20
        for idx, position in enumerate(positions):
            col = idx * max_col_width
            stdscr.addstr(row, col, f"{position}:")
            participant_name = participants[idx] if idx < len(
                participants) else "(None)"
            stdscr.addstr(row + 1, col, f"  {participant_name}")
        unassigned = participants[len(positions):]
        if unassigned:
            stdscr.addstr(len(positions) + 4, 0, "Unassigned Participants:")
            for idx, participant_name in enumerate(unassigned):
                stdscr.addstr(len(positions) + 5 + idx,
                              0, f"  {participant_name}")
        stdscr.addstr(len(positions) + 7, 0, f"State: {state}")
        stdscr.addstr(len(positions) + 8, 0, f"Time Elapsed: {time_elapsed}s")
        stdscr.addstr(len(positions) + 9, 0,
                      f"Turn Duration: {turn_duration}s")
        stdscr.addstr(len(positions) + 10, 0,
                      f"Time Left: {max(0, turn_duration - time_elapsed)}s")
        stdscr.addstr(len(positions) + 12, 0,
                      "Press 'q' to quit, 'a' to add participant, 'd' to edit duration")
        stdscr.addstr(len(positions) + 13, 0,
                      "Press 'p' to toggle position edit mode, 'm' to toggle participant edit mode")

        if position_edit_mode:
            stdscr.addstr(len(positions) + 14, 0, "Position Edit Mode: On")
            stdscr.addstr(len(positions) + 15, 0,
                          "Use '1', '2', ... to select, 'a' to add, 'e' to edit, 'd' to delete")

        if participants_edit_mode:
            stdscr.addstr(len(positions) + 14, 0, "Participant Edit Mode: On")
            stdscr.addstr(len(positions) + 15, 0,
                          "Use '1', '2', ... to select, 'a' to add, 'e' to edit, 'd' to delete")

        stdscr.refresh()
        time.sleep(live_view['update_interval'])


def save_session():
    session_data = {
        'session_id': session_id,
        'participants': participants,
        'positions': positions,
        'state': state,
        'time_elapsed': time_elapsed,
        'turn_duration': turn_duration
    }
    with open(f'{session_id}.yml', 'w') as file:
        yaml.dump({'session': session_data}, file)


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    threading.Thread(target=draw_screen, args=(stdscr,), daemon=True).start()
    while True:
        key = stdscr.getch()
        if key != -1:
            handle_input(key, stdscr)
        time.sleep(0.1)


if __name__ == '__main__':
    wrapper(main)
