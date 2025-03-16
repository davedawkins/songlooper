class CanvasManager:
    """Manages the canvas drawing operations for the slider."""
    
    def __init__(self, slider_markers):
        self.slider_markers = slider_markers
        self.slider_view = slider_markers.slider_view
    
    def prepare_canvas(self, canvas, width, height):
        """Prepare the canvas by drawing the background and track line."""
        # Only clear marker lines, NOT the section
        canvas.delete("marker_line")
    
    def draw_section_background(self, canvas, start_x, end_x, content_top, content_bottom):
            """Draw the shaded background for the selected section area."""
            # First, clear any existing section background
            canvas.delete("section")
            
            # Get the label width from the SliderWaveform
            label_width = self.slider_view.waveform.LABEL_WIDTH
            
            # Ensure start_x is at least the label width
            start_x = max(label_width, start_x)
            
            # Use a very light color to keep waveforms visible
            canvas.create_rectangle(
                start_x, content_top - 5,
                end_x, content_bottom + 5,
                fill="#f0f8ff", outline="#d0e0ff", width=1, tags="section"
            )