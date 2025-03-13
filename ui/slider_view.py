import tkinter as tk
from tkinter import ttk

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
        
        # Marker tracking
        self.dragging_marker = None
        
        # Set up the UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the slider view UI."""
        # Time label
        self.time_label = ttk.Label(self, text="0:00 / 0:00", width=12)
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
            self.update_time_label(self.pos.get(), self.app.eng.get_total_duration())
            
        # Only update marker positions if not dragging to avoid conflicts
        if not self.dragging_marker:
            self.update_marker_positions()
    
    def update_time_label(self, current, total):
        """Update the time display label."""
        c_min, c_sec = divmod(int(current), 60)
        t_min, t_sec = divmod(int(total), 60)
        time_text = f"{c_min}:{c_sec:02d} / {t_min}:{t_sec:02d}"
        self.time_label.config(text=time_text)
    
    def update_marker_positions(self):
        """Redraw all markers based on current position and section boundaries."""
        if not hasattr(self.app, 'eng') or not self.app.eng.current_song:
            return
        
        # Get canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1:  # Not yet drawn
            self.app.root.update_idletasks()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            if canvas_width <= 1:  # Still not ready
                return
        
        # Define constants for marker drawing
        triangle_width = 10
        triangle_height = 8
        margin = triangle_height + 2
        
        # Content area
        content_top = margin
        content_bottom = canvas_height - margin
        
        # Fetch current time values
        start_time = self.stt.get()
        end_time = self.ent.get()
        
        # Get current position
        current_pos = self.pos.get()
        
        # Calculate marker positions based on view mode
        if self.svm.get():
            # Section view mode - markers at edges
            start_x = 10
            end_x = canvas_width - 10
            
            # Position marker relative to section
            section_duration = max(0.1, end_time - start_time)
            pos_ratio = (current_pos - start_time) / section_duration
            pos_ratio = max(0, min(1, pos_ratio))  # Clamp between 0 and 1
            pos_x = 10 + pos_ratio * (canvas_width - 20)
        else:
            # Full song view - markers at relative positions
            total_duration = max(0.1, self.app.eng.get_total_duration())
            
            start_x = max(10, min(canvas_width - 20, (start_time / total_duration) * canvas_width))
            end_x = max(20, min(canvas_width - 10, (end_time / total_duration) * canvas_width))
            
            # Position marker
            pos_ratio = current_pos / total_duration
            pos_ratio = max(0, min(1, pos_ratio))  # Clamp between 0 and 1
            pos_x = pos_ratio * canvas_width
            pos_x = max(10, min(canvas_width - 10, pos_x))
        
        # Clear canvas
        self.canvas.delete("all")
        
        # Draw background track line
        self.canvas.create_line(
            0, canvas_height / 2, 
            canvas_width, canvas_height / 2,
            fill="#dddddd", width=2
        )
        
        # Draw shaded area between start and end markers
        self.canvas.create_rectangle(
            start_x, content_top,
            end_x, content_bottom,
            fill="#e6f0ff", outline="", tags="section"
        )
        
        # MARKERS - Order matters for overlapping (last drawn = top)
        
        # 1. Draw position marker (black triangle pointing UP from bottom)
        pos_triangle_width = 12
        pos_triangle_height = 10
        
        # Draw position marker line
        self.canvas.create_line(
            pos_x, content_top, pos_x, content_bottom, 
            fill="black", width=1, dash=(2, 1), tags="position_marker"
        )
        
        # Draw position marker triangle at BOTTOM
        self.canvas.create_polygon(
            pos_x, content_bottom,
            pos_x - pos_triangle_width/2, content_bottom + pos_triangle_height,
            pos_x + pos_triangle_width/2, content_bottom + pos_triangle_height,
            fill="black", outline="black", width=1, tags="position_marker"
        )
        
        # 2. Draw start marker (green triangle pointing DOWN from top)
        self.canvas.create_line(
            start_x, content_top, start_x, content_bottom, 
            fill="green", width=1, tags="start_marker"
        )
        
        self.canvas.create_polygon(
            start_x, content_top,
            start_x - triangle_width/2, content_top - triangle_height,
            start_x + triangle_width/2, content_top - triangle_height,
            fill="green", outline="black", width=1, tags="start_marker"
        )
        
        # 3. Draw end marker (red triangle pointing DOWN from top)
        self.canvas.create_line(
            end_x, content_top, end_x, content_bottom, 
            fill="red", width=1, tags="end_marker"
        )
        
        self.canvas.create_polygon(
            end_x, content_top,
            end_x - triangle_width/2, content_top - triangle_height,
            end_x + triangle_width/2, content_top - triangle_height,
            fill="red", outline="black", width=1, tags="end_marker"
        )
    
    def on_canvas_click(self, event):
        """Handle mouse click on canvas to select marker or set position."""
        # Check Y position to determine which marker to select
        canvas_height = self.canvas.winfo_height()
        
        # Define Y ranges for different markers
        top_region = 15  # Top area for start/end markers
        bottom_region = canvas_height - 15  # Bottom area for position marker
        
        # Items under cursor
        items = self.canvas.find_closest(event.x, event.y)
        
        # Y-coordinate based selection
        if event.y < top_region:
            # Top region - check for start/end markers
            for item in items:
                tags = self.canvas.gettags(item)
                if "start_marker" in tags:
                    self.dragging_marker = "start"
                    return
                elif "end_marker" in tags:
                    self.dragging_marker = "end"
                    return
        
        elif event.y > bottom_region:
            # Bottom region - check for position marker
            for item in items:
                tags = self.canvas.gettags(item)
                if "position_marker" in tags:
                    self.dragging_marker = "position"
                    return
        
        else:
            # Mid region - check all markers but with priority
            # First check for click on a marker line
            for item in items:
                tags = self.canvas.gettags(item)
                if "position_marker" in tags:
                    self.dragging_marker = "position"
                    return
                elif "start_marker" in tags:
                    self.dragging_marker = "start"
                    return
                elif "end_marker" in tags:
                    self.dragging_marker = "end"
                    return
        
        # If we get here, user clicked on empty space - set position directly
        self.update_position_from_x(event.x)
    
    def on_canvas_drag(self, event):
        """Handle drag motion on canvas."""
        if not self.dragging_marker:
            return
        
        # Constrain x to canvas bounds
        canvas_width = self.canvas.winfo_width()
        x = max(10, min(event.x, canvas_width - 10))
        
        if self.dragging_marker == "start":
            # Prevent start marker from going past end marker
            end_time = self.ent.get()
            end_x = self.time_to_x(end_time)
            if x >= end_x - 15:
                x = end_x - 15
            
            # Update start time
            new_time = self.x_to_time(x)
            self.stt.set(round(new_time, 2))
            
        elif self.dragging_marker == "end":
            # Prevent end marker from going before start marker
            start_time = self.stt.get()
            start_x = self.time_to_x(start_time)
            if x <= start_x + 15:
                x = start_x + 15
                
            # Update end time
            new_time = self.x_to_time(x)
            self.ent.set(round(new_time, 2))
            
        elif self.dragging_marker == "position":
            # Update position time
            new_time = self.x_to_time(x)
            self.pos.set(new_time)
            
        # Redraw markers
        self.update_marker_positions()
    
    def on_canvas_release(self, event):
        """Handle release of mouse button after dragging."""
        if not self.dragging_marker:
            return
        
        if self.dragging_marker == "position":
            # When position marker is released, update the engine position
            new_pos = self.pos.get()
            was_playing = self.app.eng.is_playing()
            
            # Update engine position
            self.app.eng.stop()
            self.app.eng.set_start_position(new_pos)
            
            if was_playing:
                self.app.play_current()
                self.app.sts.set(f"Playback at {new_pos:.1f}s")
            else:
                self.app.sts.set(f"Position: {new_pos:.2f}s")
        
        elif self.dragging_marker == "start":
            # Check if current position is now before section start
            start_time = self.stt.get()
            current_pos = self.app.eng.get_current_position()
            
            if self.app.eng.is_playing() and current_pos < start_time:
                # Restart playback from new section start
                self.app.eng.stop()
                self.app.eng.set_start_position(start_time)
                self.app.play_current()
                self.app.sts.set(f"Restarted playback from new start: {start_time:.2f}s")
            else:
                self.app.sts.set(f"Section start: {start_time:.2f}s")
                
        elif self.dragging_marker == "end":
            end_time = self.ent.get()
            self.app.sts.set(f"Section end: {end_time:.2f}s")
        
        # Clear dragging state
        self.dragging_marker = None
    
    def update_position_from_x(self, x):
        """Update position based on x coordinate."""
        if not self.app.eng.current_song:
            return
            
        # Calculate time at this x position
        new_pos = self.x_to_time(x)
        
        # Update engine position
        was_playing = self.app.eng.is_playing()
        if was_playing:
            self.app.eng.stop()
        
        self.app.eng.set_start_position(new_pos)
        
        # Update position variable - triggers UI update through trace
        self.pos.set(new_pos)
        
        # Resume playback if needed
        if was_playing:
            self.app.play_current()
            
        self.app.sts.set(f"Position: {new_pos:.2f}s")
    
    def x_to_time(self, x):
        """Convert x coordinate to time value."""
        canvas_width = self.canvas.winfo_width()
        
        if self.svm.get():
            # Section view
            start_time = self.stt.get()
            end_time = self.ent.get()
            section_range = max(0.1, end_time - start_time)
            
            position_ratio = (x - 10) / max(1, canvas_width - 20)
            position_ratio = max(0, min(1, position_ratio))
            return start_time + position_ratio * section_range
        else:
            # Full song view
            total_duration = max(0.1, self.app.eng.get_total_duration())
            
            position_ratio = x / max(1, canvas_width)
            position_ratio = max(0, min(1, position_ratio))
            return position_ratio * total_duration
    
    def time_to_x(self, time):
        """Convert time value to x coordinate."""
        canvas_width = self.canvas.winfo_width()
        
        if self.svm.get():
            # Section view
            start_time = self.stt.get()
            end_time = self.ent.get()
            section_range = max(0.1, end_time - start_time)
            
            position_ratio = (time - start_time) / section_range
            position_ratio = max(0, min(1, position_ratio))
            return 10 + position_ratio * (canvas_width - 20)
        else:
            # Full song view
            total_duration = max(0.1, self.app.eng.get_total_duration())
            
            position_ratio = time / total_duration
            position_ratio = max(0, min(1, position_ratio))
            return position_ratio * canvas_width