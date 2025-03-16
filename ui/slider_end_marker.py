
class EndMarker:
    """Represents and manages the section end marker in the slider."""
    
    def __init__(self, slider_markers):
        self.slider_markers = slider_markers
        self.slider_view = slider_markers.slider_view
    
    def draw(self, canvas, x, content_top, content_bottom):
        """Draw the end marker at the specified position."""
        # Marker properties
        triangle_width = 10
        triangle_height = 8
        
        # Draw end marker line
        canvas.create_line(
            x, content_top, x, content_bottom, 
            fill="red", width=1, tags="end_marker"
        )
        
        # Draw end marker triangle
        canvas.create_polygon(
            x, content_top,
            x - triangle_width/2, content_top - triangle_height,
            x + triangle_width/2, content_top - triangle_height,
            fill="red", outline="black", width=1, tags="end_marker"
        )
    
    def handle_drag(self, x):
        """Update end time based on drag to x coordinate."""
        # Prevent end marker from going before start marker
        start_time = self.slider_view.time_utils.parse_time(self.slider_view.stt.get())
        start_x = self.slider_view.time_utils.time_to_x(start_time)
        if x <= start_x + 15:
            x = start_x + 15
            
        # Update end time
        new_time = self.slider_view.time_utils.x_to_time(x)
        self.slider_view.ent.set(self.slider_view.time_utils.format_time(new_time))
    
    def handle_release(self):
        """Handle release of end marker after dragging."""
        end_time = self.slider_view.time_utils.parse_time(self.slider_view.ent.get())
        
        # Resume playback if needed
        if self.slider_markers.was_playing:
            self.slider_view.app.play_current()
        
        self.slider_view.app.sts.set(f"Section end: {self.slider_view.time_utils.format_time(end_time)}")

