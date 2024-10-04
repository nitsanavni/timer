@./timer.py

File "/Users/nitsanavni/code/timer/timer.py", line 212, in handle_input
    elif key == ord(actions.get('add_position', 'pa')):
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: ord() expected a character, but string of length 2 found


---

let's add in memory state
'p' -> positions edit mode
if position_edit_mode:
  \d -> pos_num = d
  a -> position add
  e -> position edit (d)
  d -> position delete (d)
