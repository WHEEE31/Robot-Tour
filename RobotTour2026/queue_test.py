import random

queue = []
for i in range(16):
    queue.append(["LEFT", "RIGHT"][random.randint(0,1)])
targetTime = 5

queue = ['ENTER',
         'RIGHT',
         'FORWARD',
         'LEFT',
         'FORWARD',
         'RIGHT',
         'BACKBUMP',
         'LEFT',
         'FORWARD',
         'BUMP',
         'LEFT',
         'FORWARD2',
         'LEFT',
         'FORWARD',
         'RIGHT',
         'FORWARD',
         'LEFT',
         'BUMP',
         'LEFT',
         'FORWARD',
         'LEFT',
         'FORWARD',
         'LEFT',
         'FORWARD',
         'RIGHT',
         'FORWARD2',
         'RIGHT',
         'FORWARD',
         'RIGHT',
         'FORWARD',
         'MINIBUMP',
         'LEFT',
         'FORWARD',
         'RIGHT',
         'FORWARD',
         'EXIT']
targetTime = 72

counts = [0,0,0,0,0,0,0,0,0]
for i,step in enumerate(queue):
    print(f'\r#{i}: "{step}"', end = '')
    if step not in ['FORWARD', 'FORWARD2', 'FORWARD3', 'FORWARD4', 'BACKWARD', 
                       'BUMP', 'MINIBUMP', 'BACKBUMP', 'ENTER', 'EXIT', 'LEFT', 'RIGHT',
                       'RAISE', 'LOWER', 'ALIGN', 'CALIBRATE']:
        print(' (???)', end = '')
    print('', end = '')
    if step == "FORWARD":
        counts[0] += 1
    elif step == "FORWARD2":
        counts[0] += 2
    elif step == "FORWARD3":
        counts[0] += 3
    elif step == "FORWARD4":
        counts[0] += 4
    elif step == "BACKWARD":
        counts[0] += 1
    elif step == "BUMP":
        counts[1] += 1
    elif step == "MINIBUMP":
        counts[2] += 1
    elif step == "BACKBUMP":
        counts[3] += 1

    elif step == "ENTER":
        counts[4] += 1
    elif step == "EXIT":
        counts[5] += 1

    elif step == "LEFT":
        counts[6] += 1
    elif step == "RIGHT":
        counts[6] += 1

    elif step == "RAISE":
        counts[7] += 1
    elif step == "LOWER":
        counts[8] += 1
    elif step == "ALIGN":
        counts[9] += 1
    elif step == "CALIBRATE":
        pass
    
    input('')
print(counts)