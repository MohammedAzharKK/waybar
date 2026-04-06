#!/usr/bin/env python3
import gi
import time
import os
import math
import cairo
import psutil
import random

gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell

class BatteryLiquidGauge(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
        
        self.set_app_paintable(True)
        self.set_visual(self.get_screen().get_rgba_visual())
        self.set_decorated(False)
        self.set_default_size(260, 400)

        if GtkLayerShell.is_supported():
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_namespace(self, "battery_liquid")
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 50)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 10)

        self.darea = Gtk.DrawingArea()
        self.darea.set_size_request(260, 400)
        self.darea.connect("draw", self.on_draw)
        self.add(self.darea)

        self.percent = 0.0
        self.is_charging = False
        self.time_left = ""
        self.anim_phase = 0.0
        
        # Bubbles for charging animation
        self.bubbles = []
        for _ in range(15):
            self.bubbles.append({'x': random.uniform(50, 210), 'y': random.uniform(100, 350), 's': random.uniform(1, 3)})

        self.update_battery()
        GLib.timeout_add(30, self.animate)
        GLib.timeout_add_seconds(5, self.update_battery)
        
        self.connect("button-press-event", lambda w, e: Gtk.main_quit())
        self.connect("key-press-event", self.on_key)
        self.close_timeout = GLib.timeout_add_seconds(20, Gtk.main_quit)
        self.show_all()

    def on_key(self, widget, event):
        if event.keyval == Gdk.KEY_Escape: Gtk.main_quit()
        return False

    def update_battery(self):
        batt = psutil.sensors_battery()
        if batt:
            self.percent = batt.percent
            self.is_charging = batt.power_plugged
            if batt.secsleft == psutil.POWER_TIME_UNLIMITED:
                self.time_left = "Unlimited"
            elif batt.secsleft == psutil.POWER_TIME_UNKNOWN:
                self.time_left = "Calculating..."
            else:
                self.time_left = f"{batt.secsleft // 3600}h {(batt.secsleft % 3600) // 60}m"
        return True

    def animate(self):
        self.anim_phase += 0.1
        if self.is_charging:
            for b in self.bubbles:
                b['y'] -= b['s']
                if b['y'] < 80:
                    b['y'] = 350
                    b['x'] = random.uniform(60, 200)
        self.darea.queue_draw()
        return True

    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        xc, yc = width / 2, height / 2

        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.Operator.SOURCE)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)

        # Tank Frame
        cr.set_source_rgba(0.05, 0.05, 0.1, 0.9)
        self.draw_rounded_rect(cr, 50, 60, 160, 300, 20)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.15)
        cr.set_line_width(3)
        cr.stroke()

        # Liquid Level Calculation
        max_fill_height = 280
        fill_height = max_fill_height * (self.percent / 100.0)
        base_y = 350 - fill_height

        # Liquid Color
        if self.is_charging:
            color = (0, 0.8, 1, 0.7) # Cyan
        elif self.percent > 50:
            color = (0.2, 0.8, 0.2, 0.7) # Green
        elif self.percent > 20:
            color = (0.9, 0.7, 0, 0.7) # Yellow
        else:
            color = (1, 0.2, 0.2, 0.7) # Red

        # Draw Liquid with Waves
        cr.set_source_rgba(*color)
        cr.move_to(50, 360)
        cr.line_to(210, 360)
        cr.line_to(210, base_y)
        
        # Sine wave surface
        steps = 40
        step_w = 160 / steps
        for i in range(steps + 1):
            x = 210 - (i * step_w)
            y = base_y + 6 * math.sin(self.anim_phase + (i * 0.4))
            cr.line_to(x, y)
        
        cr.close_path()
        cr.fill()

        # Bubbles (if charging)
        if self.is_charging:
            cr.set_source_rgba(1, 1, 1, 0.4)
            for b in self.bubbles:
                if b['y'] > base_y: # Only bubbles inside liquid
                    cr.arc(b['x'], b['y'], 2, 0, 2*math.pi)
                    cr.fill()

        # Shine Effect
        lg = cairo.LinearGradient(70, 0, 100, 0)
        lg.add_color_stop_rgba(0, 1, 1, 1, 0.15)
        lg.add_color_stop_rgba(1, 1, 1, 1, 0)
        cr.set_source(lg)
        self.draw_rounded_rect(cr, 65, 75, 20, 270, 10)
        cr.fill()

        # Percentage Text
        cr.set_source_rgba(1, 1, 1, 1)
        cr.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.BOLD)
        cr.set_font_size(32)
        txt = f"{int(self.percent)}%"
        xb, yb, tw, th, xa, ya = cr.text_extents(txt)
        cr.move_to(xc - tw/2, 220)
        cr.show_text(txt)

        # Status Stats
        cr.set_font_size(12)
        cr.set_source_rgba(1, 1, 1, 0.6)
        status_text = "CHARGING" if self.is_charging else "DISCHARGING"
        xb, yb, tw, th, xa, ya = cr.text_extents(status_text)
        cr.move_to(xc - tw/2, 380)
        cr.show_text(status_text)
        
        time_text = f"REMAINING: {self.time_left}"
        xb, yb, tw, th, xa, ya = cr.text_extents(time_text)
        cr.move_to(xc - tw/2, 20)
        cr.show_text(time_text)

    def draw_rounded_rect(self, cr, x, y, w, h, r):
        cr.new_sub_path()
        cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
        cr.arc(x + w - r, y + r, r, 1.5 * math.pi, 2 * math.pi)
        cr.arc(x + w - r, y + h - r, r, 0, 0.5 * math.pi)
        cr.arc(x + r, y + h - r, r, 0.5 * math.pi, math.pi)
        cr.close_path()

if __name__ == "__main__":
    try:
        win = BatteryLiquidGauge()
        Gtk.main()
    except Exception as e:
        print(f"Error: {e}")
