import sys
sys.setrecursionlimit(10000)
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = 'hide'
import pygame
import pickle
#import cv2
#from PIL import Image
import ctypes
import time
from collections import deque
from functools import lru_cache
import heapq
import builtins
import threading
from queue import Queue

import transfer

#####################################################################################
#####################################################################################
#####################################################################################
class Background:
    def __init__(self, screen, display_type):
        """
        Background.__init__(screen, display_type = 'color') --> None
            handles the window's background
            screen (pygame.Display) - the Pygame screen
            display_type (string) {'color', 'video'} ('color') - type of background
        """
        self.screen = screen
        self.display_type = display_type

        # console stuff
        self.queue = Queue()
        self.displayQueue = []
        self.font = pygame.font.Font("CascadiaCode.ttf", 15)

        self.defaultLengths = [100,-100]
        self.linePad = [25, 15]     # normal, /n newline
        self.fontColor = [(200,200,200)] * 20

        self.original = builtins.print
        builtins.print = custom_disp
        
        # color stuff
        if display_type == 'color':
            self.color = [0,0,0]
            self.maxes = [30,30,30]
            self.rates = [0.1,0.2,0.3]

    def update(self):
        """
        Background.update() --> None
            updates the background depending on the display type initialized
        """

        if self.display_type == 'color':
            self.screen.fill(self.color)
            for i, val in enumerate(self.color):
                new = val + self.rates[i]
                if new > self.maxes[i] or new < 0:
                    self.rates[i] *= -1
                    new += self.rates[i]
                self.color[i] = new
        else:
            self.screen.fill((0,0,0, 125))

        while not self.queue.empty():
            msg, timing = self.queue.get()
            if (len(self.displayQueue) > 0 and msg == self.displayQueue[-1]['msg']):
                pass
            else:
                self.displayQueue.append({"msg" : msg, "counter" : 0, "max" : timing})

        for i in range(min(len(self.displayQueue)-1,len(self.fontColor)-1), -1, -1):
            lines = self.displayQueue[i]['msg'].splitlines()
            for j, line in enumerate(lines):
                self.screen.blit(self.font.render(f'{line}', True, self.fontColor[i]), (10, 10 + self.linePad[0]*i + self.linePad[1]*j))
            self.displayQueue[i]['counter'] = self.displayQueue[i]['counter'] + 1
            if self.displayQueue[i]['counter'] >= (self.displayQueue[i]['max'] if self.displayQueue[i]['max'] != self.defaultLengths[1] else self.defaultLengths[0]):
                self.displayQueue.pop(i)

    def clear_cache(self):
        while not self.queue.empty(): self.queue.get()
        self.displayQueue = []

class Cursor:
    def __init__(self, screen):
        """
        Cursor.__init__(screen) --> None
            creates a new Cursor
            screen (pygame.Display) - the Pygame screen
        """
        self.screen = screen
        self.coords = [0, 0]     
        self.state = ["cursor", False, None]
        self.mouseDown = False

        self.size = 20
        self.colors = [(100,0,0), (255,100,100)]

        self.movementBuffer = 0.2
        self.update()

    def update(self):
        """
        Cursor.update() --> None
            updates cursor x,y; displays cursor
        """
        userCoords = pygame.mouse.get_pos()
        move = [(userCoords[0] - self.coords[0]) * self.movementBuffer,
                (userCoords[1] - self.coords[1]) * self.movementBuffer]
        self.coords = [self.coords[0] + move[0],
                       self.coords[1] + move[1]]

        #print(f'Current cursor coords: [{int(self.coords[0])},{int(self.coords[1])}]', end = '     \r')

        color = self.colors[1] if self.mouseDown else self.colors[0]
        pygame.draw.circle(self.screen, color, (int(self.coords[0]), int(self.coords[1])), self.size//2)
        #self.screen.blit(self.currentImage, (self.coords[0]-self.currentImage.get_size()[0]/2, self.coords[1]-self.currentImage.get_size()[1]/2))

    def is_click_valid(self, object):
        """
        Cursor.is_click_valid(object) --> bool
            checks if the object can be clicked by the cursor
            object - some object
        """
        if self.coords[0] < object.get_hitbox(0) or self.coords[0] > object.get_hitbox(1) or self.coords[1] < object.get_hitbox(2) or self.coords[1] > object.get_hitbox(3):
            return False
        if object.get_state(2) == "menu" or self.state[2] == None:
            return True
        if object.get_state(2) == None:
            if object.state[0] == "gridsegment":
                return self.state[2].state[0] == "start_point" or self.state[2].state[0] == "block" or self.state[2].state[0] == "bottle"
            elif object.state[0] == "gridsquare":
                return self.state[2].state[0] == "end_point" or self.state[2].state[0] == "gate"

    def click(self, object):
        """
        Cursor.click(object) --> None
            clicks the object and updates cursor accordingly
        """
        if self.is_click_valid(object):
            object.click(self)
        else:
            self.set_state(False)

    def set_state(self, thing):
        """
        Cursor.set_state(thing) --> None
            sets the cursor's state
            thing (bool) - if the cursor is clicked
        """
        if isinstance(thing, bool):
            self.state[1] = thing
            self.mouseDown = thing
        elif thing == None or isinstance(thing, object):
            if self.state[2]: self.state[2].delete()
            self.state[2] = thing

    def get_coords(self):
        """
        Cursor.get_coords() --> list
            returns the cursor's coords
        """
        return self.coords

#####################################################################################
#####################################################################################
#####################################################################################
class Sprite:
    objects = []

    def __init__(self, screen, box, type, priority, gridLocation = [0,0], buffer = 0):
        """
        Sprite.__init__(screen, box, type, priority, gridLocation = [0,0], buffer=0) --> creates a new Sprite object
            screen (pygame.Display) - the Pygame screen
            box (list) - [coords.x, coords.y, width, height]
            type (str) - identification tag
                note: used for loading images ('type.png')
            priority (int) {1,2,3} - order of displaying objects
                ex: objects w/ priority 1 are blitted before (under) objects w/ priority 3
            gridLocation (list) [0,0] - location of object within grid
            buffer (int) (=0) - padding around the image within the hitbox
        """
        self.screen = screen

        self.buffer = buffer
        self.dims = [box[2], box[3]]
        self.coords = []
        self.hitbox = []
        self.set_coords([box[0],box[1]])
        self.gridLocation = gridLocation

        paths = [type, type+'_hover']
        self.images = [pygame.transform.smoothscale(pygame.image.load(os.path.join(ROOT, path+'.png')).convert_alpha(), self.dims) for path in paths]
        self.currentImage = self.images[0]

        self.state = [type, False, None]
        self.priority = priority

        Sprite.objects.append(self)
    
    def __str__(self):
        #return f'{self.state[0]} object at {self.coords}. Clicked? {self.state[1]}. Contains: {self.state[2]}'
        return f'{self.state} at {self.coords}, {self.gridLocation}'

    def get_coords(self):
        """
        Sprite.get_coords() --> list
            returns the object's coordinates [x,y]
        """
        return self.coords
    
    def set_coords(self, coords):
        """
        Sprite.set_coords(coords) --> None
            coords (list) - new coordinates
            sets object's coordinates to coords and updates hitbox
        """
        self.coords = coords
        self.hitbox = [self.coords[0]-self.buffer,self.coords[0]+self.dims[0]+self.buffer,self.coords[1]-self.buffer,self.coords[1]+self.dims[1]+self.buffer]

    def get_state(self, index=-1):
        """
        Sprite.get_state(index=-1) --> list
            returns object's state
                [type, clicked?, container object]
            index (int) (-1) - specific index of state
        """
        if index == -1:
            return self.state
        return self.state[index]
    
    def set_state(self, state):
        """
        Sprite.set_state(state) --> None
            state (list) - new state
                can be a string: updates type
                can be a boolean: updates clicked?
                can be a whole list: 
                    has two elements: updates just clicked? and container object
                    has three elements: updates all vars
        """
        if isinstance(state, str):
            self.state[0] = state
        elif isinstance(state, bool):
            self.state[1] = state
        elif isinstance(state, list):
            self.state = state if len(state) == 3 else [self.state[0]]+state

    def get_hitbox(self, index):
        """
        Sprite.get_hitbox(index) --> list
            returns the object's hitbox [x,y, width, height]
            index (int) - the specific element of the hitbox
        """
        return self.hitbox[index]

    def get_gridloc(self):
        """
        Sprite.get_gridloc() --> list
            returns the gridlocation of the object
        """
        return self.gridLocation
    
    def get_priority(self):
        """
        Sprite.get_priority() --> int
            returns the priority of the object
        """
        return self.priority

    def delete(self):
        """
        Sprite.delete() --> None
            deletes the current object (isn't updating)
        """
        for i,o in enumerate(Sprite.objects):
            if o == self:
                Sprite.objects.pop(i)
                break

    def update(self):
        """
        Sprite.update() --> None
            updates the object's current image
        """
        # update sprite object in game canvas
        if self.state[1] == True:
            self.currentImage = self.images[1]
        else:
            self.currentImage = self.images[0]
        self.screen.blit(self.currentImage, self.coords)

        if self.state[2] and not isinstance(self.state[2], str):
            self.state[2].update()

    def click(self, cursor):
        """
        Sprite.click(cursor) --> None
            cursor (Cursor) - the cursor
            updates the object based on the cursor
        """
        if self.state[2] == None:
            if cursor.state[2] != None:
                self.state[2] = cursor.state[2].copy(self.coords + self.dims, self.gridLocation)
                cursor.state[2] = None
        else:
            self.state[2].delete()
            self.state[2] = None

    def reset(self):
        """
        Sprite.reset() --> None
            resets the sprite (deletes any menuitems within it if necessary)
        """
        if self.state[2] and not isinstance(self.state[2], str):
            self.state[2].delete()
            self.state[2] = None

class DirectionalSprite(Sprite):
    def __init__(self, screen, box, type, direction, priority, gridLocation = [0,0], buffer = 0):
        """
        DirectionalSprite.__init__(screen, box, type, direction, priority, buffer=0) --> creates a new Sprite object
            screen (pygame.Display) - the Pygame screen
            box (list) - [coords.x, coords.y, width, height]
            type (str) - identification tag
                note: used for loading images ('type.png')
            direction (str) {'vertical', 'horizontal'} - object orientation
            priority (int) {1,2,3} - order of displaying objects
                ex: objects w/ priority 1 are blitted before (under) objects w/ priority 3
            gridLocation (list) [0,0] - location of object within grid
            buffer (int) (=0) - padding around the image within the hitbox
        """
        self.direction = direction
        super().__init__(screen, box, type+'_'+self.direction, priority, gridLocation, buffer)
        self.state[0] = type

    def get_direction(self):
        """
        DirectionalSprite.get_direction() --> str
            returns object's orientation
        """
        return self.direction
    
    def rotate(self):
        """
        DirectionalSprite.rotate() --> None
            rotates the object
                ensure the images are in type_{direction}
        """
        if self.direction == 'vertical':
            self.direction = 'horizontal'
        else:
            self.direction = 'vertical'
        
        paths = [self.state[0]+'_'+self.direction, self.state[0]+'_'+self.direction+'_hover']
        self.dims = [self.dims[1], self.dims[0]]
        self.coords = [self.coords[0] + (self.dims[1]-self.dims[0])/2, self.coords[1] + (self.dims[0]-self.dims[1])/2]
        self.images = [pygame.transform.smoothscale(pygame.image.load(os.path.join(ROOT, path+'.png')).convert_alpha(), self.dims) for path in paths]
        self.set_coords(self.coords)

class MenuItem(DirectionalSprite, Sprite):
    def __init__(self, screen, coords, sizes, type, priority, gridLocation = None, direction = None):
        """
        MenuItem(DirectionalSprite, Sprite).__init__(screen, coords, sizes, type, priority, gridLocation = None, direction = None) --> new MenuItem object
            screen (pygame.Display) - the Pygame screen
            coords (list) - the coords at which the item will be displayed
            sizes (dictionary) - the sizes of all menuitem types (from the gridding engine)
            type (str) - identification tag
                note: used for loading images ('type.png')
            priority (int) {1,2,3} - order of displaying objects
                ex: objects w/ priority 1 are blitted before (under) objects w/ priority 3
            gridLocation (list) None - location of object within grid
            direction (str) {'vertical', 'horizontal'} None - object orientation
        """
        box = coords + sizes[type[0]][type[1]]
        self.box = box
        self.sizes = sizes
        if not direction:
            self.direction = None
            Sprite.__init__(self, screen, box, type[0], priority, gridLocation = gridLocation)
        else:
            DirectionalSprite.__init__(self, screen, box, type[0], 'horizontal', priority, gridLocation)
            if direction == 'vertical':
                self.rotate()
        self.state[2] = type[1]
        self.ttmp = priority
        self.normalGateImg = self.images[0]
        self.lastGateImg = pygame.transform.smoothscale(pygame.image.load(os.path.join(ROOT, 'gate_last.png')).convert_alpha(), self.dims)

    def update(self):
        """
        MenuItem.update() --> None
        updates the MenuItem based on where it is (e.g. menu, board, carrying)
        """
        super().update()
        global g
        if self.state[2] == 'carrying':
            cursor = g.cursor
            if cursor.state[2] == None:
                self.delete()
            self.priority = g.layers["cursor"]
            self.coords = [cursor.get_coords()[0]+10, cursor.get_coords()[1]+10]
        elif self.state[2] == 'board' and self.state[0] == 'gate':
            count = 0
            indices = []
            idx = 0
            for i, o in enumerate(Sprite.objects):
                if o.state[0] == 'gate' and o.state[2] == 'board':
                    count += 1
                    indices.append(i)
                    if o == self:
                        idx = i
            if LASTGATEMECHANIC and count == g.gateCount and indices[g.gateCount-1] == idx:
                self.images[0] = self.lastGateImg
            else:
                self.images[0] = self.normalGateImg

    def click(self, cursor):
        """
        MenuItem.click(cursor) --> None
            cursor (Cursor) - the cursor
            updates the object based on the cursor
        """
        if self.state[2] == 'menu':
            if cursor.state[2] != None:
                cursor.state[2].delete()
            cursor.set_state(self.copy())
            self.state[1] = True
        else:
            super().click(cursor)

    def copy(self, target = [0,0,0,0], gridLocation = [0,0]):
        """
        MenuItem.copy(target = [0,0,0,0], gridLocation = [0,0]) --> MenuItem()
            target [0,0,0,0] --> box of the target thing (if applicable - if being clicked onto the board)
            gridLocation [0,0] --> gridlocation of the target thing (again, if applicable)

            creates a new MenuItem object in another location
        """
        self.priority = self.ttmp
        if self.state[2] == 'menu':
            d = 'horizontal' if self.state[0] == 'block' else None
            return MenuItem(self.screen, self.coords, self.sizes, [self.state[0],'carrying'], self.priority, gridLocation = None, direction = d)
        elif self.state[2] == 'carrying':
            dims = self.sizes[self.state[0]]['board']
            buf = 0 if self.state[0] == 'bottle' else 5
            point = [x+buf for x in target[:2]]+[x-buf for x in target[2:]]
            coords = [point[0] + (point[2]-dims[0])/2, point[1] + (point[3]-dims[1])/2]
            d = None if self.state[0] != 'block' else ('horizontal' if target[2] > target[3] else 'vertical')
            return MenuItem(self.screen, coords, self.sizes, [self.state[0], 'board'], self.priority, gridLocation, d)

class DialogueBox:
    def __init__(self, screen, box):
        """
        DialogueBox.__init__(screen, box) --> None
            screen (pygame.Display) - the Pygame screen
            box (list) - [coords.x, coords.y, width, height]

            creates a new DialogueBox object
        """
        self.screen = screen
        self.colors = [(200,200,200), (0,0,255), (0,0,100)]
        self.box = pygame.Rect(box[0], box[1], box[2], box[3])

        self.font_size = 24
        self.font = pygame.font.SysFont("monospace", self.font_size)
        self.default_text = 'Target Time'
        self.text = ''
        self.toPrint = self.font.render(self.text, True, (0,0,0))

        self.state = ["input_box", False, 0]
        
    def update(self, cursor):
        """
        DialogueBox.update(cursor) --> None
            updates the DialogueBox
            cursor (Cursor) - the cursor object
        """

        if self.state[1] == True:
            currentColor = self.colors[1]
        elif self.box.collidepoint(cursor.get_coords()):
            currentColor = self.colors[2]
        else:
            currentColor = self.colors[0]

        if self.text == '' and self.state[1] == False:
            self.toPrint = self.font.render(self.default_text, True, (100,100,100))
        else:
            self.toPrint = self.font.render(self.text, True, (0,0,0))

        pygame.draw.rect(self.screen, currentColor, self.box, 2)
        self.screen.blit(self.toPrint, (self.box.x + 5,self.box.y + (self.box.h-self.font_size)/2))

    def click(self, cursor):
        """
        DialogueBox.click(cursor) --> None
            updates the DialogueBox with cursor click
            different from other objects'.. needs to run constantly
        """
        if self.box.collidepoint(cursor.get_coords()):
            self.state[1] = not self.state[1]
        else:
            self.state[1] = False
            if str(self.state[2]) != self.text:
                self.text = ''

    def type(self, event):
        """
        DialogueBox.type(event) --> None
            updates the box!!!!!!
        """
        if self.state[1] == True:
            if event.key == pygame.K_RETURN:
                if self.text.isdigit() and int(self.text) >= 55 and int(self.text) <= 85:             # CHECK FOR CORRECT TIME
                    print(f'Saved input: {self.text} seconds')
                    self.state[2] = int(self.text)
                else:
                    self.text = ''
                    print("Invalid input", end = '                                                                                   \r')
                self.state[1] = False
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]  # Remove last character
            else:
                self.text += event.unicode  # Add the typed character

    def set_state(self, num):
        """
        DialogueBox.set_state(num) --> None
            num (int) --> new stored number
            sets the stored number of the dialogue box
        """
        self.state[2] = num
        self.text = str(self.state[2])

    def reset(self):
        """
        DialogueBox.reset() --> None
            resets the dialogue box (for the rest func)
        """
        self.state[2] = 0
        self.text = ''

    def get_state(self, index):
        """
        DialogueBox.get_state(index) --> int
            returns the stored number of the dialogue box
        """
        return self.state[index]
    
class Button:
    def __init__(self, screen, box, id, toggled=False, glint=False):
        self.screen = screen
        self.box = box      # x, y, width, height
        self.hitbox = pygame.Rect(self.box)
        self.state = [id, False]
        
        self.id = id
        self.toggled = toggled  # if the button is a toggle button, True.
        self.glint = glint
        self.imgs = []

        if self.toggled:
            self.imgs = [pygame.transform.smoothscale(pygame.image.load(os.path.join(ROOT, f'{id}_false.png')).convert_alpha(), (self.box[2], self.box[3])),
                         pygame.transform.smoothscale(pygame.image.load(os.path.join(ROOT, f'{id}_true.png')).convert_alpha(), (self.box[2], self.box[3]))]
            self.justToggled = False
        else:
            self.imgs = [pygame.transform.smoothscale(pygame.image.load(os.path.join(ROOT, f'{id}.png')).convert_alpha(), (self.box[2], self.box[3])),
                         pygame.transform.smoothscale(pygame.image.load(os.path.join(ROOT, f'{id}_hover.png')).convert_alpha(), (self.box[2], self.box[3]))]
            
        if self.glint:
            self.glintImg = pygame.transform.smoothscale(pygame.image.load(os.path.join(ROOT, 'glint.png')).convert_alpha(), (self.box[2]+10, self.box[2]+10))
            self.glintOffsetX, self.glintOffsetY = 0, 0
            
            self.scrollSpeedX = -0.002
            self.scrollSpeedY = 0.0015
            
    def update(self, cursor):
        imgIdx = 0
        if self.hitbox.collidepoint(cursor.get_coords()):
            if self.toggled:
                if self.justToggled:
                    imgIdx = 1 if self.state[1] else 0
                else:
                    imgIdx = 0 if self.state[1] else 1
            else:
                imgIdx = 1
        else:
            if self.toggled and self.justToggled:
                self.justToggled = False
            imgIdx = 1 if self.state[1] else 0

        self.screen.blit(self.imgs[imgIdx], (self.box[0], self.box[1]))

        # manage glint
        if self.glint:
            self.glintOffsetX = (self.glintOffsetX + self.scrollSpeedX) % 1.0
            self.glintOffsetY = (self.glintOffsetY + self.scrollSpeedY) % 1.0
            pixel_offset_x = int(self.glintOffsetX * self.glintImg.get_width() * 2)
            pixel_offset_y = int(self.glintOffsetY * self.glintImg.get_height() * 2)

            glint_surf = pygame.Surface((self.box[2], self.box[3]), pygame.SRCALPHA)
            x = -pixel_offset_x
            while x > 0:
                x -= self.glintImg.get_width()
            y = -pixel_offset_y
            while y > 0:
                y -= self.glintImg.get_height()

            start_x = x
            for ty in range(y, int(self.box[3]), int(self.glintImg.get_height())):
                for tx in range(start_x, int(self.box[2]), int(self.glintImg.get_width())):
                    glint_surf.blit(self.glintImg, (tx, ty))

            button_img = self.imgs[imgIdx]
            glint_surf.blit(button_img, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(glint_surf, (self.box[0], self.box[1]), special_flags=pygame.BLEND_ADD)

    def click(self, cursor):
        if self.hitbox.collidepoint(cursor.get_coords()):
            if self.toggled:
                self.state[1] = not self.state[1]
                self.justToggled = True
            else:
                self.state[1] = True

    def set_state(self, boolean):
        self.state[1] = boolean

    def get_state(self):
        return self.state[1]

class GriddingEngine:
    def __init__(self, screen):
        """
        GriddingEngine.__init__(screen, grid_size) --> new GriddingEngine object
            screen (pygame.Display) - the Pygame screen
            grid_size (list) - the size of the grid in cells (length x width)
                right now it should be [5,4]

            handles gridding
        """
        self.screen = screen

        # window params
        self.windowBuffer = 100
        self.running = True
        self.keybinds = {"quit" : pygame.K_q,
                         "reset" : pygame.K_r,
                         "start_point" : pygame.K_s,
                         "end_point" : pygame.K_e,
                         "block" : pygame.K_w,
                         "gate": pygame.K_g,
                         "bottle" : pygame.K_b}
        self.layers = {"bg" : 0,
                       "cursor" : 5,
                       "gridsquare" : 1,
                       "gridsegment" : 3,
                       "menubg" : 1,
                       "menu_input" : 2,
                       "menu_buttons" : 2,
                       "start_point" : 4,
                       "end_point" : 2,
                       "block" : 4,
                       "gate" : 2,
                       "bottle" : 4}
        self.stats = []
        self.gateCount = NUMGATES
        self.bottleCount = NUMBOTTLES
        self.blockCount = NUMOBSTACLES

        print("----KEYBINDS----")
        for key in self.keybinds:
            print(f"{key}: {pygame.key.name(self.keybinds[key])}")
        print()

        # grid params
        self.gridSize = BOARDSIZE
        self.cellWidth = 150

        # grid init
        width,height = self.gridSize[0]*self.cellWidth, self.gridSize[1]*self.cellWidth
        self.gridBox = [self.windowBuffer,        # halfway between left window border and left menu border
                        (self.screen.get_height()-height)/2, width, height]
        self.outsideSegments = []
        for x in range(self.gridSize[0]*2+1):
            for y in range(self.gridSize[1]*2+1):
                if (x+y) % 2 == 1:
                    direction = ['vertical', 'horizontal'][x%2]
                    dims = {'vertical':[5,self.cellWidth], 'horizontal':[self.cellWidth,5]}[direction]
                    box = [self.gridBox[0]+x//2*self.cellWidth, self.gridBox[1]+y//2*self.cellWidth] + dims
                    DirectionalSprite(self.screen, box, "gridsegment", direction, self.layers["gridsegment"], [x,y], 35)
                    if (x==0 or y==0 or x==self.gridSize[0]*2 or y==self.gridSize[1]*2):
                        self.outsideSegments.append((x,y))
        for x in range(self.gridSize[0]):
            for y in range(self.gridSize[1]):
                Sprite(self.screen, [self.gridBox[0]+x*self.cellWidth, self.gridBox[1]+y*self.cellWidth, self.cellWidth, self.cellWidth], "gridsquare", self.layers["gridsquare"], [x,y])

        # menu params
        self.menuWidth = self.screen.get_width()-(self.gridBox[0]+self.gridBox[2]+self.windowBuffer*2)
        self.menuBuffer = self.windowBuffer/2
        self.sizes = {'start_point' : {'carrying' : [40,40], 'board': [0.3*self.cellWidth,0.3*self.cellWidth], 'menu': [0.15*self.menuWidth,0.15*self.menuWidth]},
                      'end_point' : {'carrying' : [40,40], 'board': [0.3*self.cellWidth,0.3*self.cellWidth], 'menu': [0.15*self.menuWidth,0.15*self.menuWidth]},
                      'block': {'carrying' : [80,16], 'board': [0.8*self.cellWidth,15], 'menu': [0.5*self.menuWidth,0.1*self.menuWidth]},
                      'gate': {'carrying' : [80,80], 'board': [0.98*self.cellWidth,0.98*self.cellWidth], 'menu': [0.5*self.menuWidth,0.5*self.menuWidth]},
                      'bottle': {'carrying' : [60,60], 'board': [0.6*self.cellWidth,0.6*self.cellWidth], 'menu': [0.25*self.menuWidth,0.25*self.menuWidth]}}

        # menu init
        self.menuBox = [self.gridBox[0]+self.gridBox[2]+self.windowBuffer,
                        (self.screen.get_height()-self.cellWidth*self.gridSize[1])/2+5, 
                        self.menuWidth, self.cellWidth*self.gridSize[1]-5]
        self.menuBG = pygame.Rect(self.menuBox)
        self.font = pygame.font.Font('CascadiaCode.ttf', 45)
        self.menuHeading = self.font.render('Actions ', False, (0,0,0))
        MenuItem(self.screen, [self.menuBox[0]+self.menuBox[2]-self.menuBuffer-40, self.menuBox[1]+91], self.sizes, ['start_point', 'menu'], self.layers["start_point"])
        MenuItem(self.screen, [self.menuBox[0]+self.menuBox[2]-self.menuBuffer-40, self.menuBox[1]+161], self.sizes, ['end_point', 'menu'], self.layers["end_point"])
        MenuItem(self.screen, [self.menuBox[0]+self.menuBox[2]-self.menuBuffer-58, self.menuBox[1]+244], self.sizes, ['bottle', 'menu'], self.layers["bottle"])
        MenuItem(self.screen, [self.menuBox[0]+self.menuBuffer, self.menuBox[1]+100], self.sizes, ['block', 'menu'], self.layers["block"], gridLocation = None, direction = 'horizontal')
        MenuItem(self.screen, [self.menuBox[0]+self.menuBuffer, self.menuBox[1]+155], self.sizes, ['gate', 'menu'], self.layers["gate"])

        height = 50; buffer = 11; cull = 8
        self.inputBox = DialogueBox(self.screen, [self.menuBox[0] + self.menuBuffer, 
                                                  self.menuBox[1] + self.menuBox[3] - self.menuBuffer - buffer*2 - height*2 - (height-cull),
                                                  self.menuBox[2] - self.menuBuffer*2, height-cull])
        self.btnToggle = Button(self.screen, [self.menuBox[0] + self.menuBuffer, 
                                              self.menuBox[1] + self.menuBox[3] - (height+self.menuBuffer) - (height+buffer)*1,
                                              (self.menuBox[2] - buffer - self.menuBuffer*2)/2, height], 'toggle', toggled=True)
        self.btnReset = Button(self.screen, [self.menuBox[0] + self.menuBox[2] - (self.menuBox[2] - buffer - self.menuBuffer*2)/2 - self.menuBuffer,
                                             self.menuBox[1] + self.menuBox[3] - (height+self.menuBuffer) - (height+buffer)*1,
                                             (self.menuBox[2] - buffer - self.menuBuffer*2)/2, height], 'reset')
        self.btnRand = Button(self.screen, [self.menuBox[0] + self.menuBuffer,
                                            self.menuBox[1] + self.menuBox[3] - (height+self.menuBuffer),
                                            self.menuBox[2] - self.menuBuffer*2, height], 'rand')
        factor = 2.5
        self.btnCalc = Button(self.screen, [(self.menuBox[2]-725/factor)/2+self.menuBox[0], 10, 725/factor, 212/factor], 'calc', glint=True)
        
        # cursor init
        self.cursor = Cursor(screen)
        self.saveHandling = [0, 10]

        # load previous setup if it exists
        self.savepath = os.path.join(ROOT, 'gridsave.txt')
        if os.path.getsize(self.savepath) == 0:
            with open(self.savepath, 'wb') as file: pickle.dump(self.stats, file)
        with open(self.savepath, 'rb') as file:
            saveData = pickle.load(file)
            if saveData[0] != 0:
                self.inputBox.set_state(saveData[0])
            if len(saveData) == 5:
                saveData.append([])
            for o in Sprite.objects:
                found = True
                if o.get_gridloc() == saveData[1] and o.state[0] == 'gridsegment':
                    self.cursor.set_state(MenuItem(screen, [1210,145], self.sizes, ["start_point", "carrying"], self.layers["start_point"]))
                elif o.get_gridloc() == saveData[2] and o.state[0] == 'gridsquare':
                    self.cursor.set_state(MenuItem(screen, [1210,145], self.sizes, ["end_point", "carrying"], self.layers["end_point"]))
                elif o.get_gridloc() in saveData[3] and o.state[0] == 'gridsegment':
                    self.cursor.set_state(MenuItem(screen, [1210,160], self.sizes, ["block", "carrying"], self.layers["block"], gridLocation = None, direction = 'horizontal'))
                elif o.get_gridloc() in saveData[4] and o.state[0] == 'gridsquare':
                    self.cursor.set_state(MenuItem(screen, [1210,130], self.sizes, ["gate", "carrying"], self.layers["gate"]))
                elif o.get_gridloc() in saveData[5] and o.state[0] == 'gridsegment':
                    self.cursor.set_state(MenuItem(screen, [1210,145], self.sizes, ["bottle", "carrying"], self.layers["bottle"]))
                else:
                    found = False
                if found:
                    o.click(self.cursor)
            for coords in saveData[4]:
                if len(coords) == 3:
                    for o in Sprite.objects:
                        if o.get_gridloc() == coords[:2] and o.state[0] == 'gridsquare':
                            self.cursor.set_state(MenuItem(screen, [1210,130], self.sizes, ["gate", "carrying"], self.layers["gate"]))
                            o.click(self.cursor)
            self.cursor.state[2] = None

        self.save()

    def run_engine(self):
        """
        GriddingEngine.run_engine() --> bool
            runs the gridding program for one frame
            returns whether we should display the path (if enter was pressed)
        """

        #### get events and establish update queues by tier
        events = pygame.event.get()
        queue = [[] for _ in range(len(set(self.layers.values())))]

        #### queue cursor
        if not self.inputBox.state[1]:
            queue[self.layers["cursor"]].append(self.cursor.update)

        #### queue menu
        def mu():
            pygame.draw.rect(self.screen, (220,220,225), self.menuBG, 0),
            self.screen.blit(self.menuHeading, [self.menuBox[0] + (self.menuBox[2]-self.menuHeading.get_width())/2+10, 
                                                self.menuBox[1] + self.menuBuffer-10])
        queue[self.layers["menubg"]].append(mu)

        #### queue input box and buttons
        queue[self.layers["menu_input"]].append(lambda: self.inputBox.update(self.cursor))
        queue[self.layers["menu_buttons"]].append(lambda: self.btnToggle.update(self.cursor))
        queue[self.layers["menu_buttons"]].append(lambda: self.btnReset.update(self.cursor))
        queue[self.layers["menu_buttons"]].append(lambda: self.btnRand.update(self.cursor))
        queue[self.layers["menu_buttons"]].append(lambda: self.btnCalc.update(self.cursor))

        #### queue all objects
        clicked = False
        pressed = False
        for event in events:
            if event.type == pygame.QUIT:
                self.quit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.inputBox.click(self.cursor)
                self.btnToggle.click(self.cursor)
                self.btnReset.click(self.cursor)
                self.btnRand.click(self.cursor)
                self.btnCalc.click(self.cursor)

                self.cursor.set_state(True)
                clicked = True

                if self.btnReset.get_state():
                    self.btnReset.set_state(False)
                    self.reset()
                elif self.btnRand.get_state():
                    self.btnRand.set_state(False)
                    self.randomize()
                elif self.btnCalc.get_state():
                    self.btnCalc.set_state(False)
                    self.save()
                    if len(self.stats[1]) == 2:
                        if len(self.stats[2]) == 2:
                            self.switch_states()
                            pressed = True
                        else:
                            print('You need an end point!')
                    else:
                        print('You need a start point!')
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.cursor.set_state(False)
                if self.saveHandling[0] >= self.saveHandling[1]:
                    self.save()
                    self.saveHandling[0] = 0

            elif event.type == pygame.KEYDOWN:        
                if self.inputBox.get_state(1) == False:
                    o = None
                    if event.key == self.keybinds["quit"] or event.key == pygame.K_ESCAPE:
                        self.quit()
                    elif event.key == self.keybinds["reset"]:
                        self.reset()
                    elif event.key == self.keybinds["start_point"]:
                        o = MenuItem(screen, [1210,145], self.sizes, ["start_point", "carrying"], self.layers["start_point"])
                    elif event.key == self.keybinds["end_point"]:
                        o = MenuItem(screen, [1210,145], self.sizes, ["end_point", "carrying"], self.layers["end_point"])
                    elif event.key == self.keybinds["block"]:
                        o = MenuItem(screen, [1210,160], self.sizes, ["block", "carrying"], self.layers["block"], gridLocation = None, direction = 'horizontal')
                    elif event.key == self.keybinds["gate"]:
                        o = MenuItem(screen, [1210,130], self.sizes, ["gate", "carrying"], self.layers["gate"])
                    elif event.key == self.keybinds["bottle"]:
                        o = MenuItem(screen, [1210,145], self.sizes, ["bottle", "carrying"], self.layers["bottle"])
                    elif event.key == pygame.K_RETURN:
                        self.save()
                        if len(self.stats[1]) == 2:
                            if len(self.stats[2]) == 2:
                                self.switch_states()
                                pressed = True
                            else:
                                print('You need an end point!')
                        else:
                            print('You need a start point!')
                    if o and not self.cursor.state[2] and self.check(o):
                        self.cursor.set_state(o)
                self.inputBox.type(event)    
        
        found = False
        for object in Sprite.objects:
            if not found and self.cursor.is_click_valid(object) and self.check(object):
                found = True
                object.set_state(True)
                if clicked:
                    self.cursor.click(object)
            else:
                object.set_state(False)
            queue[object.get_priority()].append(object.update)
        if clicked and not found:
            self.cursor.set_state(None)

        #### update by tiers
        for tier in queue:
            for obj_update_func in tier:
                obj_update_func()

        self.saveHandling[0] += 1
        return pressed

    def quit(self):
        """
        GriddingEngine.quit() --> None
            quits gridding - called when pygame window is closed (x)
                saves the current layout such that the next usage of the program will open with this layout
        """
        
        self.running = False
        self.save()

    def reset(self):
        """
        GriddingEngine.reset() --> None
            resets the grid (all menu items deleted) as well as the target time input box
        """
        if self.cursor.state[2]:
            self.cursor.state[2].delete()
        self.inputBox.reset()
        for object in Sprite.objects:
            object.reset()

    def switch_states(self):
        b.clear_cache()
        print('Calculating optimal path...', timing=1000)
        self.cursor.coords = [self.screen.get_width()+30, self.screen.get_height()+30]
        for _ in range(5):
            b.update()
            time.sleep(0.001)

    def check(self, object):
        """
        GriddingEngine.check(object) --> bool
            ensures that the placement of the items in the grid is valid (number and position)
            doesn't check if a path exists - just don't mess up >:)

            returns True or False depending on validity of the object to be placed where it is being placed
        """
        if object.state[2] in ['menu', 'carrying']:
            counts = [0,0,0,0,0]
            for i in [o for o in Sprite.objects if o.state[2] == 'board']:
                counts[['start_point','end_point','block','gate','bottle'].index(i.get_state(0))] += 1
            if object.state[0] == 'gate':   # make sure there are less than 5 (states)
                if counts[3] >= g.gateCount:
                    print("Too many gates!")
                    return False
            elif object.state[0] == 'bottle':   # make sure there are less than 4 (states)
                if counts[4] >= g.bottleCount:
                    print("Too many bottles!")
                    return False
            elif object.state[0] == 'block':    # make sure there are less than 10
                if counts[2] >= g.blockCount:
                    print("Too many blocks!")
                    return False
            elif object.state[0] == 'start_point':  # make sure there are 0
                if counts[0] >= 1:
                    print("Too many start points!")
                    return False
            elif object.state[0] == 'end_point':    # make sure there are 0
                if counts[1] >= 1:
                    print("Too many end points!")
                    return False
        elif self.cursor.state[2] != None:
            coords = object.get_gridloc()
            if self.cursor.state[2].state[0] == 'block':    # make sure a path exists
                if len(self.stats[1]) == 0 or len(self.stats[2]) == 0:
                    return True
                start = [x for x in p.get_segment_neighbors(self.stats[1]) if (0 <= x[0] < self.gridSize[0]) and (0 <= x[1] < self.gridSize[1])][0]
                obs = set([tuple(x) for x in self.outsideSegments + self.stats[3] + [coords]])

                targets = [self.stats[2]] + self.stats[4]   # the endpoint, all gates
                for t in targets:
                    res = p.pathfind(start, t, (1,0), 0, obs, False)
                    if len(res[0]) == 0:
                        print(f"This block would prevent access to {'the endpoint' if t==self.stats[2] else 'a gate zone'}!")
                        return False
                    
                targets = self.stats[5]                     # all bottles
                for t in targets:
                    paths = []
                    for adj in p.get_segment_neighbors(t):
                        paths.append(len(p.pathfind(start, adj, (1,0), 0, obs, False)[0]) == 0)
                    if all(paths):
                        print('This block would prevent access to a bottle!')
                        return False
            elif self.cursor.state[2].state[0] == 'start_point':    # make sure it is on the outer boundary
                for c in self.outsideSegments:
                    if coords[0] == c[0] and coords[1] == c[1]:
                        return True
                print("Start points can only be placed on the outside boundary!")
                return False
            elif self.cursor.state[2].state[0] == 'bottle':     # make sure it is NOT on the outer boundary
                for c in self.outsideSegments:
                    if coords[0] == c[0] and coords[1] == c[1]:
                        print("Bottles cannot be placed on the outside boundary!")
                        return False
        return True
    
    def save(self):
        """
        GriddingEngine.save() --> None
            updates stats based on the locations of the items in the board
        """
        startPoint = []
        endPoint = []
        blocks = []
        gates = []
        bottles = []

        gateCount = 0
        for object in Sprite.objects:
            if object.get_state(2) != "board":
                continue
            pos = object.get_gridloc()
            t = object.get_state(0)
            if t == 'start_point':
                startPoint = pos
            elif t == 'end_point':
                endPoint = pos
            elif t == 'block':
                blocks.append(pos)
            elif t == 'gate':
                gateCount += 1
                if LASTGATEMECHANIC and gateCount == self.gateCount:
                    pos = pos+ [0]
                gates.append(pos)
            elif t == 'bottle':
                bottles.append(pos)  
        
        self.stats = [self.inputBox.get_state(2), startPoint, endPoint, blocks, gates, bottles, self.btnToggle.get_state()]

        with open(self.savepath, 'wb') as file:
            pickle.dump(self.stats, file)
    
    def get_specs(self):
        """
        GriddingEngine.get_specs() --> list
            returns stats (locations)
        """
        return self.stats
    
    def randomize(self):
        """
        GriddingEngine.randomize() --> None
            genrates a random board setup
        """
        return

#####################################################################################
#####################################################################################
#####################################################################################
class PathMarker:
    points = []

    def __init__(self, screen, length, coords):
        """
        PathMarker.__init__(screen, length, coords) --> new PathMarker object
            screen (pygame.Display) - the Pygame screen
            length (int) - the length of the object (it's a circle, remember?)
            coords (list) - where to place the object (pixel coords, not grid coords)
            creates a new marker object
        """
        self.screen = screen
        self.coords = coords
        self.images = [pygame.transform.smoothscale(pygame.image.load(os.path.join(ROOT, 'marker.png')).convert_alpha(), [length, length]),
                       pygame.transform.smoothscale(pygame.image.load(os.path.join(ROOT, 'marker_hover.png')).convert_alpha(), [length, length])]

        self.counter = [0, 13]

        PathMarker.points.append(self)

    def update(self):
        """
        PathMarker.update() -> None
            updates the PathMarker object
            does the movement animations
        """
        max = (len(PathMarker.points)+10) * self.counter[1]
        self.counter[0] += 1
        if self.counter[0] > max:
            self.counter[0] = 0

        ps = PathMarker.points
        c = self.counter[1]
        if self.counter[0] < c * (ps.index(self)) or self.counter[0] > c * (ps.index(self) + 1.5):
            image = self.images[0]
        else:
            image = self.images[1]
        self.screen.blit(image, self.coords)

    def delete(self):
        """
        PathMarker.delete() --> None
            removes the PathMarker object
        """
        PathMarker.points.remove(self)

class PathingEngine:
    def __init__(self, screen, gridder):
        """
        PathingEngine().__init__(screen, gridder) --> new PathingEngine object
            screen (pygame.Display) - the Pygame screen
            gridder (object) - the GriddingEngine object (cuz why not)

            handles making the path
        """
        self.screen = screen
        self.gridBox = gridder.gridBox
        self.cellWidth = gridder.cellWidth
        self.bg = None
        self.bgAnchor = [80,80]

        self.timer = 0
        self.dispPad = 100
        self.dispChar = '> '
        self.markerSize = [50,30]
        self.minibumpDisp = 4
        
        # from gridding
        self.targetTime = 0
        self.startPoint = []
        self.endPoint = []
        self.gates = []
        self.bottles = []

        # for computing path
        self.route = []
        self.endpoints = []
        self.obstacles = []
        self.distances = {'forward' : 50,
                          'bump' : (25 + 13.69 + 5) * 2,
                          'minibump' : 7 * 2,
                          'backbump' : (25 - 13.69 + 5) * 2,
                          'enter' : (25 - 13.69),
                          'exit' : (13.69)}
        self.costs = {'move' : 40,
                      'turn' : 20,
                      '180 penalty' : 0,
                      'bump' : 40 * self.distances['bump'] / self.distances['forward'] + 1,
                      'minibump' : 40 * self.distances['minibump'] / self.distances['forward'] + 1,
                      'backbump' : 40 * self.distances['backbump'] / self.distances['forward'] + 1,
                      'gate' : [100, 10000000, 400],
                      'bottle_bonus' : 100000}

        # displaying
        self.robotRoute = []
        self.heading = []
        self.directions = [[-1,0],[0,1],[1,0],[0,-1]]        # w, s, e, n

        # engine logic
        self.running = False
        self.started = False
        self.finished = False
        self.calculated = False

    def setup(self, stats, grid_size):
        """
        PathingEngine.setup(stats, grid_size) --> None
            stats (list) --> the location stats from GriddingEngine
            grid_size (list) --> the size of the grid in cells (length x width)

            creates the adjacency matrix to facilitate pathing
        """
        self.targetTime, self.startPoint, self.endPoint, blocks, gates, bottles, self.shouldExport = stats

        i = -1
        for j, gate in enumerate(gates):
            if len(gate) != 3:
                self.gates.append(tuple(gate))
            else:
                i = j
        if i != -1:
            self.gates.append(tuple(gates[i][:2]))
        
        self.bottles = [tuple(b) for b in bottles]
        self.endpoints = [[0,0], self.endPoint]
        self.obstacles = set(g.outsideSegments + [tuple(b) for b in blocks])
        
        sq1, sq2 = self.get_segment_neighbors(self.startPoint)
        if 0 <= sq1[0] < grid_size[0] and 0 <= sq1[1] < grid_size[1]:
            self.endpoints[0] = sq1
        else:
            self.endpoints[0] = sq2
        sx, sy = self.startPoint
        ex, ey = self.endpoints[0]
        self.heading = [
            (ex * 2 + 1) - sx,
            (ey * 2 + 1) - sy
        ]
        
        self.bg = self.screen.subsurface(pygame.Rect(
            self.bgAnchor[0],
            self.bgAnchor[1], 
            self.gridBox[2]+(self.gridBox[0]-self.bgAnchor[0]+10)*2, 
            self.gridBox[3]+(self.gridBox[1]-self.bgAnchor[1]+10)*2
        )).copy()

        self.started = False

    def calc_path(self):
        """
        PathingEngine.calc_path(start, gates, last_gate) --> list, int
        - start: Starting coordinates [x, y]
        - gates: List of gate coordinates [[x, y], ...]

            Calculates the optimal path using dp
            Returns the optimal path and its cost.
        """

        all_gates_mask = (1 << len(self.gates)) - 1  # Bitmask representing all gates visited
        gate_segments = []
        for gate in self.gates:
            segs = self.get_square_neighbors(gate)
            gate_segments.append(segs['horizontal'] + segs['vertical'])

        def blocking_pattern(gate_idx, h_blocked, v_blocked):
            pattern = 0
            segs = self.get_square_neighbors(self.gates[gate_idx])
            if h_blocked:
                for seg in segs['horizontal']:  # bits 0,1
                    pattern |= (1 << gate_segments[gate_idx].index(seg))
            if v_blocked:
                for seg in segs['vertical']:    # bits 2,3
                    pattern |= (1 << gate_segments[gate_idx].index(seg))
            return pattern

        def lower_bound(current, visited_mask, scored_bottle_mask, carrying_idx):   # attempt at pruning (failed, incompatible with lru_cache)
            return -float('inf')
            unvisited_gates = bin(all_gates_mask ^ visited_mask).count('1')
            gate_lb = unvisited_gates * self.costs['move']

            unscored_bottles = bin(((1 << len(self.bottles)) - 1) & ~scored_bottle_mask).count('1')
            if carrying_idx != -1: unscored_bottles -= 1
            bottle_savings = unscored_bottles * self.costs['bottle_bonus']

            ex, ey = self.endpoints[1]
            cx, cy = current
            dist_lb = (abs(ex - cx) + abs(ey - cy)) * self.costs['move']

            return gate_lb + dist_lb - bottle_savings

        @lru_cache(None)
        def dp(current, visited_mask, scored_bottle_mask, carrying_idx, current_dir, scored_gate_info):

            min_cost = float('inf')
            best_path = []

            additional_obs = set()
            # Add all bottles NOT currently being carried and NOT yet scored
            for idx, b_seg in enumerate(self.bottles):
                if idx != carrying_idx and not (scored_bottle_mask & (1 << idx)):
                    additional_obs.add(b_seg)
            # Add blocked segments for gates that already contain bottles
            for i, gate in enumerate(self.gates):
                pattern = (scored_gate_info >> (i*4)) & 0xF
                for bit in range(4):
                    if pattern & (1 << bit):
                        additional_obs.add(gate_segments[i][bit])
            obs_set = frozenset(set(self.obstacles) | additional_obs)

            '''
            BASE CASE (end)
            '''
            if visited_mask == all_gates_mask:
                try: result = self.pathfind(current, self.endpoints[1], current_dir, visited_mask, obs_set, False)
                except ValueError: return 1, []
                print(f'FINISHED w/ cost [{result[0]}]', timing=1)
                return result[1], result[0]

            ''' 
            OPTION 1: Go to gate 
            '''
                    
            for i, gate in enumerate(self.gates):
                is_visited = visited_mask & (1 << i)
                is_scored = bool((scored_gate_info >> (i * 4)) & 0xF)
                if carrying_idx == -1:
                    if is_visited: continue
                else:
                    if is_scored: continue
                print(f'checking gate @ {gate}...', timing=1)

                adj_bottle = current == gate
                if current in set(self.gates) and not adj_bottle: continue
                next_visited_mask = visited_mask | (1 << i)

                for dx, dy in self.directions:
                    if adj_bottle and (-dx,-dy) != current_dir:
                        continue
                    sq_adj = (gate[0] + dx, gate[1] + dy)
                    if not self.is_valid(gate, sq_adj, obs_set):
                        continue
                    try: path, cost, next_dir = ([], 0, current_dir) if adj_bottle else self.pathfind(current, sq_adj, current_dir, visited_mask, obs_set, (carrying_idx != -1))                
                    except ValueError: return 2, []
                    if cost == float('inf'): continue

                    entry_dir = (-dx, -dy)
                    sq_opp = (gate[0]-dx, gate[1]-dy)
                    crossing_vertical = (dx != 0)
                    crossing_horizontal = (dy != 0)

                    # 1. Robot carrying bottle
                    if carrying_idx != -1:

                        # 1a. Gate already has a bottle
                        if is_scored and False:     # we ignore this bc it doesn't progress.
                            g_idx, h_blocked, v_blocked = is_scored
                            if (crossing_vertical and v_blocked) or (crossing_horizontal and h_blocked):
                                continue
                            if not self.is_valid(gate, sq_opp, obs_set):
                                continue

                            move_cost = self.costs['move']
                            if next_dir != entry_dir: move_cost += self.costs['turn']

                            sub_cost, sub_path = dp(sq_opp, next_visited_mask, scored_bottle_mask, carrying_idx, entry_dir, scored_gate_info, level+1)
                            total_cost = cost + sub_cost + move_cost
                            if total_cost < min_cost:
                                min_cost = total_cost
                                best_path = path + [tuple(gate), sq_opp] + sub_path[1:]
                        
                        # 1b. Gate is empty
                        else:
                            new_scored_mask = scored_bottle_mask | (1 << carrying_idx)

                            lb = lower_bound(gate, next_visited_mask, new_scored_mask, -1)
                            if cost + lb >= min_cost:
                                continue

                            # 1bA. Normal Bump
                            move_cost = ((self.costs['bump']/2 if adj_bottle else self.costs['bump']) - 
                                         self.costs['bottle_bonus'] + (self.costs['turn'] if next_dir != entry_dir else 0))
                            new_gate_info_a = scored_gate_info | (blocking_pattern(i, True, True) << (i*4))
                            sub_cost, sub_path = dp(sq_adj, next_visited_mask, new_scored_mask, -1, (dx, dy), new_gate_info_a)
                            total_cost = cost + sub_cost + move_cost
                            if total_cost < min_cost:
                                min_cost = total_cost
                                best_path = path + [tuple(gate), sq_adj] + sub_path[1:]

                            # 1bB. Minibump
                            new_gate_info_b = scored_gate_info | (blocking_pattern(i, crossing_horizontal, crossing_vertical) << (i*4))
                            base_m = ((0 if adj_bottle else self.costs['move']) + 
                                      self.costs['minibump'] - self.costs['bottle_bonus'] + (self.costs['turn'] if next_dir != entry_dir else 0))

                                # 1bBa. Backward exit
                            move_cost = base_m + self.costs['move']
                            sub_cost, sub_path = dp(sq_adj, next_visited_mask, new_scored_mask, -1, (dx, dy), new_gate_info_b)
                            total_cost = cost + sub_cost + move_cost
                            if total_cost < min_cost:
                                min_cost = total_cost
                                best_path = path + [tuple(gate), (gate[0]-dx/self.minibumpDisp, gate[1]-dy/self.minibumpDisp), tuple(gate)] + sub_path

                                # 1bBb. Side exit (Left/Right)
                            for turn in [(-dy, dx), (dy, -dx)]:
                                sq_side = (gate[0]+turn[0], gate[1]+turn[1])
                                if not self.is_valid(gate, sq_side, obs_set):
                                    continue
                                move_cost = base_m + self.costs['turn'] + self.costs['move']
                                sub_cost, sub_path = dp(sq_side, next_visited_mask, new_scored_mask, -1, turn, new_gate_info_b)
                                total_cost = cost + sub_cost + move_cost
                                if total_cost < min_cost:
                                    min_cost = total_cost
                                    best_path = path + [tuple(gate), (gate[0]-dx/self.minibumpDisp, gate[1]-dy/self.minibumpDisp), tuple(gate)] + sub_path

                            # 1bC. Side Minibump
                            if not self.is_valid(gate, sq_opp, obs_set):
                                continue
                            new_gate_info_c = scored_gate_info | (blocking_pattern(i, not crossing_horizontal, not crossing_vertical) << (i*4))
                            move_cost = (self.costs['move'] * (1 if adj_bottle else 2) + 
                                         self.costs['turn'] * 2 + self.costs['minibump'] - self.costs['bottle_bonus'] + (self.costs['turn'] if next_dir != entry_dir else 0))
                            sub_cost, sub_path = dp(sq_opp, next_visited_mask, new_scored_mask, -1, entry_dir, new_gate_info_c)
                            total_cost = cost + sub_cost + move_cost
                            if total_cost < min_cost:
                                min_cost = total_cost
                                best_path = path + [tuple(gate), (gate[0]-dy/self.minibumpDisp, gate[1]+dx/self.minibumpDisp), tuple(gate)] + sub_path
                    
                    # 2. Robot not carrying bottle
                    else:
                        
                        lb = lower_bound(gate, next_visited_mask, scored_bottle_mask, -1)
                        if cost + lb >= min_cost:
                            continue

                        # 2a. pass through
                        for exit_dir in [entry_dir, (-dy, dx), (dy, -dx)]:
                            sq_out = (gate[0] + exit_dir[0], gate[1] + exit_dir[1])
                            if not self.is_valid(gate, sq_out, obs_set):
                                continue
                            move_cost = self.costs['move'] + (self.costs['turn'] if next_dir != entry_dir else 0)
                            if exit_dir != entry_dir: move_cost += self.costs['turn'] + self.costs['move']

                            sub_cost, sub_path = dp(sq_out, next_visited_mask, scored_bottle_mask, -1, exit_dir, scored_gate_info)
                            total_cost = cost + sub_cost + move_cost
                            if total_cost < min_cost:
                                min_cost = total_cost
                                best_path = path + [tuple(gate), sq_out] + sub_path[1:]

                        # 2b. Backbump
                        move_cost = self.costs['backbump'] + (self.costs['turn'] if next_dir != entry_dir else 0)
                        sub_cost, sub_path = dp(sq_adj, next_visited_mask, scored_bottle_mask, -1, (dx, dy), scored_gate_info)
                        total_cost = cost + sub_cost + move_cost
                        if total_cost < min_cost:
                            min_cost = total_cost
                            best_path = path + [tuple(gate), sq_adj] + sub_path[1:]
            '''
            OPTION 2: Get a bottle
            '''
            if BOTTLEMECHANIC and carrying_idx == -1 and len(self.bottles) > 0:
                for i, b_seg in enumerate(self.bottles):
                    if scored_bottle_mask & (1 << i):
                        continue
                    print(f'checking bottle @ {b_seg}...', timing=1)
                    sq_a, sq_b = self.get_segment_neighbors(b_seg)

                    for sq_enter, sq_exit in [(sq_a, sq_b), (sq_b, sq_a)]:
                        try: path, cost, next_dir = self.pathfind(current, sq_enter, current_dir, visited_mask, obs_set, False)
                        except ValueError: return 3, []
                        if cost == float('inf'): continue

                        lb = lower_bound(sq_exit, visited_mask, scored_bottle_mask, i)
                        if cost + lb >= min_cost:
                            continue

                        push_dir = (sq_exit[0]-sq_enter[0], sq_exit[1]-sq_enter[1])
                        push_cost = self.costs['move']
                        if next_dir != push_dir:
                            push_cost += self.costs['turn']
                    
                        sub_cost, sub_path = dp(tuple(sq_exit), visited_mask, scored_bottle_mask, i, push_dir, scored_gate_info)
                    
                        total_cost = cost + sub_cost + push_cost
                        if total_cost < min_cost:
                            min_cost = total_cost
                            best_path = path + [sq_exit] + sub_path[1:]

            return min_cost, best_path

        # Initial call (no gates visited, no bottles scored, not carrying anything)
        total_cost, optimal_path = dp(tuple(self.endpoints[0]), 0, 0, -1, tuple(self.heading), 0)
        return optimal_path, total_cost

    def pathfind(self, start, end, start_direction, visited, obs_set, carrying):
        """
        PathingEngine.pathfind(start, end, start_direction) --> list, int
        - start: Starting coordinates [x, y]
        - end: Ending coordinates [x, y]
        - start_direction: Initial direction (optional), as a tuple (dx, dy)
        - visited: gates it has visited

        Calculates the optimal path between start and end, considering turn costs.
        Returns the path and the cost.
        """
        directions = [(0, -1), (1, 0), (0, 1), (-1, 0)]  # Up, Right, Down, Left
        queue = [(0, tuple(start), start_direction)]
        best_cost = {(tuple(start), start_direction): 0}  
        parent = {(tuple(start), start_direction): None}

        while queue:
            cost, current, current_dir = heapq.heappop(queue)
            if current == tuple(end):
                path = []
                state = (current, current_dir)
                while state is not None:
                    path.append(state[0])
                    state = parent[state]
                path.reverse()
                return path, cost, current_dir
            
            if best_cost.get((current, current_dir), float('inf')) < cost:
                continue

            for dx, dy in directions:
                next_pos = (current[0] + dx, current[1] + dy)
                next_seg = (current[0]*2+1 + dx, current[1]*2+1 + dy)
                if next_seg in obs_set:
                    continue

                # handle gates
                gate_penalty = 0
                if LASTGATEMECHANIC and next_pos == self.gates[-1]:
                    if bin(visited).count('1') != len(self.gates)-1 and next_pos != end:
                        gate_penalty = self.costs['gate'][1]

                # handle movement
                turn_penalty = 0
                if current_dir != (dx, dy):
                    diff = abs(directions.index(current_dir) - directions.index((dx, dy)))
                    turn_penalty = self.costs['turn'] * (2 - abs(2-diff))
                    if turn_penalty == self.costs['turn']*2 and carrying: 
                        turn_penalty += self.costs['180 penalty']
                
                total_cost = cost + self.costs['move'] + turn_penalty + gate_penalty
                next_state = (next_pos, (dx, dy))

                if total_cost < best_cost.get(next_state, float('inf')):
                    best_cost[next_state] = total_cost
                    parent[next_state] = (current, current_dir)
                    heapq.heappush(queue, (total_cost, next_pos, (dx, dy)))

        return [], float('inf'), start_direction
    
    def get_segment_neighbors(self, seg):
        sx, sy = seg
        if sx % 2 == 0: # vertical segment
            return (sx//2 - 1, (sy-1)//2), (sx//2, (sy-1)//2)
        else: # horizontal segment
            return ((sx-1)//2, sy//2 - 1), ((sx-1)//2, sy//2)
        
    def get_square_neighbors(self, sq):
        j,i = sq
        return {
            'horizontal' : [(j*2+1, i*2), (j*2+1, i*2+2)],
            'vertical' : [(j*2, i*2+1), (j*2+2, i*2+1)]
        }
    
    def is_valid(self, start, end, obs_seg):
        if (0 <= end[0] < BOARDSIZE[0]) and (0 <= end[1] < BOARDSIZE[1]):
            s_seg = set(self.get_square_neighbors(start)['horizontal'] + \
                         self.get_square_neighbors(start)['vertical'])
            e_seg = set(self.get_square_neighbors(end)['horizontal'] + \
                         self.get_square_neighbors(end)['vertical'])
            seg = [x for x in s_seg if x in e_seg][0]
            if seg not in obs_seg:
                return True
        return False
    
    def run_engine(self):
        """
        PathingEngine.run_engine() --> None
            calculates and then updates the path on top of the grid
        """
        self.screen.blit(self.bg, (self.screen.get_width()/2 - (self.gridBox[2]/2 + self.gridBox[0]-self.bgAnchor[0]),
                                   self.screen.get_height()/2 - (self.gridBox[3]/2 + self.gridBox[1]-self.bgAnchor[1])))

        if not self.started:
            self.started = True
            self.finished = False
            self.calculated = False

            self.worker = threading.Thread(target=self._calc_path_worker, daemon=True)
            self.worker.start()
        elif self.finished and not self.calculated:
            self.calc_instructions()
            self.calc_difficulty()

            if len(self.route) > 0:
                if self.shouldExport: self.export_path()
            else:
                self.robotRoute = ['Failed to calculate path.']

            for coord in self.route:
                if (coord[0]+coord[1])*10 % 10 != 0:
                    PathMarker(self.screen, self.markerSize[1], 
                               [2.5 + (self.cellWidth-self.markerSize[1])/2 + coord[0]*self.cellWidth + 
                                (self.screen.get_width()-self.gridBox[2])/2,
                                2.5 + (self.cellWidth-self.markerSize[1])/2 + coord[1]*self.cellWidth + 
                                (self.screen.get_height()-self.gridBox[3])/2])
                else:
                    PathMarker(self.screen, self.markerSize[0], 
                               [2.5 + (self.cellWidth-self.markerSize[0])/2 + coord[0]*self.cellWidth + 
                                (self.screen.get_width()-self.gridBox[2])/2,
                                2.5 + (self.cellWidth-self.markerSize[0])/2 + coord[1]*self.cellWidth + 
                                (self.screen.get_height()-self.gridBox[3])/2])
            
            b.clear_cache()
            self.timer = 0
            self.calculated = True

        elif self.calculated:
            for marker in PathMarker.points:
                marker.update()
            
            display = f'{self.targetTime}s Target Time, {self.counts['move']} FORWARDs, {self.counts['bump']} BUMPs, {self.counts['turn']} TURNs --> {self.counts['dist']:.2f} cm.' + \
                      ' '*10 + f'Difficulty Rating: {self.difficulty:.2f}.' + ' '*10+'[ENTER] to quit\n'
            self.timer += 1
            for i, step in enumerate(self.robotRoute):
                if self.timer // self.dispPad == i:
                    display += (self.dispChar)
                if self.timer > len(self.robotRoute) * self.dispPad:
                    self.timer = 0
                display += (step + '\n')
            print(display, keep_newlines = True, timing=1)
    
    def _calc_path_worker(self):
        try: 
            route, _ = self.calc_path()
            self.route = route
        except Exception as e: 
            pass
        self.finished = True   # signal completion

    def calc_instructions(self):
        robotRoute = []
        i = 0
        carrying = False

        while i < len(self.route)-1:
            s1 = self.route[i]
            s2 = self.route[i+1]
            s3 = self.route[i+2] if i+2 < len(self.route) else (-1,-1)
            bottles = self.bottles
            toAdd = []

            h = [s2[0]-s1[0],s2[1]-s1[1]]

            if s1 == s3:
                i += 1
                mini = False
                if ((s2[0]+s2[1])) != int(s2[0]+s2[1]):
                    mini = True
                    h = [h[0]/max(abs(h[0]),abs(h[1])), h[1]/max(abs(h[0]),abs(h[1]))]
                if carrying:
                    carrying = False
                    if mini:
                        toAdd = ['MINIBUMP']
                    else:
                        toAdd = ['BUMP']
                else:
                    a = self.get_square_neighbors(s1)['horizontal'] + self.get_square_neighbors(s1)['vertical']
                    b = set(self.get_square_neighbors(s2)['horizontal'] + self.get_square_neighbors(s2)['vertical'])
                    seg = [x for x in a if x in b]
                    if seg and seg[0] in bottles:
                        toAdd = ['FORWARD']
                        i -= 1
                        carrying = True
                        bottles.remove(seg[0])
                    else:
                        if h == self.heading:
                            toAdd = ['BUMP']
                        else:
                            h = self.directions[self.directions.index(h)-2]
                            toAdd = ['BACKBUMP']
            else:
                toAdd = ['FORWARD']
                a = self.get_square_neighbors(s1)['horizontal'] + self.get_square_neighbors(s1)['vertical']
                b = set(self.get_square_neighbors(s2)['horizontal'] + self.get_square_neighbors(s2)['vertical'])
                seg = [x for x in a if x in b]
                if seg and seg[0] in bottles:
                    carrying = True   
                    bottles.remove(seg[0])

            diff = self.directions.index(h)-self.directions.index(self.heading)

            if abs(diff) == 2:
                toAdd = ['LEFT']*2 + toAdd
            elif diff == 1 or diff == -3:
                toAdd.insert(0, 'LEFT')
            elif diff == -1 or diff == 3:
                toAdd.insert(0, 'RIGHT')

            robotRoute += toAdd
            self.heading = h
            i += 1

        robotRoute = ['ENTER'] + robotRoute + ['EXIT'] if len(robotRoute) > 0 else []
        self.robotRoute = []
        self.counts = {'move' : 0,
                       'bump' : 0,
                       'turn' : 0,
                       'dist' : 0}
        self.difficulty = 0

        for step in robotRoute:
            if step == 'FORWARD':
                self.counts['move'] += 1
                self.counts['dist'] += self.distances['forward']
                if 'FORWARD' in self.robotRoute[-1]:
                    self.robotRoute = self.robotRoute[:-1] + [f'FORWARDx{int(self.robotRoute[-1][-1])+1}']
                else:
                    self.robotRoute.append('FORWARDx1')
            else:
                if step in {'LEFT', 'RIGHT'}:
                    self.counts['turn'] += 1
                elif step in {'BUMP', 'BACKBUMP', 'MINIBUMP'}:
                    self.counts['bump'] += 1
                    self.counts['dist'] += self.distances[step.lower()]
                elif step in {'ENTER', 'EXIT'}:
                    self.counts['dist'] += self.distances[step.lower()]

                self.robotRoute.append(step)
        for i,step in enumerate(self.robotRoute):
            if step == 'FORWARDx1':
                self.robotRoute[i] = 'FORWARD'

    def calc_difficulty(self):
        raw = ((self.counts['move']+self.counts['bump']+self.counts['turn']) * 0.05 + 
                           self.counts['bump'] * 0.0 +
                           self.counts['turn'] * 0.07 +
                           self.counts['dist'] * 0.0018 + 
                           self.targetTime * 0.0 + 
                           ((self.counts['dist']-self.distances['forward']/2) / 
                            (self.targetTime-self.counts['turn']*1.4-0.7-1.2) * 0.08))
        scaleMax = 12.0
        self.difficulty = max(0.0, min(10.0, 10 * raw / scaleMax))

    def export_path(self): ########################### The queue console prints are in this function. I just commented them out >:)
        """
        PathingEngine.export_path() --> None
            prints the path such that it can be copy-pasted into main.py
            also saves the path to "queue.txt"
        """
        variableNames = ['targetTime', 'queue']  # main.py variable names
        output_lines = []

        # Console printing
        print(f'{variableNames[0]} = {self.targetTime}\n', normal=True)
        output_lines.append(f'{variableNames[0]} = {self.targetTime}')
        
        queue_line = f'{variableNames[1]} = ['

        for i, step in enumerate(self.robotRoute):
            if i != 0:
                queue_line = ' ' * (len(variableNames[1]) + 4)
            queue_line += f'"{step.replace('x','') if 'FORWARD' in step else step}"'
            if i == (len(self.robotRoute) - 1):
                queue_line += ']'
            else:
                queue_line += ','
            output_lines.append(queue_line)
            print(f'{queue_line}\n', normal=True)

        # Save output to file
        with open(os.path.join(ROOT, 'queue.txt'), 'w') as file:
            file.write('\n'.join(output_lines))
            #print(f"Saving to: {os.path.join(ROOT, 'queue.txt')}", normal = True)

        # transfer output to main.py
        #transfer.transfer()
                
    def clear(self):
        """
        PathingEngine.clear() --> None
            resets all relevant variables (called once user is done looking at the path)
        """
        PathMarker.points = []        
        self.targetTime = 0
        self.startPoint = []
        self.endPoint = []
        self.gates = []
        self.bottles = []
        self.route = []
        self.endpoints = []
        self.obstacles = []
        self.robotRoute = []
        self.heading = []
        self.running = False
        self.calculated = False

#####################################################################################
#####################################################################################
#####################################################################################

def custom_disp(*args, sep=' ', end='', timing = -100, keep_newlines = False, normal = False, **kwargs):

    message = sep.join(map(str, args)) + end
    if normal:
        b.original(message, sep=sep, end=end, **kwargs)
        return
    
    if keep_newlines: 
        b.queue.put([message, timing])
        return
    message = message.strip()

    b.queue.put([message, timing])
    return

#####################################################################################
#####################################################################################
#####################################################################################

#ROOT = r"D:\Robot Tour\gridding\assets"
ROOT = r"C:\Users\super\Documents\projects\YHS\Robot Tour\gridding\assets"
pygame.init()
pygame.mouse.set_visible(False)
screenDimensions = [1400,800]
screen = pygame.display.set_mode(screenDimensions)
clock = pygame.time.Clock()

BOARDSIZE = [5,4]
NUMOBSTACLES = 10
LASTGATEMECHANIC = False
NUMGATES = 5
BOTTLEMECHANIC = True
NUMBOTTLES = 4

debug = [0]

g = GriddingEngine(screen)
p = PathingEngine(screen, g)
b = Background(screen, 'bpooooop')

startTime = time.perf_counter()
while True:    
    b.update()

    if p.running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                p.clear()
                b.clear_cache()
                g.running = True
                p.running = False
            elif event.type == pygame.QUIT:
                p.clear()
                b.clear_cache()
                g.running = False
                p.running = False

    pressed = False
    if g.running:
        pressed = g.run_engine()        
    elif p.running:
        p.run_engine()
    else:
        break

    if pressed:
        p.setup(g.get_specs(), BOARDSIZE)
        g.running = False
        p.running = True

    #### pygame stuff
    timeLeft = 10 * 60 + startTime - time.perf_counter()
    timeLeft = 0
    mins = int(timeLeft // 60)
    secs = int((timeLeft - mins * 60)*100) / 100

    pygame.display.flip()
    clock.tick(100)
    pygame.display.set_caption(f"Grid the robot game! Prep time remaining --> {"{:02}".format(mins)} : {"{:03}".format(secs)}")

pygame.quit()
sys.exit()