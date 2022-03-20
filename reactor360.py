'''Программа для формирования картограммы размещения ТВЭЛ в узлах правильной треугольной решетки.
Позволяет создавать и редактировать расстановки с неограниченным числом типов ТВЭЛ,
а также различным образом манипулировать с расстановкой на координатной плоскости.
Расстановка хранится в файле в текстовом виде в формате:
1 строка: радиус ТВЭЛ, шаг решетки, внутренний радиус, внешний радиус [, смещение центра (x, y), угол поворота (град) ]
2 и далее: столбец, ряд, тип ТВЭЛ
Координаты хранятся в отдельных файлax для каждого типа твэл в текстовом виде в формате x,y

Управление: добавить/удалить элемент - левая кнопка мышки, изменение масштаба - колесико мышки, сдвижка экрана - перемещение мыши с зажатой правой кнопкой
'''
VERSION_INFO = "Версия 3.0 релиз Python\n (C)&(P) Ванюков Е.Е.\n\t2005 - 2022"

from random import randint
from tkinter import filedialog, messagebox, colorchooser, PhotoImage
from tkinter.ttk import Combobox
from tkinter import *
import math
import json
from pathlib import *
import shutil
import copy


#Системные параметры
ICON_NAME = 'reactor360.ico'
INI_FILE = 'reactor360.ini'
COS_60 = 0.5
SIN_60 = (3**0.5)/2
OUTPUT_FORMAT = "{:.4f},{:.4f}\n"  # формат сохранения координат
F_EXT = "tve"
DEFAULT_NAME = '' #'noname.' + F_EXT
PROGRAM_NAME = ' А.З. '
ACTIVE_COLOR = 'magenta'

# Меню
M_ARRANGE = 'Расстановка'
M_CREATE = 'Создать'
M_OPEN = 'Открыть...'
M_SAVE = 'Сохранить'
M_SAVE_AS = 'Сохранить как...'
M_SAVE_COORD = 'Сохранить координаты'
M_QUIT = "Выйти"
M_PUT = 'Твэл'
M_CLEAR = 'Очистить'
M_TVEL = 'тип '
M_TVEL_ADD_TYPE = "Добавить тип"
M_SERVIS = "Сервис"
M_ROTATE = "Повернуть"
M_MOVE_CENTER = "Сместить центр"
M_REBUILD = "Перестроить с другим шагом"
M_REFLECT = "Зеркально относительно Y"
M_RESET = "Вернуть в исходное"
M_BEAM = "Луч"
M_CIRCLE = "Окружность"
M_SCALE = "Изменить масштаб"
M_MARK = "Отметить твэл"
M_OPTIONS = "Настройки"
M_COLORS = "Цвета твэл"
M_HELP = "Помощь"
M_ABOUT = 'О программе'
M_VERSION = "Версия"
BASE_COLORS = ['white', 'red', 'green', 'yellow']
BASE_MENU = {M_ARRANGE: [M_CREATE, M_OPEN, M_SAVE, M_SAVE_AS, M_SAVE_COORD, M_QUIT],
                M_PUT: [M_CLEAR, M_TVEL_ADD_TYPE],
                M_SERVIS : [M_ROTATE, M_MOVE_CENTER, M_REFLECT, M_REBUILD, M_RESET, M_BEAM ,M_CIRCLE, M_SCALE,  M_MARK],  
                M_OPTIONS: [M_COLORS],
                M_HELP: [M_ABOUT, M_VERSION],
                }

#Параметры
PARAM_RADIUS = "Радиус твэл:"
PARAM_STEP = "Шаг решетки:"
PARAM_RIN = "Внутренний радиус:"
PARAM_ROUT = "Внешний радиус:"

parameters = [PARAM_RADIUS, PARAM_STEP, PARAM_RIN, PARAM_ROUT]

def data_consistency(r_tvel, step, r_in, r_out):
    return (r_tvel>0 and step>=2*r_tvel and r_in>=0 and r_out>r_in) 

def RGB(red,green,blue): return '#%02x%02x%02x' % (int(red), int(green) , int(blue))

def rand_color(): return RGB(randint(0,255), randint(0,255), randint(0,255))

def radius(x,y): return (x*x+y*y)**0.5

class Arrange():
    def __init__(self, r_tvel=0, step=0, r_in=0, r_out=0):
        self.tvel = {} # структура словарь: Ключ - тип ТВЭЛ, значения - список позиции ТВЭЛ
        self.tvel_marked =set()
        self.flag_changed = False
        self.r_tvel = r_tvel
        self.r_in = r_in
        self.r_out = r_out
        self.step = step
        self.position = [0, 0]
        self.rotation = 0
    
    def get_tvel(self, i, j):
        for key in self.tvel:
            if (i, j) in self.tvel[key]:
                return key
    
    def add(self, i, j, type):
        self.pop(i, j)
        if type not in self.tvel:
            self.tvel[type]=[]
        self.tvel[type].append((i, j))
    
    def pop(self, i, j):
        key = self.get_tvel(i, j)
        if key:
            self.tvel[key].remove((i, j))
        if self.tvel.get(key) == []:
            self.tvel.pop(key) 
        
    def get_quantity(self, i):
        if i in self.tvel:
            return len(self.tvel[i])
        else:
            return 0
    
    def get_size(self):
        number = 0
        for key in self.tvel:
            number += self.get_quantity(key)
        return number
      
    def get_tvel_types(self):
        tmp = list(self.tvel.keys())
        if tmp!=[]:
            return max(tmp) #возвращает максимальный значение типа твел, при создании меню и обработке количества ТВЭЛ учитывать, что нумерация типов с 1 (т.е. +1 к длине списка)
        else:
            return 0
    
    def get_values(self):
        #return list(set().union(*list(self.tvel.values()))) # в старой версии для множеств
        return sum(list(self.tvel.values()), [])

    @classmethod
    def open(cls, filename):
        if filename=='':
            return None
        try:
            with open(filename,'r') as f:
                line = f.readline().rstrip().split(",")
                # first line - tvel radius, step, radius inner, radius out [, position(list), angle_of_rotation ]
                data=[float(line[i]) for i in range(len(line))]
                if data_consistency(*data[0:4]):
                    tmp=Arrange(*data[0:4])
                    if(len(data)>4): # в старых версиях position(list), angle_of_rotation в файле данных отсутствовало, для совместимости
                        tmp.position=data[-3:-1]
                        tmp.rotation=data[-1]
                    for line in f:
                        data = line.rstrip().split(",")
                        tmp.add(int(data[0]), int(data[1]),int(data[2])) # x, y, tvel type
                else:
                    messagebox.showerror(
                        "Ошибка чтения файла!",
                        "Несогласованные данные!")
                    return None
            return tmp
        except:
            messagebox.showerror(
            "Ошибка чтения файла!",
            "Неверный формат или файл не существует!")
            return None

    def save(self, filename):
        newdir = filename.split('/')[-1].replace("." + F_EXT, '' )
        outpath = Path(filename).parent / newdir
        shutil.rmtree(outpath, ignore_errors =True) # удаляем директорию со старыми данными координат, чтобы сохранение координат и расстановки были синхронизированы
        try:
            with open(filename,'w') as f:
                f.write("{},{},{},{},{},{},{}\n".format(self.r_tvel, self.step, self.r_in, self.r_out, self.position[0], self.position[1], self.rotation))
                for key in self.tvel:
                    for data in self.tvel[key]:
                        f.write("{},{},{}\n".format(data[0], data[1], key )) # x, y, tvel type
            return True
        except:
            messagebox.showerror("Ошибка записи файла!")
    
    def save_coord(self, filename):
        newdir = filename.split('/')[-1].replace("." + F_EXT, '' )
        outpath = Path(filename).parent / newdir
        shutil.rmtree(outpath, ignore_errors =True) # удаляем директорию со старыми данными координат
        outpath.mkdir()
        try:
            files = {key: open("{}/{}.{}{}".format(outpath, newdir, F_EXT, key), 'w') for key in self.tvel}
            for key in self.tvel:
                for item in self.tvel[key]:
                    files[key].write(OUTPUT_FORMAT.format(*self.get_coord(*item))) # x, y type
            for i in files:
                files[i].close()
            if(len(self.tvel_marked) != 0):
                with open("{}/{}.{}".format(outpath, newdir,'mrkd') , 'w') as f:
                    for item in self.tvel_marked:
                        f.write(OUTPUT_FORMAT.format(*self.get_coord(*item))) # x, y type
            return True
        except:
            messagebox.showerror("Ошибка записи файлoв!")

    @classmethod
    def new(cls, r_tvel, step, r_in, r_out):
        if data_consistency(r_tvel, step, r_in, r_out):
            tmp = Arrange(r_tvel, step, r_in, r_out)
            index = int(tmp.r_out/(tmp.step*SIN_60) + 1)
            for i in range(-index, index + 1):
                for j in range(-index, index + 1):
                    r = radius(*tmp.get_coord(i, j))
                    if (r + tmp.r_tvel <= tmp.r_out):
                        if (r - tmp.r_tvel >= tmp.r_in) or (r_in==0.0):
                            tmp.add(i,j ,1)
            if tmp.tvel!={}:    
                return tmp
        else:
            messagebox.showerror("Ошибка ввода данных!", "Несогласованне данные!")
            return None
    
    def get_coord(self, i, j):
        x0 = i * self.step * SIN_60 + self.position[0]
        y0 = (j + i % 2 * COS_60) * self.step + self.position[1]
        angle= self.rotation/180*math.pi
        x = x0 * math.cos(angle) - y0 * math.sin(angle)
        y = x0 * math.sin(angle) + y0 * math.cos(angle)
        return x, y

    def get_index(self, x, y):
        angle= -self.rotation/180*math.pi
        x0 = x * math.cos(angle) - y * math.sin(angle) - self.position[0]
        y0 = x * math.sin(angle) + y * math.cos(angle) - self.position[1]
        i = round(x0/ self.step/ SIN_60)
        j = round(y0/ self.step - i % 2 * COS_60)
        return i, j
    

class ServiceDialog():
    def __init__(self, parrent, *args, title = "", geometry = "250x250+200+200", func = lambda: True):
        self.dlg = Toplevel(parrent, bd = 3)
        self.dlg.title(title)
        self.dlg.geometry(geometry)
        self.dlg.resizable(width = False, height= False)
        if (Path(ICON_NAME).exists()):
            self.dlg.iconbitmap(ICON_NAME)
        self.dlg.grab_set()
        #self.window = Label(self.dlg)
        labels = []
        self.entrys = []
        for i in range(len(args)):
            labels.append(Label(self.dlg, text = args[i]))
            #label_r.place(relx=0, rely=0.5, height=20, width=100)
            labels[i].pack(pady=5)
            self.entrys.append(Entry(self.dlg, width=10))
            self.entrys[i].pack(pady=3)
        
        self.entrys[0].focus_set() 
        self.entrys[len(self.entrys)-1].bind("<Return>", lambda obj=self: func(self))
              
        button_ok = Button( self.dlg, text = "Ок", command = lambda obj=self: func(self)) 
        button_ok.bind("<Return>", lambda obj=self: func(self))
        button_ok.pack(side='left', pady = 10, padx=20)
        button_cancel = Button(self.dlg, text="Отмена", command = self.destroy) 
        button_cancel.bind("<Return>", self.destroy)
        button_cancel.pack(side='right',pady = 10, padx=20)
        self.dlg.bind("<Escape>", self.destroy)
    
    def get_value(self):
        try:
            return [float(i.get()) for i in self.entrys]
        except:
            messagebox.showerror("Ошибка типа данных!", "Попробуйте еще раз...")
    
    def destroy(self, *args):
        self.dlg.destroy()
       

class ResizingCanvas(Canvas):
    def __init__(self,parent,**kwargs):
        Canvas.__init__(self,parent,**kwargs)
        self.bind("<Configure>", self.on_resize)
        self.height = self.winfo_reqheight()
        self.width = self.winfo_reqwidth()
        self.parent = parent
        self.x0 = 0
        self.y0 = 0

    def on_resize(self,event):
        # determine the ratio of old width/height to new width/height
        wscale = float(event.width)/self.width
        hscale = float(event.height)/self.height

        self.width = event.width 
        self.height = event.height 

        # resize the canvas 
        self.config(width=self.width, height=self.height)
        # rescale all the objects tagged with the "all" tag
        # self.scale("all",0,0,wscale,hscale)
        if(self.parent.arrange != None):
            self.parent.get_scale()
            self.set_center()
            self.parent.draw_arrange()
    
    def get_center(self):
        return self.width/2 + self.x0, self.height/2 - self.y0
    
    def set_center(self, *args):
        if args == ():
            self.x0 = 0
            self.y0 = 0
        else:
            self.x0 = args[0]
            self.y0 = args[1]

class App(Tk):
    global parameters
    menuitem={}

    def __init__(self):
        super().__init__()
        self.configure(bg='blue')
        self.title( PROGRAM_NAME + " - " + DEFAULT_NAME)
        if (Path(ICON_NAME).exists()):
            #print(ICON_NAME)
            #self.tk.call('wm', 'iconphoto', self._w, PhotoImage(file=ICON_NAME))
            #self.iconphoto(False, PhotoImage(file = "reactor360.png"))
            self.iconbitmap(ICON_NAME)
        else:
            print("No icon")
            pass
        screen_height=int(self.wm_maxsize()[1])  # получаем размер экрана и вычисляем размер окна приложения
        self.start_position_askdialog="+{}+{}".format(int(screen_height/3), int(screen_height/3))
        self.geometry('{}x{}+{}+{}'.format(int(screen_height*0.9), int(screen_height*0.9), 0, 0))
        #self.state("zoomed") #- окно на весь экран над панелью задач
        self.minsize(400, 400)
        self.arrange = None 
        self.scale = 0
        self.filename = ''
        self.mouse_position=[0,0]
        self.mouse_xy = ()
        self.last_dir = Path.cwd()
        self.colors = BASE_COLORS
        self.tvel_types = ["{}{}".format(M_TVEL,i) for i in range(len(self.colors))]
        self.menu_ = BASE_MENU
        self.menu_[M_PUT] = [M_CLEAR, *[self.tvel_types[i] for i in range(1,len(self.tvel_types))], M_TVEL_ADD_TYPE]
        
        self.screen = ResizingCanvas(self, bg='white')
        self.statusbar = Label(self, text="  No data", bd=3, relief=SUNKEN, anchor=W, font="Arial 10")
        self.statusbar.pack(side=BOTTOM, fill=X)
        self.screen.pack(fill="both", expand=True)
        self.screen.bind("<Button-1>", self.mouse_pressed)
        self.screen.bind("<Motion>", self.mouse_move)
        self.screen.bind("<MouseWheel>", self.mouse_wheel)
        self.screen.bind("<Button-3>", self.mouse_B3)
        self.screen.bind("<B3-Motion>", self.mouse_B3motion)

       
        self.load_ini()
        # create menu
        self.mainmenu = Menu(self, bd=3)
        self.tvel_var = IntVar()
        self.mark = BooleanVar(False)
        self.tvel_var.set(0)
        
        for key in self.menu_:
            App.menuitem[key] = Menu(self.mainmenu, tearoff=0, bd=1)
            if key!=M_PUT:
                for tag in self.menu_[key]:
                    if tag!=M_MARK:
                        App.menuitem[key].add_command(label=tag, command=lambda x=tag: self.callback(x)) #https://webdevblog.ru/kak-ispolzovat-v-python-lyambda-funkcii/ - почему lambda надо писать так
                    else:
                        App.menuitem[key].add_checkbutton(label=tag, variable = self.mark)
            else:
                self.create_menu_tvel()
            self.mainmenu.add_cascade(label=key, menu=App.menuitem[key])
        
        self.config(menu=self.mainmenu)

    def update(self):
        titlename = PROGRAM_NAME + " - " + self.filename
        self.title(titlename)
        status = "  No data"
        if (self.arrange):
            current_tvel_type = self.arrange.get_tvel(*self.mouse_position)
            current_tvel_type = "пусто" if current_tvel_type == None else M_TVEL + str(current_tvel_type)
            status = "Радиус твэл: {RTVEL}  Шаг: {STEP}  Rin: {RIN}  Rout: {ROUT}".format(
                RTVEL = self.arrange.r_tvel, STEP = self.arrange.step, RIN = self.arrange.r_in, ROUT = self.arrange.r_out) + \
                "  Центр: {CNTR}  Поворот: {ANGLE}  Указатель на {curtvel}  X= {X:.4f}  Y= {Y:.4f}  столбец= {COLUMN}  ряд= {LINE}".format(
                    CNTR =self.arrange.position, COLUMN = self.mouse_position[0], LINE = self.mouse_position[1], ANGLE = self.arrange.rotation, curtvel = current_tvel_type,
                    X = self.arrange.get_coord(*self.mouse_position)[0], Y = self.arrange.get_coord(*self.mouse_position)[1]) + \
                        "   Количество элементов: {NUM}".format(NUM = len(self.arrange.get_values()))
            for i in range(1, self.arrange.get_tvel_types() + 1):
                num = self.arrange.get_quantity(i)
                if num != 0:
                    status += "  "+ self.tvel_types[i]+": "+str(num)
            if self.mark.get():
                status = "РЕЖИМ ПОМЕТКИ\t" + status
            else:
                status = "РЕЖИМ РАССТАНОВКИ\t" + status
        self.statusbar['text'] = status
        
    def load_ini(self):
        #global COLORS, TVEL
        try:
            with open(INI_FILE,'r') as f:
                self.last_dir = f.readline().rstrip()
                self.colors = json.loads(f.readline())
                self.tvel_types = ["{}{}".format(M_TVEL,i) for i in range(len(self.colors))]
                self.menu_[M_PUT] = [M_CLEAR, *[self.tvel_types[i] for i in range(1,len(self.colors))], M_TVEL_ADD_TYPE]
        except:
            print("Ошибка чтения ini файла")
        
    def save_ini(self):
        try:
            with open(INI_FILE,'w') as f:
                f.write("{}\n".format(self.last_dir))
                f.write("{}".format(json.dumps(self.colors)))
        except:
            pass
        
    def create_menu_tvel(self):
        add_pos=len(self.menu_[M_PUT])-1
        for tag in range(add_pos):
            App.menuitem[M_PUT].add_radiobutton(label=self.menu_[M_PUT][tag], variable=self.tvel_var, value=tag)#: добавляет в меню переключатель
        App.menuitem[M_PUT].add_command(label=self.menu_[M_PUT][add_pos], command=self.add_menu_tvel)

    def add_menu_tvel(self):
        (rgb, hx) = colorchooser.askcolor(title = "Выберите цвет для нового типа твел")
        if (rgb!= None):
            self.colors.append(RGB(*rgb))
            add_pos = len(self.menu_[M_PUT])-1
            for tag in range(add_pos+1):
                App.menuitem[M_PUT].delete(self.menu_[M_PUT][tag]) #удаляем старые пункты
            self.menu_[M_PUT].insert(add_pos, "{}{}".format(M_TVEL, add_pos))
            self.tvel_var.set(add_pos)
            self.tvel_types.append("{}{}".format(M_TVEL,add_pos)) #"{}{}".format(M_TVEL,i) for i in range(0,len(self.colors))
            self.create_menu_tvel()
    
    def mark_tvel(self):
        self.mark.set(not self.mark.get())

    def mouse_wheel(self, event):
        if self.arrange != None:
            self.scale *= (1+event.delta/120*0.03)
            self.draw_arrange()
    
    def mouse_B3motion(self, event):
        if self.arrange != None:
            self.screen.set_center(event.x - self.mouse_xy[0], -(event.y - self.mouse_xy[1]))
            self.draw_arrange()

    def mouse_B3(self, event):
        self.mouse_xy = (event.x, event.y)

    def mouse_pressed(self, event):
        tvel_type = self.tvel_var.get()
        if(self.arrange):
            x0, y0 = self.screen.get_center()
            i, j = self.arrange.get_index((event.x - x0)/self.scale, (y0-event.y)/self.scale)
            x, y = self.arrange.get_coord(i, j)
                
            if (not self.mark.get()):
                if tvel_type != 0:
                    self.arrange.add(i, j, tvel_type)
                    self.circle(x, y, self.arrange.r_tvel, width=1, outline='black', activefill = ACTIVE_COLOR, fill = self.colors[tvel_type])
                    if (i, j) in self.arrange.tvel_marked:
                        self.draw_mark(x, y)
                else:
                    self.arrange.pop(i, j)
                    self.circle(x, y, self.arrange.r_tvel, width=1, outline= self.screen['background'], fill = self.screen['background'])
            else:
                if self.arrange.get_tvel(i, j):
                    if (i,j) not in self.arrange.tvel_marked:
                        self.arrange.tvel_marked.add((i, j))
                        #помечаем на экране
                        self.draw_mark(x, y)
                    else:
                        self.arrange.tvel_marked.remove((i, j))
                        self.circle(x, y, self.arrange.r_tvel, width=1, outline='black', activefill = ACTIVE_COLOR, fill = self.colors[self.arrange.get_tvel(i, j)]) #activefill = ACTIVE_COLOR,
        self.update()
    
    def draw_mark(self, x, y):
        x0, y0 = self.screen.get_center()
        self.screen.create_line(x0 + (x - self.arrange.r_tvel/2) * self.scale, y0 - y*self.scale,
                                                x0 + (x + self.arrange.r_tvel/2) * self.scale, y0 - y*self.scale, width=2, fill ='black')
        self.screen.create_line(x0 + x * self.scale, y0 - (y - self.arrange.r_tvel/2) * self.scale,
                                                x0 + x * self.scale, y0 - (y + self.arrange.r_tvel/2) * self. scale, width=2, fill ='black')

    def mouse_move(self,  event):
        if(self.arrange):
            x0, y0 = self.screen.get_center()
            i, j = self.arrange.get_index((event.x - x0)/self.scale, (y0-event.y)/self.scale)
            if [i,j] !=self.mouse_position:
                x, y = self.arrange.get_coord(i, j)
                if (i,j) not in self.arrange.tvel:
                    x, y = self.arrange.get_coord(i, j)
                    self.circle(x, y, self.arrange.r_tvel, width=1, outline='black')
                if self.arrange.get_tvel(*self.mouse_position) == None:
                    x, y = self.arrange.get_coord(*self.mouse_position)
                    self.circle(x, y, self.arrange.r_tvel, width=1, outline= self.screen['background'])
                self.mouse_position = [i,j]
        self.update()
       
    def circle(self, x , y , radius, fill=None, width=1, outline='black', dash = None , activefill = None):
        scale=self.scale
        x0, y0 = self.screen.get_center()
        self.screen.create_oval( (x0 + x * scale) - radius * scale,
                                (y0 - y * scale) - radius * scale,
                                (x0 + x * scale) + radius * scale,
                                (y0 - y * scale) + radius * scale,
                                width= width, outline= outline, fill=fill, dash = dash, activefill = activefill)

    def draw_arrange(self):
        if (self.arrange != None):
            scale = self.scale
            self.screen.delete("all")            #очистить экран
            x0, y0 = self.screen.get_center()
            self.screen.create_line(x0, y0, x0 + 2*scale, y0 , arrow='last', arrowshape=(scale/2,scale/2*1/0.8, scale/2*0.2/0.8))  # arrowshape see https://anzeljg.github.io/rin2/book2/2405/docs/tkinter/create_line.html
            self.screen.create_line(x0, y0, x0 , y0 - 2*scale , arrow='last', arrowshape=(scale/2,scale/2*1/0.8, scale/2*0.2/0.8))
            self.circle(0, 0, self.arrange.r_out, width=2, outline='black', dash = int(scale))
            self.circle(0, 0, self.arrange.r_in, width=2, outline='black', dash = int(scale))
            
            for item in self.arrange.get_values():
                x, y = self.arrange.get_coord(*item)
                a = self.colors[self.arrange.get_tvel(*item)]
                self.circle(x, y, self.arrange.r_tvel, width=1, outline='black', activefill = ACTIVE_COLOR, fill = self.colors[self.arrange.get_tvel(*item)])
            for item in self.arrange.tvel_marked:
                self.draw_mark(*self.arrange.get_coord(*item))
 
    def get_scale(self):
        if (self.arrange!= None):
            max_radius = max(*[radius(*self.arrange.get_coord(*item)) for item in self.arrange.get_values()], self.arrange.r_out)
            if (self.arrange.r_out != 0):
                self.scale = min(self.screen.width, self.screen.height) / (2*max_radius + self.arrange.step)

    def create(self):
        def ok(object):
            data = object.get_value()
            tmp = Arrange.new(*data)
            if tmp:
                object.destroy()
                self.arrange=tmp
                self.filename=''
                self.get_scale()
                self.draw_arrange()
            else:
                messagebox.showerror(
                    "Ошибка ввода данных!",
                    "При данных параметрах расстановка не содержит твелов!")
        dlg = ServiceDialog(self, *parameters, title = M_CREATE, geometry = '280x300' + self.start_position_askdialog, func = ok)

    def rebuild_new_step(self):
        def ok(object):
            tmp = object.get_value()[0]
            if (tmp<2*self.arrange.r_tvel):
                messagebox.showerror(
                    "Ошибка ввода данных!",
                    "Недопустимо, пересечение твелов!")
            else:
                self.arrange.step = tmp
                object.destroy()
                self.get_scale()
                self.draw_arrange()
        if self.arrange:
            dlg = ServiceDialog(self, "Введите новый шаг", title = M_REBUILD, geometry = '250x120' + self.start_position_askdialog, func = ok)
    
    def draw_beam(self):
        def ok(object):
            angle = object.get_value()[0]
            x0, y0 = self.screen.get_center()
            scale = self.scale
            self.screen.create_line(x0, y0, x0 * (1 + math.cos(angle/180*math.pi)), y0 *(1 - math.sin(angle/180*math.pi)) , dash = int(scale))
            object.destroy()
        if self.arrange:
            dlg = ServiceDialog(self, "Введите угол наклона луча", title = M_BEAM, geometry = '250x120' + self.start_position_askdialog, func = ok)
   
    def draw_circle(self):
        def ok(object):
            tmp = object.get_value()[0]
            if (tmp>0.0):
                object.destroy()
                self.circle(0, 0, tmp, width=2, outline='black', dash = int(self.scale))
            else:
                messagebox.showerror(
                    "Ошибка ввода данных!",
                    "Требуется положительное значение!")
        if self.arrange:
            dlg = ServiceDialog(self, "Введите радиус окружности", title = M_CIRCLE, geometry = '250x120' + self.start_position_askdialog, func = ok)
    
    def rotate(self):
        def ok(object):
            self.arrange.rotation += object.get_value()[0]
            object.destroy()
            self.draw_arrange()
        if self.arrange:
            dlg = ServiceDialog(self, "Введите угол поворота", title = M_ROTATE, geometry = '250x120' + self.start_position_askdialog, func = ok)

    def change_scale(self):
        def ok(object):
            tmp = object.get_value()[0]
            if (tmp>0.0):
                self.scale *= tmp
                object.destroy()
                self.draw_arrange()
            else:
                messagebox.showerror(
                    "Ошибка ввода данных!",
                    "Требуется положительное значение!")
        if self.arrange:
            dlg = ServiceDialog(self, "Введите изменение масштаба", title = M_SCALE, geometry = '250x120' + self.start_position_askdialog, func = ok)

    def move_center(self):
        def ok(object):
            self.arrange.position[0] += object.get_value()[0]
            self.arrange.position[1] += object.get_value()[1]
            object.destroy()
            self.get_scale()
            self.draw_arrange()
        if self.arrange:
            dlg = ServiceDialog(self, "Смещение по X", "Смещение по Y", title = M_MOVE_CENTER, geometry = '250x200' + self.start_position_askdialog, func = ok)

    def reflect(self):
        if self.arrange:
            tmp = copy.deepcopy(self.arrange)
            for item in self.arrange.get_values():
                tmp.add(-item[0], item[1], self.arrange.get_tvel(*item))
            self.arrange = tmp    

            self.draw_arrange()

    def reset(self):
        if self.arrange:
            self.arrange.rotation = 0
            self.arrange.position = [0, 0]
            self.screen.set_center()
            self.get_scale()
            self.draw_arrange()

    def choose_colors(self):
        def get_choice(event):
            tvel_type = combo_choice.get()
            num = int(tvel_type[len(M_TVEL):])
            color_tvel.config(bg=self.colors[num])
            
        def change_color():
            tvel_type = combo_choice.get()
            num = int(tvel_type[len(M_TVEL):])
            (rgb, hx) = colorchooser.askcolor(title = "Выберите цвет")
            # print(rgb) 
            if (rgb!= None):
                self.colors[num] = RGB(*rgb)
            color_tvel.config(bg=self.colors[num])
            self.draw_arrange()
        
        def close(*args):
            dialog.destroy()
            #self.draw_arrange()
            
        dialog = Toplevel(self, bd = 3 ) 
        dialog.geometry('280x100'+self.start_position_askdialog)
        dialog.title("Выбрать цвета")
        dialog.focus_set()
        if (Path(ICON_NAME).exists()):
            dialog.iconbitmap(ICON_NAME)
        dialog.grab_set()
        dialog.protocol("WM_DELETE_WINDOW", close)
        dialog.resizable(width = False, height= False)
        color_tvel=Button(dialog, width = 1, height= 1, bg= self.colors[1], command = change_color)
        color_tvel.place(relx=0.8, rely=0.18)
        Button(dialog, text = "Ок", width= 10, command = close).place(relx=0.35, rely=0.65)
        combo_choice = Combobox(dialog, values=self.menu_[M_PUT][1:-1], state = 'readonly')
        combo_choice.current(0)
        combo_choice.place(relx=0.1, rely=0.23)
        combo_choice.bind("<<ComboboxSelected>>", get_choice)
        dialog.bind("<Escape>", close)        
       
    def show_version(self):
        messagebox.showinfo(title = PROGRAM_NAME, message = VERSION_INFO)       
    
    def show_about(self):
        messagebox.showinfo(title = PROGRAM_NAME, message = __doc__)       

    def open_file(self):
        temp_filename =  filedialog.askopenfilename(initialdir = self.last_dir, title = "Выберите файл",filetypes = (("tvel files","*.{}".format(F_EXT)),("all files","*.*")))
        tmp = Arrange.open(temp_filename) 
        if tmp:
            self.arrange = tmp
            num_colors = len(self.colors) - 1   #актуальные цвета для твэлов в списке self.colors с 1-ой позиции
            if self.arrange.get_tvel_types() > num_colors:
                self.tvel_types.extend(["{}{}".format(M_TVEL,i) for i in range(num_colors+1, self.arrange.get_tvel_types()+1)])
                self.colors.extend([rand_color() for _ in range(num_colors+1, self.arrange.get_tvel_types()+1)])
                # перерисовываем меню 
                for tag in range(len(self.menu_[M_PUT])):
                    App.menuitem[M_PUT].delete(self.menu_[M_PUT][tag]) #удаляем старые пункты
                self.menu_[M_PUT] = [M_CLEAR, *[self.tvel_types[i] for i in range(1,len(self.tvel_types))], M_TVEL_ADD_TYPE]
                self.create_menu_tvel()
            self.config(menu=self.mainmenu)
            self.get_scale()
            self.draw_arrange()
            self.filename = temp_filename
            self.last_dir = Path(self.filename).parent  #https://python-scripts.com/pathlib

   
    def save_coord(self):
        if (self.arrange):
            if self.filename=='':
                messagebox.showinfo(title = M_SAVE_COORD, message = "Сначала сохраните расстановку!")   
                self.save_as_file()
                self.save_coord()
            else:
                if (self.arrange.save(self.filename) and self.arrange.save_coord(self.filename)):
                    messagebox.showinfo(title = M_SAVE_COORD, message = "Координаты и расстановка сохранены!") 
        
    def save(self):
        if (self.arrange):
            if self.filename=='':
                self.save_as_file()
            else:
                if (self.arrange.save(self.filename)):
                    messagebox.showinfo(title = M_SAVE, message = "Расстановка сохранена!") 

    def save_as_file(self):
        if (self.arrange):
            filename =  filedialog.asksaveasfilename(initialdir = self.last_dir, title = "Выберите файл",
                                                        filetypes = (("tvel files","*.{}".format(F_EXT)),("all files","*.*")))
            if(filename!=''):
                if ".{}".format(F_EXT) not in filename:
                    filename +=".{}".format(F_EXT)
                self.last_dir = Path(filename).parent
                self.filename=filename
                self.save()

    def quit(self):
        answer = True
        if (self.arrange != None):
            answer = messagebox.askokcancel("Выйти", "Вы точно хотите закончить работу программы?")
        if answer:
            self.save_ini()
            self.destroy()

    def callback(self, tag):
        if tag == M_CREATE:
            self.create()
        if tag == M_OPEN:
            self.open_file()
        if tag == M_SAVE:
            self.save()
        if tag == M_SAVE_AS:
            self.save_as_file()
        if tag == M_SAVE_COORD:
            self.save_coord()
        if tag == M_QUIT:
            return self.quit() # return, чтобы после уничтожения окна не вызывался self.update
        if tag == M_MOVE_CENTER:
            self.move_center()
        if tag == M_REBUILD:
            self.rebuild_new_step()
        if tag == M_SCALE:
            self.change_scale()
        if tag == M_ROTATE:
            self.rotate()
        if tag == M_REFLECT:
            self.reflect()
        if tag == M_RESET:
            self.reset()
        if tag == M_BEAM:
            self.draw_beam()
        if tag == M_CIRCLE:
            self.draw_circle()
        if tag == M_MARK:
            self.mark_tvel()
        if tag == M_COLORS:
            self.choose_colors()
        if tag == M_VERSION:
            self.show_version()
        if tag == M_ABOUT:
            self.show_about()
        self.update()
    

if (__name__ == "__main__"):
    app=App()
    app.protocol('WM_DELETE_WINDOW', app.quit)
    app.mainloop()

