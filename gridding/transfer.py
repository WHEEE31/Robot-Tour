"""

Purpose is to transfer the queue saved from gridding.py 
into main.py of the actual tour

"""

import os
import re

def transfer():
    #print("transfer called")
    # Define paths
    queue_txt_path = os.path.join("assets", "queue.txt")
    main_py_path = os.path.join("..", "RobotTour2025", "main.py")

    # Read the targetTime and queue from queue.txt
    with open(queue_txt_path, "r") as file:
        queue_txt_content = file.read()

    # Extract targetTime using regex
    target_time_match = re.search(r"targetTime\s*=\s*([\d.]+)", queue_txt_content)
    if not target_time_match:
        raise ValueError("Could not find targetTime in queue.txt")
    target_time = target_time_match.group(1)

    # Extract queue (multiline list) using regex
    queue_match = re.search(r"queue\s*=\s*\[([\s\S]*?)\]", queue_txt_content)
    if not queue_match:
        raise ValueError("Could not find queue in queue.txt")
    queue_content = queue_match.group(1).strip()

    # Format the queue content as a multiline string
    queue_lines = [line.strip() for line in queue_content.splitlines() if line.strip()]
    queue_formatted = "[" + "\n".join(f'        {line}' for line in queue_lines) + "]"

    # Read the main.py file
    with open(main_py_path, "r") as file:
        main_py_content = file.read()

    # Replace targetTime in main.py using regex
    main_py_content = re.sub(
        r"targetTime\s*=\s*[\d.]+", 
        f"targetTime = {target_time}", 
        main_py_content
    )

    # Replace queue in main.py using regex
    main_py_content = re.sub(
        r"queue\s*=\s*\[[\s\S]*?\]", 
        f"queue = {queue_formatted}", 
        main_py_content
    )

    # Write the updated content back to main.py
    with open(main_py_path, "w") as file:
        file.write(main_py_content)

    #print("main.py has been updated with the values from queue.txt.")