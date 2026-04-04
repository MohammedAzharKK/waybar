#!/usr/bin/env python3
import gi
import time
import os
import math
import cairo
import psutil

gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell

def get_top_processes():
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        try:
            processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    # Sort by CPU and get top 5
    top = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:5]
    return top

def get_cpu_temp():
    try:
        temps = psutil.sensors_temperatures()
        if 'coretemp' in temps:
            return temps['coretemp'][0].current
        elif 'acpitz' in temps:
            return temps['acpitz'][0].current
        return 0
    except:
        return 0

class SystemHealthGauge(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
        
        self.set_app_paintable(True)
        self.set_visual(self.get_screen().get_rgba_visual())
        self.set_decorated(False)
        self.set_default_size(500, 320)

        if GtkLayerShell.is_supported():
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_namespace(self, "system_health")
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 50)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 10)

        self.darea = Gtk.DrawingArea()
        self.darea.set_size_request(500, 320)
        self.darea.connect("draw", self.on_draw)
        self.add(self.darea)

        self.cpu_usage = 0.0
        self.ram_usage = 0.0
        self.temp = 0.0
        self.top_procs = []
        
        self.target_cpu = 0.0
        self.target_ram = 0.0
        self.target_temp = 0.0

        GLib.timeout_add(500, self.update_stats)
        GLib.timeout_add(30, self.animate)
        
        self.connect("button-press-event", lambda w, e: Gtk.main_quit())
        self.connect("key-press-event", self.on_key)
        self.close_timeout = GLib.timeout_add_seconds(20, Gtk.main_quit)
        self.show_all()

    def on_key(self, widget, event):
        if event.keyval == Gdk.KEY_Escape: Gtk.main_quit()
        return False

    def update_stats(self):
        self.target_cpu = psutil.cpu_percent()
        self.target_ram = psutil.virtual_memory().percent
        self.target_temp = get_cpu_temp()
        self.top_procs = get_top_processes()
        return True

    def animate(self):
        self.cpu_usage += (self.target_cpu - self.cpu_usage) * 0.1
        self.ram_usage += (self.target_ram - self.ram_usage) * 0.1
        self.temp += (self.target_temp - self.temp) * 0.1
        self.darea.queue_draw()
        return True

    def draw_gauge(self, cr, x, y, radius, val, max_val, label, color_start, color_end, small=False):
        # Background
        cr.set_source_rgba(0.05, 0.05, 0.1, 0.9)
        cr.arc(x, y, radius + (10 if small else 20), 0, 2 * math.pi)
        cr.fill()
        
        cr.set_source_rgba(1, 1, 1, 0.1)
        cr.set_line_width(2)
        cr.arc(x, y, radius + (10 if small else 20), 0, 2 * math.pi)
        cr.stroke()

        # Track
        start_angle = 135 * (math.pi / 180)
        end_angle = 45 * (math.pi / 180)
        cr.set_line_width(8 if small else 12)
        cr.set_line_cap(cairo.LineCap.ROUND)
        cr.set_source_rgba(0.2, 0.2, 0.25, 1.0)
        cr.arc(x, y, radius, start_angle, end_angle)
        cr.stroke()

        # Progress
        percent = min(val / max_val if max_val > 0 else 0, 1.0)
        active_end = start_angle + (270 * (math.pi / 180) * percent)
        
        lg = cairo.LinearGradient(x, y + radius, x, y - radius)
        lg.add_color_stop_rgba(0, *color_start)
        lg.add_color_stop_rgba(1, *color_end)
        cr.set_source(lg)
        cr.arc(x, y, radius, start_angle, active_end)
        cr.stroke()

        # Needle
        cr.set_source_rgba(1, 1, 1, 0.9)
        cr.set_line_width(3 if small else 4)
        cr.move_to(x, y)
        cr.line_to(x + (radius + 5) * math.cos(active_end), 
                   y + (radius + 5) * math.sin(active_end))
        cr.stroke()

        # Center dot
        cr.set_source_rgba(0.8, 0.8, 0.8, 1)
        cr.arc(x, y, 5 if small else 8, 0, 2 * math.pi)
        cr.fill()

        # Text
        cr.set_source_rgba(1, 1, 1, 1)
        cr.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.BOLD)
        cr.set_font_size(14 if small else 18)
        txt = f"{int(val)}%" if not small else f"{int(val)}°C"
        xb, yb, tw, th, xa, ya = cr.text_extents(txt)
        cr.move_to(x - tw/2, y + radius/2)
        cr.show_text(txt)

        cr.set_font_size(10)
        cr.set_source_rgba(1, 1, 1, 0.5)
        xb, yb, tw, th, xa, ya = cr.text_extents(label)
        cr.move_to(x - tw/2, y + radius/2 + (15 if small else 20))
        cr.show_text(label)

    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.Operator.SOURCE)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)

        # CPU Left (Turbo)
        self.draw_gauge(cr, width*0.25, height*0.35, 70, self.cpu_usage, 100, 
                        "CPU TURBO", (0.2, 0.8, 0.2, 1), (1, 1, 0, 1))

        # RAM Right (Fuel)
        self.draw_gauge(cr, width*0.75, height*0.35, 70, self.ram_usage, 100, 
                        "RAM FUEL", (1, 0.5, 0, 1), (1, 0.2, 0.2, 1))

        # Temp Center (Engine Temp)
        self.draw_gauge(cr, width*0.5, height*0.35, 45, self.temp, 100, 
                        "TEMP", (0.3, 0.3, 1, 1), (1, 0, 0, 1), small=True)

        # Process Panel
        cr.set_source_rgba(0.1, 0.1, 0.15, 0.85)
        cr.rectangle(width*0.05, height*0.72, width*0.9, height*0.25)
        cr.fill()
        
        cr.set_source_rgba(1, 1, 1, 0.8)
        cr.set_font_size(12)
        cr.move_to(width*0.1, height*0.78)
        cr.show_text("TOP PROCESSES (CPU)")
        
        cr.set_font_size(10)
        y_off = height*0.84
        for p in self.top_procs:
            cr.move_to(width*0.1, y_off)
            cr.set_source_rgba(1, 1, 1, 0.7)
            cr.show_text(f"{p['name'][:20]}")
            
            cr.move_to(width*0.7, y_off)
            cr.set_source_rgba(1, 0.8, 0, 1)
            cr.show_text(f"{p['cpu_percent']:.1f}%")
            y_off += 14

if __name__ == "__main__":
    try:
        win = SystemHealthGauge()
        Gtk.main()
    except Exception as e:
        print(f"Error: {e}")
