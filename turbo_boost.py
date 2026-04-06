#!/usr/bin/env python3
import gi
import time
import os
import math
import cairo

gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell

def get_disk_stats():
    try:
        with open("/proc/diskstats", "r") as f:
            lines = f.readlines()
        data = {}
        # We look for the main disk, usually sda, nvme0n1, etc.
        # Summing all partitions or focusing on the primary device
        total_read = 0
        total_write = 0
        for line in lines:
            parts = line.split()
            # 3rd field is device name, 6th is sectors read, 10th is sectors written
            # sector size is usually 512 bytes
            total_read += int(parts[5]) * 512
            total_write += int(parts[9]) * 512
        return total_read, total_write
    except Exception as e:
        return 0, 0

class TurboBoostGauge(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
        
        self.set_app_paintable(True)
        self.set_visual(self.get_screen().get_rgba_visual())
        self.set_decorated(False)
        self.set_default_size(480, 280)

        if GtkLayerShell.is_supported():
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_namespace(self, "turbo_gauge")
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 50)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 100)

        self.darea = Gtk.DrawingArea()
        self.darea.set_size_request(480, 280)
        self.darea.connect("draw", self.on_draw)
        self.add(self.darea)

        read, write = get_disk_stats()
        self.last_read, self.last_write = read, write
        self.last_time = time.time()
        
        self.curr_read_mb = 0.0
        self.curr_write_mb = 0.0
        self.target_read_mb = 0.0
        self.target_write_mb = 0.0
        
        self.max_read_mb = 50.0  # Initial scale
        self.max_write_mb = 50.0

        GLib.timeout_add(200, self.update_stats)
        GLib.timeout_add(30, self.animate_needle)
        
        self.connect("button-press-event", lambda w, e: Gtk.main_quit())
        self.connect("key-press-event", self.on_key)
        self.close_timeout = GLib.timeout_add_seconds(15, Gtk.main_quit)
        self.show_all()

    def on_key(self, widget, event):
        if event.keyval == Gdk.KEY_Escape: Gtk.main_quit()
        return False

    def update_stats(self):
        now = time.time()
        read, write = get_disk_stats()
        
        dt = now - self.last_time
        if dt > 0:
            self.target_read_mb = (read - self.last_read) / (dt * 1_048_576.0)
            self.target_write_mb = (write - self.last_write) / (dt * 1_048_576.0)
            
            # Autoscale logic
            self.max_read_mb = max(self.max_read_mb, self.target_read_mb * 1.5, 10.0)
            self.max_write_mb = max(self.max_write_mb, self.target_write_mb * 1.5, 10.0)
            
        self.last_read, self.last_write = read, write
        self.last_time = now
        return True

    def animate_needle(self):
        self.curr_read_mb += (self.target_read_mb - self.curr_read_mb) * 0.1
        self.curr_write_mb += (self.target_write_mb - self.curr_write_mb) * 0.1
        self.darea.queue_draw()
        return True

    def draw_gauge(self, cr, x, y, radius, val, max_val, label, color_start, color_end):
        # Shadow/Glow Background
        cr.set_source_rgba(0.05, 0.05, 0.1, 0.95)
        cr.arc(x, y, radius + 25, 0, 2 * math.pi)
        cr.fill()
        
        # Border Glow
        cr.set_source_rgba(color_start[0], color_start[1], color_start[2], 0.2)
        cr.set_line_width(4)
        cr.arc(x, y, radius + 25, 0, 2 * math.pi)
        cr.stroke()

        # Track
        start_angle = 135 * (math.pi / 180)
        end_angle = 45 * (math.pi / 180)
        cr.set_line_width(15)
        cr.set_line_cap(cairo.LineCap.ROUND)
        cr.set_source_rgba(0.15, 0.15, 0.2, 1.0)
        cr.arc(x, y, radius, start_angle, end_angle)
        cr.stroke()

        # Progress Arc
        percent = min(val / max_val if max_val > 0 else 0, 1.0)
        active_end = start_angle + (270 * (math.pi / 180) * percent)
        
        lg = cairo.LinearGradient(x, y + radius, x, y - radius)
        lg.add_color_stop_rgba(0, *color_start)
        lg.add_color_stop_rgba(1, *color_end)
        cr.set_source(lg)
        cr.arc(x, y, radius, start_angle, active_end)
        cr.stroke()

        # Ticks
        cr.set_source_rgba(1, 1, 1, 0.3)
        cr.set_line_width(2)
        for i in range(11):
            angle = start_angle + (270 * (math.pi / 180) * (i / 10.0))
            cr.move_to(x + (radius - 15) * math.cos(angle), y + (radius - 15) * math.sin(angle))
            cr.line_to(x + (radius - 5) * math.cos(angle), y + (radius - 5) * math.sin(angle))
            cr.stroke()

        # Needle
        cr.set_source_rgba(1, 0.3, 0.1, 0.9) # Reddish orange needle
        cr.set_line_width(5)
        cr.set_line_cap(cairo.LineCap.ROUND)
        cr.move_to(x, y)
        cr.line_to(x + (radius + 10) * math.cos(active_end), 
                   y + (radius + 10) * math.sin(active_end))
        cr.stroke()

        # Center dot
        cr.set_source_rgba(0.9, 0.9, 0.9, 1)
        cr.arc(x, y, 10, 0, 2 * math.pi)
        cr.fill()
        cr.set_source_rgba(0.1, 0.1, 0.1, 1)
        cr.arc(x, y, 4, 0, 2 * math.pi)
        cr.fill()

        # Text Readout
        cr.set_source_rgba(1, 1, 1, 1)
        cr.select_font_face("Orbitron", cairo.FontSlant.NORMAL, cairo.FontWeight.BOLD)
        cr.set_font_size(24)
        txt = f"{val:.1f}"
        xb, yb, tw, th, xa, ya = cr.text_extents(txt)
        cr.move_to(x - tw/2, y + radius/2 + 5)
        cr.show_text(txt)

        cr.set_font_size(14)
        cr.set_source_rgba(1, 1, 1, 0.7)
        xb, yb, tw, th, xa, ya = cr.text_extents(label)
        cr.move_to(x - tw/2, y + radius/2 + 25)
        cr.show_text(label)

    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.Operator.SOURCE)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)

        # Background Card
        cr.set_source_rgba(0.1, 0.1, 0.15, 0.4)
        cr.rectangle(20, 20, width-40, height-40)
        cr.fill()

        # Draw Turbo Boost Gauges
        # Reading Gauge
        self.draw_gauge(cr, width*0.28, height*0.5, 85, self.curr_read_mb, self.max_read_mb, 
                        "BOOST READ (MB/s)", (1, 0.6, 0, 1), (1, 0.2, 0, 1))

        # Writing Gauge
        self.draw_gauge(cr, width*0.72, height*0.5, 85, self.curr_write_mb, self.max_write_mb, 
                        "BOOST WRITE (MB/s)", (1, 0.8, 0, 1), (1, 0.5, 0, 1))

if __name__ == "__main__":
    win = TurboBoostGauge()
    Gtk.main()
