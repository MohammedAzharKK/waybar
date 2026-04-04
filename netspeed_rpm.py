#!/usr/bin/env python3
import gi
import time
import os
import math
import cairo
import socket

gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell

def get_net_stats():
    try:
        with open("/proc/net/dev", "r") as f:
            lines = f.readlines()
        data = {}
        for line in lines[2:]:
            parts = line.split(':')
            if len(parts) < 2: continue
            iface = parts[0].strip()
            stats = parts[1].split()
            rx = int(stats[0])
            tx = int(stats[8])
            data[iface] = (rx, tx)
        return data
    except Exception as e:
        return {}

def get_default_iface():
    try:
        with os.popen("ip route show default") as f:
            line = f.readline()
            if "dev" in line:
                return line.split("dev")[1].split()[0]
    except:
        pass
    try:
        data = get_net_stats()
        for k in data.keys():
            if k != "lo": return k
    except:
        pass
    return "wlan0"

def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        # Use a dummy address to find the local IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "N/A"

class NetSpeedGauge(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
        
        self.set_app_paintable(True)
        self.set_visual(self.get_screen().get_rgba_visual())
        self.set_decorated(False)
        self.set_default_size(480, 280)

        if GtkLayerShell.is_supported():
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_namespace(self, "netspeed_gauge")
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 50)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 20)

        self.darea = Gtk.DrawingArea()
        self.darea.set_size_request(480, 280)
        self.darea.connect("draw", self.on_draw)
        self.add(self.darea)

        self.iface = get_default_iface()
        self.ip_addr = get_ip_address()
        print(f"Tracking network interface: {self.iface} at {self.ip_addr}", flush=True)
        
        stats = get_net_stats().get(self.iface, (0, 0))
        self.last_rx, self.last_tx = stats
        self.start_rx, self.start_tx = stats
        self.last_time = time.time()
        
        self.curr_rx_mbps = 0.0
        self.curr_tx_mbps = 0.0
        self.target_rx_mbps = 0.0
        self.target_tx_mbps = 0.0
        
        self.max_rx_mbps = 20.0
        self.max_tx_mbps = 10.0

        GLib.timeout_add(100, self.update_speed)
        GLib.timeout_add(30, self.animate_needle)
        
        self.connect("button-press-event", lambda w, e: Gtk.main_quit())
        self.connect("key-press-event", self.on_key)
        self.close_timeout = GLib.timeout_add_seconds(20, Gtk.main_quit)
        self.show_all()

    def on_key(self, widget, event):
        if event.keyval == Gdk.KEY_Escape: Gtk.main_quit()
        return False

    def update_speed(self):
        now = time.time()
        stats = get_net_stats().get(self.iface, (0, 0))
        curr_rx, curr_tx = stats
        
        dt = now - self.last_time
        if dt > 0:
            self.target_rx_mbps = ((curr_rx - self.last_rx) * 8) / (dt * 1_000_000.0)
            self.target_tx_mbps = ((curr_tx - self.last_tx) * 8) / (dt * 1_000_000.0)
            
            # Autoscale
            self.max_rx_mbps = max(self.max_rx_mbps, self.target_rx_mbps * 1.2)
            self.max_tx_mbps = max(self.max_tx_mbps, self.target_tx_mbps * 1.2)
            
        self.last_rx, self.last_tx = curr_rx, curr_tx
        self.last_time = now
        return True

    def animate_needle(self):
        self.curr_rx_mbps += (self.target_rx_mbps - self.curr_rx_mbps) * 0.1
        self.curr_tx_mbps += (self.target_tx_mbps - self.curr_tx_mbps) * 0.1
        self.darea.queue_draw()
        return True

    def draw_gauge(self, cr, x, y, radius, val, max_val, label, color_start, color_end):
        # Background
        cr.set_source_rgba(0.05, 0.05, 0.1, 0.9)
        cr.arc(x, y, radius + 20, 0, 2 * math.pi)
        cr.fill()
        
        # Border
        cr.set_source_rgba(1, 1, 1, 0.1)
        cr.set_line_width(2)
        cr.arc(x, y, radius + 20, 0, 2 * math.pi)
        cr.stroke()

        # Track
        start_angle = 135 * (math.pi / 180)
        end_angle = 45 * (math.pi / 180)
        cr.set_line_width(12)
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
        cr.set_line_width(4)
        cr.move_to(x, y)
        cr.line_to(x + (radius + 5) * math.cos(active_end), 
                   y + (radius + 5) * math.sin(active_end))
        cr.stroke()

        # Center dot
        cr.set_source_rgba(0.9, 0.9, 0.9, 1)
        cr.arc(x, y, 8, 0, 2 * math.pi)
        cr.fill()

        # Text
        cr.set_source_rgba(1, 1, 1, 1)
        cr.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.BOLD)
        cr.set_font_size(20)
        txt = f"{val:.1f}"
        xb, yb, tw, th, xa, ya = cr.text_extents(txt)
        cr.move_to(x - tw/2, y + radius/2)
        cr.show_text(txt)

        cr.set_font_size(12)
        cr.set_source_rgba(1, 1, 1, 0.6)
        xb, yb, tw, th, xa, ya = cr.text_extents(label)
        cr.move_to(x - tw/2, y + radius/2 + 20)
        cr.show_text(label)

    def on_draw(self, widget, cr):
        # print("Drawing frame...", flush=True) # Too noisy to keep on always, but good for one check
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        # Clear background
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.Operator.SOURCE)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)

        # Draw Download Gauge
        self.draw_gauge(cr, width*0.28, height*0.45, 80, self.curr_rx_mbps, self.max_rx_mbps, 
                        "DOWNLOAD (Mbps)", (0, 0.6, 1, 1), (0, 1, 1, 1))

        # Draw Upload Gauge
        self.draw_gauge(cr, width*0.72, height*0.45, 80, self.curr_tx_mbps, self.max_tx_mbps, 
                        "UPLOAD (Mbps)", (1, 0.4, 0, 1), (1, 1, 0, 1))

        # Bottom Info Panel
        cr.set_source_rgba(0.1, 0.1, 0.15, 0.8)
        cr.rectangle(width*0.05, height*0.82, width*0.9, height*0.15)
        cr.fill()
        
        cr.set_source_rgba(1, 1, 1, 0.8)
        cr.set_font_size(11)
        
        # Calculate session usage
        session_rx = (self.last_rx - self.start_rx) / 1_000_000.0
        session_tx = (self.last_tx - self.start_tx) / 1_000_000.0
        
        info_text = f"IFACE: {self.iface}  |  IP: {self.ip_addr}  |  SESSION: ↓{session_rx:.1f}MB ↑{session_tx:.1f}MB"
        xb, yb, tw, th, xa, ya = cr.text_extents(info_text)
        cr.move_to(width/2 - tw/2, height*0.92)
        cr.show_text(info_text)

if __name__ == "__main__":
    try:
        print("Initializing Dual Gauge Dashboard...", flush=True)
        win = NetSpeedGauge()
        print("Window successfully initialized and shown.", flush=True)
        Gtk.main()
    except Exception as e:
        print(f"Fatal Startup Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
