
class CanvasManager:
    """Manages the canvas drawing operations for the slider."""
    
    def __init__(self, slider_markers):
        self.slider_markers = slider_markers
        self.slider_view = slider_markers.slider_view
    
    def prepare_canvas(self, canvas, width, height):
        """Prepare the canvas by drawing the background and track line."""
        # Clear canvas
        canvas.delete("all")
        
        # Draw background - solid white
        canvas.create_rectangle(
            0, 0, width, height,
            fill="#FFFFFF", outline=""
        )
        
        # Draw background track line
        canvas.create_line(
            10, height / 2, 
            width - 10, height / 2,
            fill="#dddddd", width=2
        )
    
    def draw_section_background(self, canvas, start_x, end_x, content_top, content_bottom):
        """Draw the shaded background for the selected section."""
        canvas.create_rectangle(
            start_x, content_top,
            end_x, content_bottom,
            fill="#e6f0ff", outline="", tags="section"
        )
