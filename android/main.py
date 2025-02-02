from calc import CalculatorWidget,Button
from kivy.config import Config
from album import Album,Folder
from clock import MyClockWidget,Ticks
from gallery import Pictures
from paint import Painter
from drawboard import DrawBoard, Fold
from camera import Camera
from copy import copy
from kivy.app import App
from kivy.clock import Clock
from functools import partial
from kivy.lang import Builder
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.screenmanager import ScreenManager,Screen,FadeTransition
from kivy.properties import NumericProperty, ListProperty, ObjectProperty, DictProperty
import socket
import datetime
import random 
import sys,os

'''Window.borderless=1
Window.left=100
Window.top=100
Window.hieght=200
'''
KV = '''
#:import pi math.pi
#:import cos math.cos
#:import sin math.sin
#:import V kivy.vector.Vector
<ModernMenu>:
    canvas.before:
        Color:
            rgba: .505, .647, .776, .9
        Ellipse:
            pos: self.center_x - self.radius, self.center_y - self.radius
            size: self.radius * 2, self.radius * 2
            angle_start: 0
            angle_end: self.circle_progress * 360 * self.creation_direction
        Color:
            rgba: self.color
        Line:
            circle:
                (
                self.center_x, self.center_y,
                self.radius, 0, self.circle_progress * 360 * self.creation_direction
                )
            width: self.line_width
    on_touch_down:
        V(args[1].pos).distance(self.center) < self.radius and (
        self.back() if self.choices_history else self.dismiss())
<ModernMenuLabel>:
    size: self.texture_size
    padding: 5, 5
    font_size: 50
    color:.31, .573, .816, .9
    on_press: self.callback and self.callback(self)
    canvas.before:
        Color:
            rgba: .31, .573, .816, .9
        Line:
            points:
                self.pos,(self.pos[0],self.pos[1]+self.size[1]),(self.pos[0]+self.size[0],self.pos[1]+self.size[1]),(self.pos[0]+self.size[0],self.pos[1]),self.pos
            width:self.parent.line_width if self.parent else 1
        Line:
            points:
                (
                (self.center_x+self.parent.center_x + cos(
                self.opacity * self.index * 2 * pi / self.siblings
                ) * self.parent.radius)/2, (self.center_y+self.parent.center_y + sin(
                self.opacity * self.index * 2 * pi / self.siblings
                ) * self.parent.radius)/2,
                self.parent.center_x + cos(
                self.opacity * self.index * 2 * pi / self.siblings
                ) * self.parent.radius,
                self.parent.center_y + sin(
                self.opacity * self.index * 2 * pi / self.siblings
                ) * self.parent.radius
                ) if self.parent else []
            width: self.parent.line_width if self.parent else 1
    center:
        (
        self.parent.center_x +
        cos(self.opacity * self.index * 2 * pi / self.siblings) * self.radius,
        self.parent.center_y +
        sin(self.opacity * self.index * 2 * pi / self.siblings) * self.radius
        ) if (self.size and self.parent and self.parent.children) else (0, 0)
'''


def dist(x,y):
    (x1, y1),(x2,y2)=x,y

    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5


class ModernMenuLabel(ButtonBehavior, Label):
    index = NumericProperty(0)
    radius = NumericProperty(250)
    siblings = NumericProperty(1)
    callback = ObjectProperty(None)
    
    def on_parent(self, *args):
        if self.parent:
            self.parent.bind(children=self.update_siblings)

    def update_siblings(self, *args):
        if self.parent:
            self.siblings = max(0, len(self.parent.children))
        else:
            self.siblings = 1

class ModernMenu(Widget):
    radius = NumericProperty(50)
    circle_width = NumericProperty(5)
    line_width = NumericProperty(2)
    color = ListProperty([.31, .573, .816, .9])
    circle_progress = NumericProperty(0)
    creation_direction = NumericProperty(1)
    creation_timeout = NumericProperty(1)
    choices = ListProperty([])
    item_cls = ObjectProperty(ModernMenuLabel)
    item_args = DictProperty({'opacity': 0})
    animation = ObjectProperty(Animation(opacity=1, d=.5))
    choices_history = ListProperty([])

    def start_display(self, touch):
        touch.grab(self)
        a = Animation(circle_progress=1, d=self.creation_timeout)
        a.bind(on_complete=self.open_menu)
        touch.ud['animation'] = a
        a.start(self)

    def open_menu(self, *args):
        self.clear_widgets()
        for i in self.choices:
            kwargs = copy(self.item_args)
            kwargs.update(i)
            ml = self.item_cls(**kwargs)
            self.animation.start(ml)
            self.add_widget(ml)

    def open_submenu(self, choices, *args):
        self.choices_history.append(self.choices)
        self.choices = choices
        self.open_menu()


    def back(self, *args):
        self.choices = self.choices_history.pop()
        self.open_menu()

    def on_touch_move(self, touch, *args):
        if (
            touch.grab_current == self and
            dist(touch.pos, touch.opos) > self.radius and
            self.parent and
            self.circle_progress < 1
        ):
            self.parent.remove_widget(self)

        return True

    def on_touch_up(self, touch, *args):
        if (
            touch.grab_current == self and
            self.parent and
            self.circle_progress < 1
        ):
            self.parent.remove_widget(self)
        return True

    def dismiss(self):
        a = Animation(opacity=0)
        a.bind(on_complete=self._remove)
        a.start(self)

    def _remove(self, *args):
        if self.parent:
            self.parent.remove_widget(self)


class MenuSpawner(Widget):
    timeout = NumericProperty(0)
    menu_cls = ObjectProperty(ModernMenu)
    cancel_distance = NumericProperty(10)
    menu_args = DictProperty({})

    def on_touch_down(self, touch, *args):
        t = partial(self.display_menu, touch)
        touch.ud['menu_timeout'] = t
        Clock.schedule_once(t, self.timeout)
        return super(MenuSpawner, self).on_touch_down(touch, *args)

    def on_touch_move(self, touch, *args):
        try:
            if (
            touch.ud['menu_timeout'] and dist(touch.pos, touch.opos) > self.cancel_distance):
                Clock.unschedule(touch.ud['menu_timeout'])
        except Exception:
            pass
        return super(MenuSpawner, self).on_touch_move(touch, *args)

    def on_touch_up(self, touch, *args):
        if touch.ud.get('menu_timeout'):
            Clock.unschedule(touch.ud['menu_timeout'])
        return super(MenuSpawner, self).on_touch_up(touch, *args)

    def display_menu(self, touch, dt):
        menu = self.menu_cls(center=touch.pos, **self.menu_args)
        self.add_widget(menu)
        menu.start_display(touch)


class Home(Screen):
    Builder.load_file("kv/home.kv")
    
Builder.load_string(KV)
Builder.load_file("kv/calculator.kv")
Builder.load_file("kv/gallery.kv")
Builder.load_file("kv/album.kv")
Builder.load_file("kv/paint.kv")
Builder.load_file("kv/drawboard.kv")

class ModernMenuApp(App):
    def build(self):
        #Config.set('input', 'default', 'tuio,192.168.43.8:3334')
        self.sm=ScreenManager(transition=FadeTransition())
        self.sm.add_widget(Home(name='home'))
        self.sm.add_widget(CalculatorWidget(name='calculator'))
        self.sm.add_widget(MyClockWidget(name='clock'))
        self.sm.add_widget(Pictures(name='pictures'))
        self.sm.add_widget(DrawBoard(name='drawboard'))
        self.sm.add_widget(Painter(name='paint'))
        self.sm.add_widget(Album(name='album'))
        self.sm.add_widget(Camera(name='camera'))
        self.sm.current="drawboard"
        return self.sm

    def calculator(self, *args):
        args[0].parent.dismiss()
        self.sm.current="calculator"

    def camera(self, *args):
        args[0].parent.dismiss()
        self.sm.current="camera"   
        
    def paint(self, *args):
        args[0].parent.dismiss()
        self.sm.current="drawboard"
    
    def clock(self, *args):
        args[0].parent.dismiss()
        
        self.sm.current="clock"

    def pictures(self, *args):
        args[0].parent.dismiss()
        self.sm.current="album"

    def callback(self, *args):
        args[0].parent.dismiss()

    def callback3(self, *args):
        print ("test 3")
        args[0].parent.dismiss()

    def devolopers(self, *args):
        
        args[0].parent.open_submenu(
            choices=[
                dict(text='Anu A', index=1, callback=self.callback),
                dict(text='Arjun K', index=2, callback=self.callback),
                dict(text='Philip Raj', index=3, callback=self.callback),
                dict(text='Athul Devin', index=4, callback=self.callback)
            ])

    def exit1(self, *args):
        
        App.get_running_app().stop()
        args[0].parent.dismiss()


if __name__ == '__main__':
    ModernMenuApp().run()
