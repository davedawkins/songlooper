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
        
        # Position tracking
        # self.pos = tk.DoubleVar(value=0)
        # Add trace to position variable for data binding
        app.pos.trace_add("write", self.on_position_changed)
        
        # Create utility components first
        self.waveform = SliderWaveform(self)
        self.time_utils = SliderTimeUtils(self)
        self.markers = SliderMarkers(self)
        
        # Set up the UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the slider view UI."""
        # Main container frame with padding
        main_frame = ttk.Frame(self, padding=0)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Time label
        # self.time_label = ttk.Label(main_frame, text="00:00.0 / 00:00.0", width=20)
        # self.time_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Slider canvas frame
        self.slider_frame = ttk.Frame(main_frame)
        self.slider_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=0)
        
        # Calculate canvas height based on stem count
        canvas_height = self.calculate_canvas_height()
        
        # Canvas for markers with increased height and white background
        self.canvas = tk.Canvas(self.slider_frame, height=canvas_height, bg="#FFFFFF", 
                               highlightthickness=1, highlightbackground="#cccccc")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Add canvas bindings
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
    
    def calculate_canvas_height(self):
        """Calculate appropriate canvas height based on stem count."""
        # Default height for when there's no stem data
        default_height = 150
        
        # If no engine or no song loaded, return default
        if not hasattr(self.app, 'eng') or not self.app.eng.current_song:
            return default_height
            
        # Get stem count
        stem_count = len(self.app.eng.stems) if hasattr(self.app.eng, 'stems') else 0
        
        if stem_count == 0:
            return default_height
            
        # Calculate height:
        # - 100px top/bottom margins for markers (50px each)
        # - 40px per stem
        # - 15px spacing between stems
        height = 100 + (stem_count * 40) + ((stem_count - 1) * 15)
        
        # Set reasonable min/max
        return max(200, min(height, 600))
    
    def resize_canvas_if_needed(self):
        """Resize the canvas if the stem count has changed."""
        # Skip if not fully initialized
        if not hasattr(self, 'canvas'):
            return
            
        new_height = self.calculate_canvas_height()
        current_height = self.canvas.winfo_height()
        
        # If significantly different, resize
        if abs(new_height - current_height) > 30:
            self.canvas.config(height=new_height)
            
        # Always redraw after resize - important!
        self.update_marker_positions()
    
    def on_position_changed(self, *args):
        """Called when the position variable changes, updates the UI."""
        # if self.app.eng.current_song:
        #     self.time_utils.update_time_label(self.app.pos.get(), self.app.eng.get_total_duration())
            
        # Only update marker positions if not dragging to avoid conflicts
        if not self.markers.dragging_marker:
            self.update_marker_positions()
    
    # Forward methods to appropriate component
    # def update_time_label(self, current, total):
    #     """Forward to time_utils."""
    #     self.time_utils.update_time_label(current, total)
    
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
        # Check if we need to resize first
        self.resize_canvas_if_needed()
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