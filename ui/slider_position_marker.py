from ui.slider_time_utils import SliderTimeUtils

class PositionMarker:
    """Represents and manages the position marker in the slider."""
    
    def __init__(self, slider_markers):
        self.slider_markers = slider_markers
        self.app = slider_markers.app
        self.slider_view = slider_markers.slider_view
    
    def draw(self, canvas, x, content_top, content_bottom):
        """Draw the position marker at the specified position."""
        # Calculate actual vertical bounds for stems
        num_stems = len(self.slider_view.app.eng.stems) if hasattr(self.slider_view.app.eng, 'stems') else 0
        if num_stems == 0:
            return
            
        # Get label width and ensure x is after label
        label_width = self.slider_view.waveform.LABEL_WIDTH
        x = max(label_width, x)
        
        # Position marker properties
        pos_triangle_width = 12
        pos_triangle_height = 10
        
        # Draw position marker line - expand slightly beyond waveform area
        canvas.create_line(
            x, content_top - 5, x, content_bottom + 5, 
            fill="black", width=1, dash=(4, 2), tags="position_marker"
        )
        
        # Draw position marker triangle OUTSIDE the waveform area (below it)
        canvas.create_polygon(
            x, content_bottom + 5,
            x - pos_triangle_width/2, content_bottom + 5 + pos_triangle_height,
            x + pos_triangle_width/2, content_bottom + 5 + pos_triangle_height,
            fill="black", outline="black", width=1, tags="position_marker"
        )
    
    def handle_drag(self, x):
        """Update position based on drag to x coordinate."""
        new_time = self.slider_view.time_utils.x_to_time(x)
        self.app.pos.set(new_time)

    def handle_release(self):
        """Handle release of position marker after dragging."""
        new_pos = self.app.pos.get()
        
        # Update engine position
        self.app.eng.set_position(new_pos)
        
        # Resume playback if it was playing before
        if self.slider_markers.was_playing:
            self.slider_view.app.play_current()
            self.slider_view.app.sts.set(f"Playback at {SliderTimeUtils.format_time(new_pos)}")
        else:
            self.slider_view.app.sts.set(f"Position: {SliderTimeUtils.format_time(new_pos)}")