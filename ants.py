'''
author Louis Larpin

Ants Colony Optimization Analysis
'''

import tkinter as tk
import tkinter.messagebox
import random
import threading
import time
import math


###############################
#   Models
###############################

'''
classdoc
'''
class Singleton:

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Singleton, cls).__new__(cls)
        return cls._instance
        

'''
classdoc
'''
class Observable:
    
    def __init__(self, initialValue=None):
        self._data = initialValue
        self._callbacks = {}    # An attribute can have many associated callbacks

    def addCallback(self, func):
        self._callbacks[func] = 1

    def delCallback(self, func):
        del self._callbacks[func]

    def __triggerCallbacks(self):
        for func in self._callbacks:
            func(self._data)

    def set(self, data):
        self._data = data
        self.__triggerCallbacks()

    def get(self):
        return self._data

    def unset(self):
        self._data = None


'''
classdoc
'''
class ObservableList(list):

    def __init__(self, initialArray=[]):
        list.__init__(self, initialArray)
        self._callbacks = {}

    def addCallback(self, func):
        self._callbacks[func] = 1

    def delCallback(self, func):
        del self._callbacks[func]

    def __triggerCallbacks(self, index):
        for func in self._callbacks:
            func(self[index])

    def addElement(self, el):
        self.append(el)
        self.__triggerCallbacks(el)

    def delElement(self, el):
        raise Exception("Not implemented yet!")

    def upElement(self, index, new):
        self[index] = new
        self.__triggerCallbacks(index)


'''
classdoc
'''
class Colony:
    
    def __init__(self, mem_count, x, y, id):
        self._level = Level._instance
        self._members = ObservableList()
        for i in range(mem_count):
            identity = '{}_{}'.format(id, i)
            ant = Ant(identity=identity, x=x, y=y)
            ant._observer.addCallback(self.memberMoved)
            self._members.append(ant)   # Use addElement instead of append to trigger callbacks

    def explore(self):
        for ant in self._members:
            ant.start()

    def genocide(self):
        for ant in self._members:
            ant.kill()

    def memberMoved(self, ant):
        self._members.upElement(int(ant._id.split('_')[1]), ant)


'''
classdoc
'''
class Ant(threading.Thread):

    SPEED = .05
    DIRECTIONS = [
        ('EAST', (4, 0)),
        ('NORTHEAST', (4, -4)),
        ('NORTH', (0, -4)),
        ('NORTHWEST', (-4, -4)),
        ('WEST', (-4, 0)),
        ('SOUTHWEST', (-4, 4)),
        ('SOUTH', (0, 4)),
        ('SOUTHEAST', (4, 4))
    ]

    def __init__(self, identity, x=8, y=8):     # init after limit
        threading.Thread.__init__(self)
        self._level = Level._instance
        self._id = identity
        self._homePosition = (x, y) 
        self._currentPosition = (x, y)
        self._observer = Observable(initialValue=self)
        self._stopevent = threading.Event()
        self._currentDirection = Observable((0, 0))
        self._allowStepBack = False

    def run(self):
        while not self._stopevent.isSet():
            self._stopevent.wait((11 - AppDelegate._instance._globalTimerPick.get())/100)               # waits before next move
            direction =  self.__gatherNextDirections()                                                  # get next available locations
            if not direction:                                                                           
                self._allowStepBack = True                                                              # allow step back on next move
                continue
            else:
                randmove = random.choice(direction)                                                     # choose from available locations
                self._currentPosition = tuple(map(lambda x, y: x + y, self._currentPosition, randmove)) # merge move to old location
                self._currentDirection = randmove                                                       # define next direction
                self._observer.set(self)                                                                # trigger redraw
            if self._allowStepBack and self.__isHomeNeighborhood():                                     # ant gets back home
                self._allowStepBack = False                                                             # restart exploration 

    def kill(self):
        self._stopevent.set()

    def __gatherNextDirections(self):
        currentDistance = self.__distanceToHome(self._currentPosition)
        nextDirections = []
        for label, direction in self.DIRECTIONS:
            newLocation = tuple(map(lambda x, y: x + y, self._currentPosition, direction))
            posX, posY = newLocation[0], newLocation[1]
            # TODO: handle food/pheronome
            if self._level.foundFood(posX//8, posY//8):
                print("Ant with id {}".format(self._id))
                self._allowStepBack = True
                continue;
            # determine available locations
            if not self._level.collide(posX//8, posY//8) and posX > 0 and posY > 0:
                distance = self.__distanceToHome(newLocation)
                if distance > currentDistance and not self._allowStepBack:
                    nextDirections.append(direction)
                elif distance < currentDistance and self._allowStepBack:
                    nextDirections.append(direction)
        return nextDirections

    def __distanceToHome(self, location):
        xoffset = abs(self._homePosition[0] - location[0])
        yoffset = abs(self._homePosition[1] - location[1])
        return math.sqrt(pow(xoffset, 2) + pow(yoffset, 2))

    def __isHomeNeighborhood(self):
        inX = self._currentPosition[0] in range(self._homePosition[0]-4, self._homePosition[0]+4)
        inY = self._currentPosition[1] in range(self._homePosition[1]-4, self._homePosition[1]+4)
        return inX and inY


'''
classdoc
'''
class Level(Singleton):

    WIDTH  = 80
    HEIGHT = 80   # Matrix 80 = 640/8

    LIMIT  = -1
    EMPTY  = 0
    WALL   = 1
    WATER  = 2
    COLONY = 3
    FOOD   = 4

    def __init__(self):
        self._observer = Observable()
        self._map = self.__genEmptyLevel()
        self._observer.set(self._map)

    def __genEmptyLevel(self):
        limits = (0, self.WIDTH-1, self.HEIGHT-1)
        var = []
        for i in range(self.WIDTH):
            var.append([])
            for j in range(self.HEIGHT):
                if i in limits or j in limits:
                    var[i].append(self.LIMIT)
                else:
                    var[i].append(self.EMPTY)
        return var

    def __addObstacle(self, x, y, kind):
        if kind == 'wall':
            self._map[x][y] = self.WALL
        elif kind == 'water':
            self._map[x][y] = self.WATER
        self._observer.set(self._map)

    def __addAgent(self, x, y, kind):
        for i in [x, x+1, x+2]:
            for j in [y, y+1, y+2]:
                if kind == 'colony':
                    self._map[i][j] = self.COLONY
                elif kind == 'food':
                    self._map[i][j] = self.FOOD
        self._observer.set(self._map)

    def __setItem(self, x, y, kind):
        if not self.collide(x, y):
            if kind in ['wall', 'water']:
                self.__addObstacle(x, y, kind)
            elif kind in ['colony', 'food']:
                self.__addAgent(x, y, kind)
            else:
                raise Exception('Kind {} does not exist'.format(kind))

    def __unsetItem(self, x, y, kind):
        if self.__canUnset(x, y, kind):
            self._map[x][y] = self.EMPTY
            self._observer.set(self._map)

    def __canUnset(self, x, y, kind):
        if kind == 'wall':
            return self._map[x][y] == self.WALL
        if kind == 'water':
            return self._map[x][y] == self.WATER
        else:
            return False

    def reset(self):
        self._map = self.__genEmptyLevel()
        self._observer.set(self._map)

    def collide(self, x, y):
        return self._map[x][y] != self.EMPTY

    def foundFood(self, x, y):
        return self._map[x][y] == self.FOOD

    def addItem(self, x, y, kind, removable=False):
        if not removable:
            self.__setItem(x, y, kind)
            return
        if not self.collide(x, y):
            self.addItem(x, y, kind)
        else:
            self.__unsetItem(x, y, kind)

    # Debugging
    def log(self):
        content = []
        for i in range(self.WIDTH):
            content.append('\n')
            for j in range(self.HEIGHT):
                content.append(str(self._map[j][i]))
        print(''.join(content))


###############################
#   Controllers
###############################


'''
classdoc
'''
class MainController:

    ANTS_COUNT = 100
    
    def __init__(self, root):
        # setup needed models
        self._level = Level._instance
        self._level._observer.addCallback(self.levelChanged)
        self._colonies = []
        self._isRunning = False
        # setup views
        left = tk.Frame(root, bg='gray')
        left.pack(side='left', anchor='n')
        # setup controls view
        self._controls = ControlsView(parent=left)
        self._controls.pack(anchor='w', padx=5, pady=5)
        self._controls._run.config(command=self.runSimulation)      # register view callbacks
        self._controls._stop.config(command=self.stopSimulation)
        self._controls._reset.config(command=self.resetLevel)
        self._controls._debug.config(command=self.debug)
        # setup toolbox
        self._toolbox = ToolboxView(parent=left)
        self._toolbox.pack(anchor='w', padx=5, pady=5)
        self._currentTool = tk.StringVar()
        self._currentTool.set('wall')       # initial value is wall
        for btn in self._toolbox._buttons:
            btn.config(variable=self._currentTool)
        # setup settings view
        self._settings = SettingsView(parent=left)
        self._settings.pack(anchor='w', padx=5, pady=5)
        self._currentColonySize = tk.IntVar()
        self._currentColonySize.set(50)
        self._settings._colonySizeBox.config(textvariable=self._currentColonySize)
        self._settings._antSpeedBox.config(textvariable=AppDelegate._instance._globalTimerPick)
        # setup canvas view
        self._canvas = LevelView(parent=root)
        self._canvas.bind('<Button-1>', self.addOrRemoveItem)
        self._canvas.bind('<B1-Motion>', self.addItem)
        self._canvas.pack(side='left', anchor='n')
        
    # Private methods
    def __validCoords(self, x, y):
        return x > 0 and y > 0 and x < LevelView.WIDTH and y < LevelView.HEIGHT

    def __toLevelCoords(self, event):
        # Convert to level coordiantes using floor division
        x = int(self._canvas.canvasx(event.x))//8
        y = int(self._canvas.canvasy(event.y))//8
        return x, y

    def __newColony(self, x, y):
        colony = Colony(self._currentColonySize.get(), x, y, len(self._colonies)+1)
        colony._members.addCallback(self.antMoved)
        self._colonies.append(colony)

    def __editLevel(self, event, removable=False):
        if not self.__validCoords(event.x, event.y): return
        coords = self.__toLevelCoords(event)
        self._level.addItem(coords[0], coords[1], self._currentTool.get(), removable)

    # Canvas events handler
    def addItem(self, event):   # Called on mouse clicked and dragged
        if self._currentTool.get() in ['colony', 'food']: return
        self.__editLevel(event)
        
    def addOrRemoveItem(self, event):   # Called on mouse clicked only
        if self._currentTool.get() == 'colony':
            if self._isRunning is True: return
            else:
                posX, posY = (event.x//8)*8, (event.y//8)*8     # Makes sure location is mutliple of 2
                self.__newColony(posX, posY) 
        self.__editLevel(event, True)

    # Buttons events handlers
    def resetLevel(self):
        result = tk.messagebox.askyesno("Confirmation", "Are You Sure?", icon='info')
        if result == True:
            self._colonies = []
            self._level.reset()
            self._canvas.clear()

    def runSimulation(self):
        if not self._colonies: 
            tk.messagebox.showinfo("Info", "You need to place at least one colony", icon='warning')
            return
        self._isRunning = True
        if self._colonies:
            self._controls.switchBtnState()
            for colony in self._colonies:
                colony.explore()

    def stopSimulation(self):
        for colony in self._colonies:
            colony.genocide()
        self._controls.switchBtnState()
        self._isRunning = False

    def debug(self):
        Level._instance.log()

    # Models callbacks
    def antMoved(self, ant):
        self._canvas.repaintAnt(ant)

    def levelChanged(self, level):
        self._canvas.repaintLevel(level)


###############################
#   Views
###############################


'''
classdoc
'''
class LevelView(tk.Canvas):

    WIDTH  = 640
    HEIGHT = 640

    WALL_COLOR   = '#1D1D1D'
    WATER_COLOR  = '#4696FF'
    COLONY_COLOR = '#5E3A16'
    FOOD_COLOR   = '#FF5B00'
    ANT_COLOR    = '#E24F42'
    
    def __init__(self, parent):
        tk.Canvas.__init__(self, parent, width=self.WIDTH, height=self.HEIGHT, relief=tk.GROOVE, bd=1)
        self._items = {}

    def repaintLevel(self, level):
        self.clear()    # Clear widget on each call
        self._items = {}
        for i in range(len(level)):
          for j in range(len(level[0])):
            posX, posY = i*8, j*8 
            if level[i][j] is Level.WALL:      # Pick up the right color
                self.create_rectangle(posX, posY, posX+8, posY+8, fill=self.WALL_COLOR, outline=self.WALL_COLOR)
            if level[i][j] is Level.WATER:
                self.create_rectangle(posX, posY, posX+8, posY+8, fill=self.WATER_COLOR, outline=self.WATER_COLOR)
            if level[i][j] is Level.COLONY:
                self.create_rectangle(posX, posY, posX+8, posY+8, fill=self.COLONY_COLOR, outline=self.COLONY_COLOR)
            if level[i][j] is Level.FOOD:
                self.create_rectangle(posX, posY, posX+8, posY+8, fill=self.FOOD_COLOR, outline=self.FOOD_COLOR)


    def repaintAnt(self, ant):
        item = self._items.get(ant._id)
        if item is not None:
            dirX, dirY = ant._currentDirection[0], ant._currentDirection[1]
            self.move(item, dirX, dirY)
        else:
            posX, posY = ant._currentPosition[0], ant._currentPosition[1]
            self._items[ant._id] = self.create_rectangle(posX, posY, posX+4, posY+4, fill=self.ANT_COLOR)    

    def clear(self):
        self.delete('all')


'''
classdoc
'''
class ControlsView(tk.LabelFrame):

    BTN_WIDTH = 9 

    def __init__(self, parent):
        tk.LabelFrame.__init__(self, parent, bg='gray', text='Controls')
        self._run = tk.Button(self, text="Run", width=self.BTN_WIDTH, highlightbackground='gray')
        self._run.pack()
        self._stop = tk.Button(self, text="Stop", width=self.BTN_WIDTH, state='disabled', highlightbackground='gray')
        self._stop.pack()
        self._reset = tk.Button(self, text="Reset", width=self.BTN_WIDTH, highlightbackground='gray')
        self._reset.pack()
        self._debug = tk.Button(self, text="Debug", width=self.BTN_WIDTH, highlightbackground='gray')
        self._debug.pack()
 
    def switchBtnState(self):
        for btn in (self._run, self._stop, self._reset):
            btn.config(state='disabled') if btn['state'] == 'normal' else btn.config(state='normal')


'''
classdoc
'''
class ToolboxView(tk.LabelFrame):

    MODES = [
        ('Wall', 'wall'),
        ('Water', 'water'),
        ('Colony', 'colony'),
        ('Food', 'food')
    ]

    def __init__(self, parent):
        tk.LabelFrame.__init__(self, parent, text='Tools', bg='gray')
        self._buttons = []
        for text, mode in self.MODES:
            btn = tk.Radiobutton(self, text=text, value=mode, indicatoron=0, bg='gray', width=12, justify='left')
            btn.pack(anchor='w')
            self._buttons.append(btn)


'''
classdoc
'''
class SettingsView(tk.LabelFrame):

    def __init__(self, parent):
        tk.LabelFrame.__init__(self, parent, text='Settings', bg='gray')
        label = tk.Label(self, text="Colony size:", bg='gray', width=12, pady=5).pack()
        self._colonySizeBox = tk.Spinbox(self, width=8, from_=1, to=100, bg='gray', highlightbackground='gray')
        self._colonySizeBox.pack()
        tk.Label(self, text="Ants speed:", bg='gray', width=12, pady=5).pack()
        self._antSpeedBox = tk.Spinbox(self, width=8, from_=1, to=10, bg='gray', highlightbackground='gray')
        self._antSpeedBox.pack()
        tk.Label(self, text="Moves count:", bg='gray', width=12, pady=5).pack()
        self._AntMoveCount = tk.Spinbox(self, width=8, from_=500, to=5000, bg='gray', highlightbackground='gray')
        self._AntMoveCount.pack()


###############################
#   Welcome
###############################


'''
application delegate
'''
class AppDelegate(Singleton):
    
    def __init__(self, root):
        root.title('Lego Colony Optimization')
        root.resizable(0,0)
        root.config(bg='gray')
        self._globalTimerPick = tk.IntVar()
        self._globalTimerPick.set(5)
        Level()
        MainController(root)


'''
mainloop
'''
def main():
    root = tk.Tk()
    app = AppDelegate(root)
    root.mainloop()

if __name__ == "__main__":
    main()

