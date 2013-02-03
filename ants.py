'''
author Louis Larpin

Ants Colony Optimization Analysis
'''

import tkinter as tk
import tkinter.messagebox
import random
import threading
import time


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
    
    def __init__(self, mem_count):
        self._level = Level._instance
        self._members = ObservableList()
        for i in range(mem_count):
            ant = Ant(index=i)
            ant._observer.addCallback(self.memberMoved)
            self._members.append(ant)   # Use addElement instead of append to trigger callbacks

    def explore(self):
        for ant in self._members:
            ant.start()

    def genocide(self):
        for ant in self._members:
            ant.kill()

    def memberMoved(self, ant):
        self._members.upElement(ant._id, ant)


'''
classdoc
'''
class Ant(threading.Thread):

    SPEED = .02

    def __init__(self, index, x=8, y=8):     # init after limit
        threading.Thread.__init__(self)
        self._level = Level._instance
        self._id = index
        self._position = (x, y)
        self._observer = Observable(initialValue=self)
        self._stopevent = threading.Event()

    def run(self):
        while not self._stopevent.isSet():
            randmove = (random.choice([-4, 0, 4]), random.choice([-4, 0, 4]))   # A random move
            newloc = tuple(map(lambda x, y: x + y, self._position, randmove))   # Merge move to old location
            posX, posY = newloc[0], newloc[1]
            self._stopevent.wait(self.SPEED)
            if not self._level.collide(posX//8, posY//8) and posX > 0 and posY > 0:     # Check availability
                self._position = newloc
                self._observer.set(self)

    def kill(self):
        self._stopevent.set()


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

    def reset(self):
        self._map = self.__genEmptyLevel()
        self._observer.set(self._map)

    def collide(self, x, y):
        return self._map[x][y] != self.EMPTY

    def setOrUnsetItem(self, x, y, kind):
        if self.collide(x, y):
            self.unsetItem(x, y)
        else:
            self.setItem(x, y, kind)

    def setItem(self, x, y, kind):
        if not self.collide(x, y):
            if kind == 'wall':
                self._map[x][y] = self.WALL
            elif kind == 'water':
                self._map[x][y] = self.WATER
            self._observer.set(self._map)

    def unsetItem(self, x, y):
        self._map[x][y] = self.EMPTY
        self._observer.set(self._map)

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
class LevelViewController:

    ANTS_COUNT = 500
    
    def __init__(self, root):
        # setup needed models
        self._level = Level._instance
        self._level._observer.addCallback(self.levelChanged)
        self._colony = None
        self.__renewColony()
        # setup views
        left = tk.Frame(root, bg='gray')
        left.pack(side='left', anchor='n')
        # setup controls view
        self._controls = ControlsView(parent=left)
        self._controls.pack(anchor='w')
        self._controls._run.config(command=self.runSimulation)      # register view callbacks
        self._controls._stop.config(command=self.stopSimulation)
        self._controls._reset.config(command=self.resetLevel)
        self._controls._debug.config(command=self.debug)
        # setup toolbox
        self._toolbox = ToolboxView(parent=left)
        self._toolbox.pack(anchor='w')
        self._currentTool = tk.StringVar()
        self._currentTool.set('wall')       # initial value is wall
        for btn in self._toolbox._buttons:
            btn.config(variable=self._currentTool)
        # setup canvas view
        self._canvas = LevelView(parent=root)
        self._canvas.bind('<Button-1>', self.addOrRemoveWall)
        self._canvas.bind('<B1-Motion>', self.addWall)
        self._canvas.bind('<Button-2>', self.addColony)
        self._canvas.pack(side='left', anchor='n')
        

    # Private methods
    def __checkCoord(self, x, y):
        return x <= 0 or y <= 0 or x >= LevelView.WIDTH or y >= LevelView.HEIGHT

    def __renewColony(self):
        self._colony = Colony(self.ANTS_COUNT)
        self._colony._members.addCallback(self.antMoved)

    # Canvas events handler
    def addWall(self, event):   # Called on mouse clicked and dragged
        if self.__checkCoord(event.x, event.y):
            return
        self._level.setItem(x=event.x//8, y=event.y//8, kind=self._currentTool.get())

    def addOrRemoveWall(self, event):   # Called on mouse clicked only
        if self.__checkCoord(event.x, event.y):
            return
        # Convert to level coordiantes using floor division
        self._level.setOrUnsetItem(x=event.x//8, y=event.y//8, kind=self._currentTool.get())

    def addColony(self, event):
        print("add colony")

    # Buttons events handlers
    def resetLevel(self):
        result = tk.messagebox.askyesno("Confirmation", "Are You Sure?", icon='warning')
        if result == True:
            self.__renewColony()
            self._level.reset()
            self._canvas.clear()

    def runSimulation(self):
        self._controls.switchBtnState()
        self._colony.explore()

    def stopSimulation(self):
        self._colony.genocide()
        self.__renewColony()
        self._controls.switchBtnState()

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

    WALL_COLOR  = 'black'
    WATER_COLOR = '#4696FF'
    ANT_COLOR   = 'red'
    
    def __init__(self, parent):
        tk.Canvas.__init__(self, parent, width=self.WIDTH, height=self.HEIGHT, relief=tk.GROOVE, bd=1)
        self._items = {}

    def repaintLevel(self, level):
        self.clear()    # Clear widget on each call
        for i in range(len(level)):
          for j in range(len(level[0])):
            posX, posY = i*8, j*8 
            if level[i][j] is Level.WALL:      # Pick up the right color
                self.create_rectangle(posX, posY, posX+8, posY+8, fill=self.WALL_COLOR)
            if level[i][j] is Level.WATER:
                self.create_rectangle(posX, posY, posX+8, posY+8, fill=self.WATER_COLOR, outline=self.WATER_COLOR)
            

    def repaintAnt(self, ant):
        item = self._items.get(ant._id)
        if item is not None:
            self.delete(item)
        posX, posY = ant._position[0], ant._position[1]
        self._items[ant._id] = self.create_rectangle(posX, posY, posX+4, posY+4, fill=self.ANT_COLOR)
        self.update()       

    def clear(self):
        self.delete('all')


'''
classdoc
'''
class ControlsView(tk.Frame):

    BTN_WIDTH = 8 

    def __init__(self, parent):
        tk.Frame.__init__(self, parent, bg='gray')
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
class ToolboxView(tk.Frame):

    MODES = [
        ('Wall', 'wall'),
        ('Water', 'water'),
        ('Colony', 'colo'),
        ('Food', 'food')
    ]

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self._buttons = []
        for text, mode in self.MODES:
            btn = tk.Radiobutton(parent, text=text, value=mode, indicatoron=0, bg='gray')
            btn.pack(anchor='w')
            self._buttons.append(btn)


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
        Level()
        LevelViewController(root)


'''
mainloop
'''
def main():
    root = tk.Tk()
    app = AppDelegate(root)
    root.mainloop()

if __name__ == "__main__":
    main()

