'''
author Louis Larpin

Ants Colony Optimization Analysis
'''

import tkinter as tk
import random
import threading
import time


BTN_WIDTH = 8    # App constant should be moved to settings singleton
BTN_BG = 'gray'


###############################
#   Models
###############################


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
    
    def __init__(self, level, mem_count):
        self._level = level
        self._members = ObservableList()
        for i in range(mem_count):
            ant = Ant(self._level, i)
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

    SPEED = .3

    def __init__(self, level, index, x=20, y=20):
        threading.Thread.__init__(self)
        self._level = level
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
class Level:

    WIDTH  = 80
    HEIGHT = 80   # Matrix 80 = 640/8

    LIMIT    = -1
    EMPTY    = 0
    WALL     = 1
    WATER    = 2
    RESOURCE = 3

    instance = None    # static class attribute

    def __new__(self):
        
        if self.instance is None:
            self.instance = object.__new__(self)
        return self.instance

    def __init__(self):
        self._map = self.__genEmptyLevel()
        self._observer = Observable(initialValue=self._map)

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

    def setOrUnsetWall(self, x, y):
        if self.collide(x, y):
            self.unsetWall(x, y)
        else:
            self.setWall(x, y)

    def collide(self, x, y):
        return self._map[x][y] != self.EMPTY

    def setWall(self, x, y):
        if not self.collide(x, y):
            self._map[x][y] = self.WALL
            self._observer.set(self._map)

    def unsetWall(self, x, y):
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
class CanvasController:

    ANTS_COUNT = 400
    
    def __init__(self, root):
        # setup needed models
        self._level = Level()
        self._level._observer.addCallback(self.levelChanged)
        self._colony = None
        self.__renewColony()
        # setup views
        self._canvas = CanvasView(parent=root)
        self._canvas.bind('<Button-1>', self.addOrRemoveWall)
        self._canvas.bind('<B1-Motion>', self.addWall)
        self._canvas.pack()
        # TODO: move this shit out of this controller!!!
        self._runBtn = tk.Button(root, text="Run", width=BTN_WIDTH, bg=BTN_BG, command=self.runSimulation)
        self._runBtn.pack()
        self._stopBtn = tk.Button(root, text="Stop", width=BTN_WIDTH, bg=BTN_BG, command=self.stopSimulation)
        self._stopBtn.pack()
        self._resetBtn = tk.Button(root, text="Reset", width=BTN_WIDTH, bg=BTN_BG, command=self.resetLevel)
        self._resetBtn.pack()
        self._debugBtn = tk.Button(root, text="Debug", width=BTN_WIDTH, bg=BTN_BG, command=self._level.log)
        self._debugBtn.pack()

    # Private methods
    def __checkCoord(self, x, y):
        return x <= 0 or y <= 0 or x >= CanvasView.WIDTH or y >= CanvasView.HEIGHT

    def __renewColony(self):
        self._colony = Colony(self._level, self.ANTS_COUNT)
        self._colony._members.addCallback(self.antMoved)

    # Canvas events handler
    def addWall(self, event):   # Called on mouse clicked and dragged
        if self.__checkCoord(event.x, event.y):
            return
        self._level.setWall(x=event.x//8, y=event.y//8)

    def addOrRemoveWall(self, event):   # Called on mouse clicked only
        if self.__checkCoord(event.x, event.y):
            return
        self._level.setOrUnsetWall(x=event.x//8, y=event.y//8) # Convert to level coordiantes using floor division

    # Buttons events handlers
    def resetLevel(self):
        result = tk.messagebox.askyesno("Confirmation", "Are You Sure?", icon='warning')
        if result == True:
            self.stopSimulation()
            self.__renewColony()
            self._level.reset()
            self._canvas.clear()

    def runSimulation(self):
        self._colony.explore()

    def stopSimulation(self):
        self._colony.genocide()
        self.__renewColony()

    # Models callbacks
    def antMoved(self, ant):
        self._canvas.repaintAnt(ant)

    def levelChanged(self, level):
        self._canvas.repaintLevel(level)


'''
classdoc
'''
class ControlsPanelController:

    def __init__(self, root):
        self._panel = ControlsPanelView(parent=root)
        self._panel.pack()


###############################
#   Views
###############################


'''
classdoc
'''
class CanvasView(tk.Canvas):

    WIDTH  = 640
    HEIGHT = 640

    WALL_COLOR = 'black'
    ANT_COLOR  = 'red'
    
    def __init__(self, parent):
        tk.Canvas.__init__(self, parent, width=self.WIDTH, height=self.HEIGHT)
        self._items = {}

    def repaintLevel(self, level):
        self.clear()    # Clear widget on each call
        for i in range(len(level)):
          for j in range(len(level[0])):
            if level[i][j] == Level.WALL:
              posX, posY = i*8, j*8
              self.create_rectangle(posX, posY, posX+8, posY+8, fill=self.WALL_COLOR)

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
class ControlsPanelView(tk.Frame):

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        tk.Label(text="Controls panel :").pack()


###############################
#   Welcome
###############################


'''
application frame
'''
class AppDelegate(tk.Frame):
    
    def __init__(self, root):
        lvl = Level()
        tk.Frame.__init__(self, root, bg='gray')
        self.__lolMsg()
        self._canvCtrl = CanvasController(root)
        self._ctrlsPanel = ControlsPanelController(root)

    def __lolMsg(self):
        print("Hi, i'm god")
        print("I am the owner of controllers")
        print("Dont fuck up with me or i'll freeze your ass bitch!")
        print("Oh, by the way, app initialized")


'''
mainloop
'''
def main():
    root = tk.Tk()
    app = AppDelegate(root)
    root.mainloop()

if __name__ == "__main__":
    main()



# GARBAGE ???
#items = ["Apple", "Banana", "Cherry"]
#self._list = tk.Listbox(root, width=8, height=8)
#for item in items:
#self._list.insert(tk.END, item)
#self._list.pack()
