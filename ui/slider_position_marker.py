class PositionMarker:
    """Represents and manages the position marker in the slider."""
    
    def __init__(self, slider_markers):
        self.slider_markers = slider_markers
        self.slider_view = slider_markers.slider_view
    
    def draw(self, canvas, x, content_top, content_bottom):
        """Draw the position marker at the specified position."""
        # Position marker properties
        pos_triangle_width = 12
        pos_triangle_height = 10
        
        # Draw position marker line
        canvas.create_line(
            x, content_top, x, content_bottom, 
            fill="black", width=1, dash=(2, 1), tags="position_marker"
        )
        
        # Draw position marker triangle at BOTTOM
        canvas.create_polygon(
            x, content_bottom,
            x - pos_triangle_width/2, content_bottom + pos_triangle_height,
            x + pos_triangle_width/2, content_bottom + pos_triangle_height,
            fill="black", outline="black", width=1, tags="position_marker"
        )
    
    def handle_drag(self, x):
        """Update position based on drag to x coordinate."""
        new_time = self.slider_view.time_utils.x_to_time(x)
        self.slider_view.pos.set(new_time)
    
    def handle_release(self):
        """Handle release of position marker after dragging."""
        new_pos = self.slider_view.pos.get()
        
        # Update engine position
        self.slider_view.app.eng.set_start_position(new_pos)
        
        # Resume playback if it was playing before
        if self.slider_markers.was_playing:
            self.slider_view.app.play_current()
            self.slider_view.app.sts.set(f"Playback at {self.slider_view.time_utils.format_time(new_pos)}")
        else:
            self.slider_view.app.sts.set(f"Position: {self.slider_view.time_utils.format_time(new_pos)}")

