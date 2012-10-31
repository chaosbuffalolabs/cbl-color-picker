import kivy
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.popup import Popup
from kivy.properties import NumericProperty, BooleanProperty, ListProperty, StringProperty, ObjectProperty
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics import Mesh, InstructionGroup, Color
from kivy.factory import Factory
from math import cos, sin, pi, sqrt, atan


def distance(pt1,pt2):
    return sqrt((pt1[0]-pt2[0])**2 + (pt1[1]-pt2[1])**2)

def polar_to_rect(origin, r, theta):
    return origin[0] + r*cos(theta), origin[1] + r*sin(theta)

def rect_to_polar(origin, x, y):
    if x == origin[0]:
        if y == origin[1]:
            return (0,0)
        elif y > origin[1]:
            return (y - origin[1], pi/2)
        else:
            return (origin[1] - y, 3*pi/2)
    t = atan(float((y-origin[1]))/(x-origin[0]))
    if x - origin[0] < 0:
        t += pi
    if t < 0: 
        t += 2*pi

    return (distance((x,y),origin), t)

class ColorWheel(Widget):
    r = NumericProperty(255)
    g = NumericProperty(255)
    b = NumericProperty(255)
    a = NumericProperty(255)
    rgba = ListProperty((255,255,255,255))

    origin = ListProperty((100,100))
    radius = NumericProperty(100)

    piece_divisions = NumericProperty(10)
    pieces_of_pie = NumericProperty(16)

    inertia_slowdown = 1.25
    inertia_cutoff = .25

    _num_touches = 0
    _pinch_flag = False

    bg_color_hsv = ListProperty([1,1,0,0])

    def __init__(self, **kwargs):
        super(ColorWheel,self).__init__(**kwargs)

        self.SVs = [(float(x)/self.piece_divisions,1) for x in range(self.piece_divisions)] + [(1, float(y)/self.piece_divisions) for y in reversed(range(self.piece_divisions))]
        print self.origin
        # Clock.schedule_once(self.init_wheel, .75)

    def on_origin(self,instance,value):
        self.init_wheel(None)

    def init_wheel(self, dt):
        # initialize list to hold all meshes
        self.canvas.clear()
        self.arcs = []
        self.SVidx = 0
        
        for r in range(self.piece_divisions):
            for t in range(self.pieces_of_pie):
                self.arcs.append(ColorArc(self.radius*(float(r)/self.piece_divisions), 
                                           self.radius*(float(r+1)/self.piece_divisions),
                                           2*pi*(float(t)/self.pieces_of_pie),
                                           2*pi*(float(t+1)/self.pieces_of_pie),
                                           origin = self.origin,
                                           color=(float(t)/self.pieces_of_pie, self.SVs[self.SVidx + r][0], self.SVs[self.SVidx + r][1], 1)))
                self.canvas.add(self.arcs[-1])              

    def recolor_wheel(self):
        for idx, segment in enumerate(self.arcs):
            segment.change_color(sv = self.SVs[self.SVidx + idx/self.pieces_of_pie])

    def change_alpha(self, val):
        for idx, segment in enumerate(self.arcs):
            segment.change_color(a = val)

    def inertial_incr_SVidx(self,dt):
        # if its already zoomed all the way out, cancel the inertial zoom
        if self.SVidx == len(self.SVs) - self.piece_divisions:
            return False
        self.SVidx += 1
        self.recolor_wheel()
        if dt*self.inertia_slowdown > self.inertia_cutoff:
            return False
        else:
            Clock.schedule_once(self.inertial_incr_SVidx, dt*self.inertia_slowdown)

    def inertial_decr_SVidx(self,dt):
        # if its already zoomed all the way in, cancel the inertial zoom
        if self.SVidx == 0:
            return False
        self.SVidx -= 1
        self.recolor_wheel()
        if dt*self.inertia_slowdown > self.inertia_cutoff:
            return False
        else:
            Clock.schedule_once(self.inertial_decr_SVidx, dt*self.inertia_slowdown)
        

    def on_touch_down(self, touch):
        r = self._get_touch_r(touch.pos)
        if r > self.radius:
            return False

        # code is still set up to allow pinch to zoom, but this is disabled for now since it was fiddly with
        # small wheels. Uncomment these lines and  adjust on_touch_move to reenable this.
        if self._num_touches != 0:
            return False

        touch.grab(self)
        self._num_touches += 1
        touch.ud['anchor_r'] = r
        touch.ud['orig_SVidx'] = self.SVidx
        touch.ud['orig_time'] = Clock.get_time()
        
    def on_touch_move(self,touch):
        if touch.grab_current is not self: return
        r = self._get_touch_r(touch.pos)
        goal_SVidx = touch.ud['orig_SVidx'] - int((r - touch.ud['anchor_r'])/(float(self.radius)/self.piece_divisions))
        if goal_SVidx != self.SVidx and goal_SVidx >= 0 and goal_SVidx <= len(self.SVs) - self.piece_divisions:
            # this is a pinch to zoom
            self._pinch_flag = True
            self.SVidx = goal_SVidx
            self.recolor_wheel()

    def on_touch_up(self,touch):
        if touch.grab_current is not self: return
        self._num_touches -= 1
        if self._pinch_flag:
            if self._num_touches == 0:
                # user was pinching, and now both fingers are up. Return to normal
                if self.SVidx > touch.ud['orig_SVidx']:
                    Clock.schedule_once(self.inertial_incr_SVidx, (Clock.get_time() - touch.ud['orig_time'])/(self.SVidx - touch.ud['orig_SVidx']))
                if self.SVidx < touch.ud['orig_SVidx']:
                    Clock.schedule_once(self.inertial_decr_SVidx, (Clock.get_time() - touch.ud['orig_time'])/(self.SVidx - touch.ud['orig_SVidx']))
                self._pinch_flag = False
                return
            else:
                # user was pinching, and at least one finger remains. We don't want to treat the remaining fingers as touches
                return
        else:
            r, theta = rect_to_polar(self.origin, *touch.pos)
            # if touch up is outside the wheel, ignore
            if r >= self.radius: return
            # compute which ColorArc is being touched (they aren't widgets so we don't get collide_point) and set bg_color based on the selected ColorArc
            piece = int((theta/(2*pi)) * self.pieces_of_pie)
            division = int((r/self.radius) * self.piece_divisions)
            self.bg_color_hsv = self.arcs[self.pieces_of_pie * division + piece].color

    def on_bg_color_hsv(self,instance,value):
        c_hsv = Color(*value, mode='hsv')
        self.r = c_hsv.r * 255.
        self.g = c_hsv.g * 255.
        self.b = c_hsv.b * 255.
        self.a = c_hsv.a * 255.
        self.rgba = (self.r, self.g, self.b, self.a)

    def _get_touch_r(self, pos):
        return distance(pos, self.origin)

class ColorArc(InstructionGroup):

    def __init__(self, r_min, r_max, theta_min, theta_max, color=(0,0,1,1), origin = (0,0), **kwargs):
        super(ColorArc, self).__init__(**kwargs)
        self.origin = origin
        self.r_min = r_min
        self.r_max = r_max
        self.theta_min = theta_min        
        self.theta_max = theta_max
        self.color = color
        self.color_instr = Color(*color, mode='hsv')
        self.add(self.color_instr)
        self.mesh = self.get_mesh()
        self.add(self.mesh)

    def __str__(self):
        return "r_min:" + str(self.r_min) + "r_max:" + str(self.r_max) + "theta_min" + str(self.theta_min) + "theta_max" + str(self.theta_max) + "color:" + str(self.color)

    def get_mesh(self):
        v = []
        # first calculate the distance between endpoints of the inner arc, so we know 
        # how many steps to use when calculating vertices
        start_point_inner = polar_to_rect(self.origin, self.r_min, self.theta_min) 
        end_point_inner = polar_to_rect(self.origin, self.r_min, self.theta_max)
        clip = lambda x: 1 if x<1 else x 
        d_inner = clip(distance(start_point_inner, end_point_inner))
        theta_step_inner = (self.theta_max - self.theta_min)/d_inner

        end_point_outer = polar_to_rect(self.origin, self.r_max, self.theta_max)
        
        if self.r_min == 0:
            start_point_outer = polar_to_rect(self.origin, self.r_max, self.theta_min)
            d_outer = clip(distance(start_point_outer, end_point_outer))
            theta_step_outer = (self.theta_max - self.theta_min)/d_outer
            for x in range(int(d_outer)):
                v += (polar_to_rect(self.origin, 0, 0)*2)
                v += (polar_to_rect(self.origin, self.r_max, self.theta_min + x*theta_step_outer)*2)
        else:
            for x in range(int(d_inner)):
                v += (polar_to_rect(self.origin, self.r_min, self.theta_min + x*theta_step_inner)*2)
                v += (polar_to_rect(self.origin, self.r_max, self.theta_min + x*theta_step_inner)*2)
            
        v += (end_point_inner*2)
        v += (end_point_outer*2)

        return Mesh(vertices = v, indices = range(len(v)/4), mode='triangle_strip')


    def change_color(self, color = None, color_delta = None, sv = None, a = None):
        self.remove(self.color_instr)
        if color is not None:            
            self.color = color
        elif color_delta is not None:
            self.color = [self.color[i] + color_delta[i] for i in range(4)]
        elif sv is not None:
            self.color = (self.color[0], sv[0], sv[1], self.color[3])
        elif a is not None:
            self.color = (self.color[0], self.color[1], self.color[2], a)
        self.color_instr = Color(*self.color, mode='hsv')
        self.insert(0, self.color_instr)            

class ColorPicker(Widget):
    label_color = ListProperty((1,1,1,1))
    font_size = NumericProperty(12)
    bg_color = ListProperty((.3,.3,.3,1))
    selected_color = ListProperty((1,1,1,1))
    wheel = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(ColorPicker, self).__init__(**kwargs)
        self.wheel.bind(rgba = self.rgba_callback)

    def rgba_callback(self,instance,value):
        self.selected_color = [x/255. for x in value]

    def button_callback(self,button_str):
        np = NumPad(self)
        np_popup = Popup(content=np, title="Please choose a color value (0-255)", size_hint=(.4,.6), id = button_str)
        np_popup.bind(on_dismiss = self.popup_dismissed)
        np_popup.open()

    def popup_dismissed(self,instance):
        colr = instance.id
        val = instance.content.display_value
        self.selected_color[{'R': 0, 'G': 1, 'B': 2, 'A': 3}[colr]] = val / 255.

        # if it's the alpha value that's been edited, we actually need to change this in the colorwheel
        if colr == 'A':
            self.wheel.change_alpha(val / 255.)

class NumPad(Widget):
    display_text = StringProperty("0")
    display_value = NumericProperty(0)

    def __init__(self, popup, **kwargs):
        super(NumPad, self).__init__(**kwargs)
        self.popup = popup

    def button_callback(self,button_str):
        if button_str in [str(x) for x in range(10)]:
            self.display_text = button_str if self.display_text == '0' else self.display_text + button_str
            if self.display_value > 255: self.display_text = "255"
        elif button_str == 'del':
            self.display_text = self.display_text[:-1]
        elif button_str == 'ret':
            self.popup.dismiss()

    def on_display_text(self,instance,value):
        if value == '':
            self.display_text = '0'
            return
        self.display_value = int(value)


Factory.register('ColorWheel', ColorWheel)

class ColorPickerDemoApp(App):
    def build(self):
        cp_width = min(Window.size)*.7
        cp_pos = [(Window.size[0]-cp_width)/2,(Window.size[1]-cp_width)/2]
        cp = ColorPicker(pos = cp_pos, size=(cp_width,cp_width), size_hint=(None,None))
        return cp
        

if __name__ in ('__android__', '__main__'):
    ColorPickerDemoApp().run()
