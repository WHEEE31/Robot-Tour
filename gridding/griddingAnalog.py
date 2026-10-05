import sys
from collections import deque
from functools import lru_cache
import heapq
import pickle
import os

import transfer

class ConsolePathPlanner:
    def __init__(self, grid_size):
        """
        Initialize the path planner with a given grid size
        grid_size: [width, height] of the grid
        """
        self.grid_size = grid_size
        self.directions = [[-1,0], [0,-1], [1,0], [0,1]]  # w, s, e, n
        
        # Core game state
        self.start_point = None
        self.end_point = None
        self.blocks = []
        self.gates = []
        self.target_time = 0
        self.heading = None
        
        # Pathfinding costs
        self.costs = {
            'move': 40,
            'turn': 20,
            'gate': [100, 10000000, 400]  # normal, invalid, last gate bonus
        }
        
        # Grid representation
        self.grid = []
        self.initialize_grid()
        
        # Save file path
        self.savepath = os.path.join('assets', 'console_gridsave.txt')
        self.load_state()

    def initialize_grid(self):
        """Initialize the adjacency list grid"""
        for i in range(self.grid_size[1]):
            row = []
            for j in range(self.grid_size[0]):
                adjacent = []
                for x, y in self.directions:
                    new_x, new_y = j + x, i + y
                    if 0 <= new_x < self.grid_size[0] and 0 <= new_y < self.grid_size[1]:
                        adjacent.append((new_x, new_y))
                row.append(adjacent)
            self.grid.append(row)

    def display_grid(self):
        """Display the current grid state in the console"""
        print("\nCurrent Grid State:")
        print("  " + "".join([f" {i:2}" for i in range(self.grid_size[0])]))
        
        for y in range(self.grid_size[1]):
            print(f"{y:2}", end=" ")
            for x in range(self.grid_size[0]):
                pos = (x, y)
                if pos == self.start_point:
                    print(" S ", end="")
                elif pos == self.end_point:
                    print(" E ", end="")
                elif pos in self.blocks:
                    print(" # ", end="")
                elif pos in self.gates:
                    print(" G ", end="")
                else:
                    print(" . ", end="")
            print()
        print()

    def get_command(self):
        """Get and process user commands"""
        print("\nCommands:")
        print("s <x> <y> - Place start point")
        print("e <x> <y> - Place end point")
        print("b <x> <y> - Place/remove block")
        print("g <x> <y> - Place gate")
        print("t <seconds> - Set target time")
        print("c - Calculate path")
        print("d - Display grid")
        print("r - Reset grid")
        print("q - Quit")
        
        cmd = input("\nEnter command: ").strip().split()
        if not cmd:
            return True
            
        command = cmd[0].lower()
        
        if command == 'q':
            return False
        elif command == 'd':
            self.display_grid()
        elif command == 'r':
            self.reset_grid()
        elif command == 'c':
            self.calculate_path()
        elif command == 't' and len(cmd) == 2:
            try:
                time = int(cmd[1])
                if 55 <= time <= 85:
                    self.target_time = time
                    print(f"Target time set to {time} seconds")
                else:
                    print("Time must be between 55 and 85 seconds")
            except ValueError:
                print("Invalid time value")
        elif len(cmd) == 3:
            try:
                x, y = int(cmd[1]), int(cmd[2])
                if 0 <= x < self.grid_size[0] and 0 <= y < self.grid_size[1]:
                    if command == 's':
                        self.start_point = (x, y)
                        self.heading = self.determine_heading(x, y)
                    elif command == 'e':
                        self.end_point = (x, y)
                    elif command == 'b':
                        if (x, y) in self.blocks:
                            self.blocks.remove((x, y))
                        else:
                            self.blocks.append((x, y))
                    elif command == 'g':
                        if len(self.gates) < 4:
                            self.gates.append((x, y))
                        else:
                            print("Maximum of 4 gates allowed")
                    self.display_grid()
                else:
                    print("Coordinates out of bounds")
            except ValueError:
                print("Invalid coordinates")
        else:
            print("Invalid command")
            
        self.save_state()
        return True

    def determine_heading(self, x, y):
        """Determine initial heading based on start point position"""
        if x == 0:
            return self.directions[0]  # West
        elif x == self.grid_size[0] - 1:
            return self.directions[2]  # East
        elif y == 0:
            return self.directions[1]  # South
        else:
            return self.directions[3]  # North

    def pathfind(self, start, end, start_direction, visited):
        """A* pathfinding algorithm with turn costs and gate handling"""
        directions = [(0, -1), (1, 0), (0, 1), (-1, 0)]  # Up, Right, Down, Left
        
        queue = [(0, start, start_direction)]
        best_cost = {start: 0}
        paths = {start: [start]}
        
        while queue:
            cost, current, current_dir = heapq.heappop(queue)
            if current == end:
                return paths[current], cost, current_dir
                
            for dx, dy in directions:
                next_pos = (current[0] + dx, current[1] + dy)
                if next_pos not in self.grid[current[1]][current[0]] or next_pos in self.blocks:
                    continue
                    
                gate_penalty = 0
                if next_pos == self.gates[-1]:
                    if bin(visited).count('1') != 3:
                        gate_penalty = self.costs['gate'][1]
                        num_visited = bin(visited).count('1')
                        if num_visited == 2:
                            gate_penalty -= self.costs['gate'][2]
                        elif num_visited == 0:
                            gate_penalty += self.costs['gate'][1]
                elif next_pos in self.gates:
                    gate_penalty += self.costs['gate'][0]
                    
                if current_dir == (dx, dy):
                    turn_penalty = 0
                else:
                    diff = abs(directions.index(current_dir) - directions.index((dx, dy)))
                    if diff in [1, 3]:
                        turn_penalty = self.costs['turn']
                    elif diff == 2:
                        turn_penalty = -self.costs['move'] + self.costs['turn'] * 4/3
                        
                total_cost = cost + self.costs['move'] + turn_penalty + gate_penalty
                
                if next_pos not in best_cost or total_cost < best_cost[next_pos]:
                    best_cost[next_pos] = total_cost
                    heapq.heappush(queue, (total_cost, next_pos, (dx, dy)))
                    paths[next_pos] = paths[current] + [next_pos]
                    
        return [], float('inf'), None

    def calculate_path(self):
        """Calculate optimal path through gates to end point"""
        if not all([self.start_point, self.end_point, self.gates, self.target_time]):
            print("Missing required elements (start, end, gates, or target time)")
            return

        @lru_cache(None)
        def dp(current, visited_mask, last_gate_is_golden, dir):
            all_gates_mask = (1 << len(self.gates)) - 1
            
            if visited_mask == all_gates_mask:
                if True:  # last_gate_is_golden
                    try:
                        result = self.pathfind(current, self.end_point, dir, visited_mask)
                        return result[1], result[0]
                    except ValueError:
                        return float('inf'), []
                        
            min_cost = float('inf')
            best_path = []
            
            for i, gate in enumerate(self.gates):
                if visited_mask & (1 << i):
                    continue
                    
                try:
                    path, cost, dir = self.pathfind(current, gate, dir, visited_mask)
                except ValueError:
                    continue
                    
                next_visited_mask = visited_mask | (1 << i)
                is_golden = gate == self.gates[-1]
                
                sub_cost, sub_path = dp(gate, next_visited_mask, last_gate_is_golden or is_golden, dir)
                
                total_cost = cost + sub_cost
                if total_cost < min_cost:
                    min_cost = total_cost
                    best_path = path + sub_path[1:]
                    
            return min_cost, best_path

        total_cost, path = dp(self.start_point, 0, False, tuple(self.heading))
        
        if path:
            print("\nCalculated Path:")
            commands = self.convert_to_commands(path)
            self.save_commands(commands)
            print("\nPath saved to 'queue.txt'")
        else:
            print("No valid path found")

    def convert_to_commands(self, path):
        """Convert coordinate path to robot commands"""
        commands = ["ENTER"]
        current_heading = self.heading
        
        for i in range(1, len(path)):
            prev = path[i-1]
            current = path[i]
            movement = [prev[0]-current[0], prev[1]-current[1]]
            
            new_heading_idx = self.directions.index(movement)
            current_heading_idx = self.directions.index(current_heading)
            
            # Handle turning
            if abs(new_heading_idx - current_heading_idx) == 2:
                if i >= 2 and path[i-2] == current:
                    commands.pop()
                    commands.append('BUMP')
                else:
                    commands.extend(['RIGHT', 'RIGHT'])
            elif (new_heading_idx - current_heading_idx) % 4 == 1:
                commands.append('RIGHT')
            elif (new_heading_idx - current_heading_idx) % 4 == 3:
                commands.append('LEFT')
                
            if not (i >= 2 and path[i-2] == current):
                commands.append('FORWARD')
                current_heading = movement
                
        commands.append("EXIT")
        return commands

    def save_commands(self, commands):
        """Save commands to queue.txt"""
        output = [f"targetTime = {self.target_time}"]
        command_str = "queue = ["
        
        for i, cmd in enumerate(commands):
            if i == 0:
                command_str += f'"{cmd}"'
            else:
                command_str += f',\n        "{cmd}"'
        command_str += "]"
        
        output.append(command_str)
        
        with open('queue.txt', 'w') as f:
            f.write('\n'.join(output))
        
        # transfer output to main.py
        transfer.transfer()

    def save_state(self):
        """Save current grid state"""
        state = [
            self.target_time,
            self.start_point,
            self.end_point,
            self.blocks,
            self.gates
        ]
        with open(self.savepath, 'wb') as f:
            pickle.dump(state, f)

    def load_state(self):
        """Load saved grid state"""
        if os.path.exists(self.savepath) and os.path.getsize(self.savepath) > 0:
            try:
                with open(self.savepath, 'rb') as f:
                    state = pickle.load(f)
                    self.target_time = state[0]
                    self.start_point = state[1]
                    self.end_point = state[2]
                    self.blocks = state[3]
                    self.gates = state[4]
                    if self.start_point:
                        self.heading = self.determine_heading(*self.start_point)
            except:
                print("Error loading saved state")

    def reset_grid(self):
        """Reset the grid to initial state"""
        self.start_point = None
        self.end_point = None
        self.blocks = []
        self.gates = []
        self.target_time = 0
        self.heading = None
        self.save_state()
        self.display_grid()

def main():
    planner = ConsolePathPlanner([5, 4])
    print("Welcome to Console Robot Path Planner!")
    planner.display_grid()
    
    running = True
    while running:
        running = planner.get_command()

if __name__ == "__main__":
    main()