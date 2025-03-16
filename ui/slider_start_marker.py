
class StartMarker:
    """Represents and manages the section start marker in the slider."""
    
    def __init__(self, slider_markers):
        self.slider_markers = slider_markers
        self.slider_view = slider_markers.slider_view
    
    def draw(self, canvas, x, content_top, content_bottom):
        """Draw the start marker at the specified position."""
        # Marker properties
        triangle_width = 10
        triangle_height = 8
        
        # Draw start marker line
        canvas.create_line(
            x, content_top, x, content_bottom, 
            fill="green", width=1, tags="start_marker"
        )
        
        # Draw start marker triangle
        canvas.create_polygon(
            x, content_top,
            x - triangle_width/2, content_top - triangle_height,
            x + triangle_width/2, content_top - triangle_height,
            fill="green", outline="black", width=1, tags="start_marker"
        )
    
    def handle_drag(self, x):
        """Update start time based on drag to x coordinate."""
        # Prevent start marker from going past end marker
        end_time = self.slider_view.time_utils.parse_time(self.slider_view.ent.get())
        end_x = self.slider_view.time_utils.time_to_x(end_time)
        if x >= end_x - 15:
            x = end_x - 15
        
        # Update start time
        new_time = self.slider_view.time_utils.x_to_time(x)
        self.slider_view.stt.set(self.slider_view.time_utils.format_time(new_time))
    
    def handle_release(self):
        """Handle release of start marker after dragging."""
        start_time = self.slider_view.time_utils.parse_time(self.slider_view.stt.get())
        
        if self.slider_markers.was_playing:
            # Restart playback from new section start
            self.slider_view.app.eng.set_start_position(start_time)
            self.slider_view.app.play_current()
            self.slider_view.app.sts.set(f"Restarted playback from new start: {self.slider_view.time_utils.format_time(start_time)}")
        else:
            self.slider_view.app.sts.set(f"Section start: {self.slider_view.time_utils.format_time(start_time)}")

