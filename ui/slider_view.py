"""Slider view module for time navigation and section boundaries."""

import tkinter as tk
from tkinter import ttk

from ui.slider_time_utils import SliderTimeUtils
from ui.slider_waveform import SliderWaveform
from ui.slider_markers import SliderMarkers

class SliderView(ttk.Frame):
    """Slider with markers for time navigation and section boundaries."""
    
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        
        # Get references to app variables
        self.stt = app.stt  # Start time
        self.ent = app.ent  # End time
        self.svm = app.svm  # Section view mode
        
        # Position tracking
        self.pos = tk.DoubleVar(value=0)
        # Add trace to position variable for data binding
        self.pos.trace_add("write", self.on_position_changed)
        
        # Create utility components
        self.time_utils = SliderTimeUtils(self)
        self.waveform = SliderWaveform(self)
        self.markers = SliderMarkers(self)
        
        # Set up the UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the slider view UI."""
        # Time label
        self.time_label = ttk.Label(self, text="00:00.0 / 00:00.0", width=20)
        self.time_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Slider canvas frame
        self.slider_frame = ttk.Frame(self)
        self.slider_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Canvas for markers with doubled height and white background
        self.canvas = tk.Canvas(self.slider_frame, height=60, bg="#FFFFFF", highlightthickness=0)
        self.canvas.pack(fill=tk.X, expand=True)
        
        # Add canvas bindings
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
    
    def on_position_changed(self, *args):
        """Called when the position variable changes, updates the UI."""
        if hasattr(self.app, 'eng') and self.app.eng.current_song:
            self.time_utils.update_time_label(self.pos.get(), self.app.eng.get_total_duration())
            
        # Only update marker positions if not dragging to avoid conflicts
        if not self.markers.dragging_marker:
            self.update_marker_positions()
    
    # Forward methods to appropriate component
    def update_time_label(self, current, total):
        """Forward to time_utils."""
        self.time_utils.update_time_label(current, total)
    
    def format_time(self, seconds):
        """Forward to time_utils."""
        return self.time_utils.format_time(seconds)
    
    def parse_time(self, time_str):
        """Forward to time_utils."""
        return self.time_utils.parse_time(time_str)
    
    def time_to_x(self, time):
        """Forward to time_utils."""
        return self.time_utils.time_to_x(time)
    
    def x_to_time(self, x):
        """Forward to time_utils."""
        return self.time_utils.x_to_time(x)
    
    def update_position_from_x(self, x):
        """Forward to time_utils."""
        self.time_utils.update_position_from_x(x)
    
    def draw_waveform(self):
        """Forward to waveform."""
        self.waveform.draw_waveform()
    
    def update_marker_positions(self):
        """Forward to markers."""
        self.markers.update_marker_positions()
    
    def on_canvas_click(self, event):
        """Forward to markers."""
        self.markers.on_canvas_click(event)
    
    def on_canvas_drag(self, event):
        """Forward to markers."""
        self.markers.on_canvas_drag(event)
    
    def on_canvas_release(self, event):
        """Forward to markers."""
        self.markers.on_canvas_release(event)