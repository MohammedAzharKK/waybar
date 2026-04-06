#!/usr/bin/env python3
import gi
import time
import os
import math
import cairo
import json
import urllib.request
#! test
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell

def get_weather():
    try:
        with urllib.request.urlopen("https://wttr.in/?format=j1") as url:
            data = json.loads(url.read().decode())
            current = data['current_condition'][0]
            weather = {
                'temp': float(current['temp_C']),
                'humidity': float(current['humidity']),
                'wind': float(current['windspeedKmph']),
                'desc': current['weatherDesc'][0]['value'],
                'forecast': []
            }
            for day in data['weather'][:3]:
                weather['forecast'].append({
                    'date': day['date'],
                    'maxtemp': day['maxtempC'],
                    'mintemp': day['mintempC'],
                    'desc': day['hourly'][4]['weatherDesc'][0]['value']
                })
            return weather
    except Exception as e:
        return None

class WeatherInfotainment(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
        
        self.set_app_paintable(True)
        self.set_visual(self.get_screen().get_rgba_visual())
        self.set_decorated(False)
        self.set_default_size(480, 320)

        if GtkLayerShell.is_supported():
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_namespace(self, "weather_dashboard")
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 50)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 10)

        self.darea = Gtk.DrawingArea()
        self.darea.set_size_request(480, 320)
        self.darea.connect("draw", self.on_draw)
        self.add(self.darea)

        self.weather = None
        self.anim_val = 0.0
        self.particles = []
        self._init_particles()
        
        self.update_weather()
        GLib.timeout_add(30, self.animate_loop)
        GLib.timeout_add_seconds(600, self.update_weather) # 10 mins

        self.connect("button-press-event", lambda w, e: Gtk.main_quit())
        self.connect("key-press-event", self.on_key)
        self.close_timeout = GLib.timeout_add_seconds(25, Gtk.main_quit)
        self.show_all()

    def on_key(self, widget, event):
        if event.keyval == Gdk.KEY_Escape: Gtk.main_quit()
        return False

    def update_weather(self):
        new_weather = get_weather()
        if new_weather:
            self.weather = new_weather
            self.darea.queue_draw()
        return True

    def _init_particles(self):
        import random
        self.particles = []
        for _ in range(50):
            self.particles.append({
                'x': random.uniform(20, 460),
                'y': random.uniform(20, 300),
                'speed': random.uniform(1, 4),
                'size': random.uniform(1, 3),
                'opacity': random.uniform(0.1, 0.6)
            })

    def animate_loop(self):
        self.anim_val += 0.05
        # Move particles
        for p in self.particles:
            p['y'] += p['speed']
            if p['y'] > 300:
                p['y'] = 20
                import random
                p['x'] = random.uniform(20, 460)
        self.darea.queue_draw()
        return True

    def draw_rounded_rect(self, cr, x, y, w, h, r):
        cr.new_sub_path()
        cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
        cr.arc(x + w - r, y + r, r, 1.5 * math.pi, 2 * math.pi)
        cr.arc(x + w - r, y + h - r, r, 0, 0.5 * math.pi)
        cr.arc(x + r, y + h - r, r, 0.5 * math.pi, math.pi)
        cr.close_path()

    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        # Clear background
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.Operator.SOURCE)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)

        # Main Glass Card
        self.draw_rounded_rect(cr, 10, 10, width-20, height-20, 25)
        
        # Dynamic Gradient Background
        temp = self.weather['temp'] if self.weather else 20
        if temp < 15:
            # Cool Blue
            lg = cairo.LinearGradient(0, 0, width, height)
            lg.add_color_stop_rgba(0, 0.05, 0.1, 0.2, 0.95)
            lg.add_color_stop_rgba(1, 0.1, 0.2, 0.4, 0.9)
        elif temp > 28:
            # Sunset Orange
            lg = cairo.LinearGradient(0, 0, width, height)
            lg.add_color_stop_rgba(0, 0.15, 0.05, 0, 0.95)
            lg.add_color_stop_rgba(1, 0.4, 0.1, 0, 0.9)
        else:
            # Modern Slate
            lg = cairo.LinearGradient(0, 0, width, height)
            lg.add_color_stop_rgba(0, 0.05, 0.05, 0.08, 0.95)
            lg.add_color_stop_rgba(1, 0.1, 0.1, 0.15, 0.9)
        
        cr.set_source(lg)
        cr.fill_preserve()
        
        # Inner Glow
        cr.set_source_rgba(1, 1, 1, 0.05)
        cr.set_line_width(2)
        cr.stroke()

        if not self.weather:
            cr.set_source_rgba(1, 1, 1, 0.5)
            cr.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.NORMAL)
            cr.set_font_size(24)
            cr.move_to(width/2 - 80, height/2)
            cr.show_text("Synchronizing...")
            return

        # --- Particle Effects Overlay ---
        self.draw_particles(cr, width, height)

        # --- Current Condition Section ---
        # Large Temp
        cr.set_source_rgba(1, 1, 1, 1)
        cr.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.BOLD)
        cr.set_font_size(72)
        temp_text = f"{int(self.weather['temp'])}°"
        xb, yb, tw, th, xa, ya = cr.text_extents(temp_text)
        cr.move_to(40, 110)
        cr.show_text(temp_text)

        # Condition Text
        cr.set_font_size(20)
        cr.set_source_rgba(1, 1, 1, 0.8)
        desc = self.weather['desc']
        cr.move_to(45, 140)
        cr.show_text(desc)

        # "Weather Icon" (Stylized Circle/Glow)
        cr.set_source_rgba(1, 0.8, 0, 0.3 + 0.1 * math.sin(self.anim_val))
        cr.arc(width - 100, 90, 40, 0, 2 * math.pi)
        cr.fill()
        cr.set_source_rgba(1, 0.9, 0.2, 0.8)
        cr.arc(width - 100, 90, 20, 0, 2 * math.pi)
        cr.fill()

        # --- Environment Stats Bar ---
        bar_y = 180
        cr.set_source_rgba(1, 1, 1, 0.1)
        self.draw_rounded_rect(cr, 40, bar_y, width-80, 40, 10)
        cr.fill()

        # Humidity
        cr.set_source_rgba(1, 1, 1, 0.6)
        cr.set_font_size(12)
        cr.move_to(60, bar_y + 25)
        cr.show_text(f"HUMIDITY: {int(self.weather['humidity'])}%")
        
        # Wind
        cr.move_to(width/2 + 20, bar_y + 25)
        cr.show_text(f"WIND SPEED: {int(self.weather['wind'])} km/h")

        # --- Forecast Section ---
        f_y = 240
        tile_w = (width - 100) / 3
        x_start = 40
        
        for i, f in enumerate(self.weather['forecast']):
            # Tile Background
            cr.set_source_rgba(1, 1, 1, 0.05)
            self.draw_rounded_rect(cr, x_start, f_y, tile_w - 10, 55, 12)
            cr.fill()
            
            # Date
            cr.set_source_rgba(1, 1, 1, 0.8)
            cr.set_font_size(11)
            date_label = f["date"].split("-")[2]
            cr.move_to(x_start + 10, f_y + 20)
            cr.show_text(f"Day {date_label}")
            
            # Temps
            cr.set_font_size(13)
            cr.set_source_rgba(1, 0.8, 0, 1)
            cr.move_to(x_start + 10, f_y + 42)
            cr.show_text(f"{f['mintemp']}° - {f['maxtemp']}°")
            
            x_start += tile_w

    def draw_particles(self, cr, width, height):
        if not self.weather: return
        desc = self.weather['desc'].lower()
        
        if "rain" in desc or "drizzle" in desc or "shower" in desc:
            # Drawing Rain
            cr.set_source_rgba(0.4, 0.6, 1.0, 0.4)
            cr.set_line_width(1)
            for p in self.particles:
                cr.move_to(p['x'], p['y'])
                cr.line_to(p['x'], p['y'] + 10)
                cr.stroke()
        elif "snow" in desc:
            # Drawing Snow
            cr.set_source_rgba(1, 1, 1, 0.5)
            for p in self.particles:
                cr.arc(p['x'], p['y'], p['size'], 0, 2*math.pi)
                cr.fill()
        else:
            # Twinkling Stars (Clear/Cloudy default)
            for p in self.particles:
                op = p['opacity'] * (0.5 + 0.5 * math.sin(self.anim_val + p['x']))
                cr.set_source_rgba(1, 1, 1, op)
                cr.arc(p['x'], p['y'], 1.5, 0, 2*math.pi)
                cr.fill()

if __name__ == "__main__":
    win = WeatherInfotainment()
    Gtk.main()
