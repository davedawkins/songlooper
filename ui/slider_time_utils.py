"""Utility functions for time handling and conversions in the slider view."""

import tkinter as tk

class SliderTimeUtils:
    """Handles time formatting, parsing, and coordinate conversions for the slider."""
    
    def __init__(self, slider_view):
        """Initialize with reference to the parent SliderView."""
        self.slider_view = slider_view
    
    def format_time(self, seconds):
        """Format time in mm:ss.c format."""
        minutes, sec_frac = divmod(seconds, 60)
        sec = int(sec_frac)
        decisec = int((sec_frac - sec) * 10)  # Only one decimal place
        return f"{int(minutes):02d}:{sec:02d}.{decisec}"

    def parse_time(self, time_str):
        """Parse time from either mm:ss.c format or float seconds."""
        if ":" in time_str:
            try:
                # Parse from mm:ss.c format
                parts = time_str.split(":")
                minutes = int(parts[0])
                if "." in parts[1]:
                    sec_parts = parts[1].split(".")
                    seconds = int(sec_parts[0])
                    if len(sec_parts[1]) > 0:
                        # Only use the first digit for deciseconds
                        decisec = int(sec_parts[1][0])
                        return minutes * 60 + seconds + decisec / 10
                    else:
                        return minutes * 60 + seconds
                else:
                    seconds = float(parts[1])
                    return minutes * 60 + seconds
            except (ValueError, IndexError):
                return None
        else:
            try:
                # Parse as raw seconds
                return float(time_str)
            except ValueError:
                return None

    def update_time_label(self, current, total):
        """Update the time display label with format mm:ss.c."""
        time_text = f"{self.format_time(current)} / {self.format_time(total)}"
        self.slider_view.time_label.config(text=time_text)
    
    def time_to_x(self, time):
        """Convert time value to x coordinate."""
        canvas_width = self.slider_view.canvas.winfo_width()
        
        if self.slider_view.svm.get():
            # Section view
            start_time = self.parse_time(self.slider_view.stt.get())
            end_time = self.parse_time(self.slider_view.ent.get())
            section_range = max(0.1, end_time - start_time)
            
            position_ratio = (time - start_time) / section_range
            position_ratio = max(0, min(1, position_ratio))
            # Add the left margin (10px)
            return 10 + position_ratio * (canvas_width - 20)
        else:
            # Full song view
            total_duration = max(0.1, self.slider_view.app.eng.get_total_duration())
            
            position_ratio = time / total_duration
            position_ratio = max(0, min(1, position_ratio))
            # Add the left margin (10px)
            return 10 + position_ratio * (canvas_width - 20)
    
    def x_to_time(self, x):
        """Convert x coordinate to time value."""
        canvas_width = self.slider_view.canvas.winfo_width()
        
        if self.slider_view.svm.get():
            # Section view
            start_time = self.parse_time(self.slider_view.stt.get())
            end_time = self.parse_time(self.slider_view.ent.get())
            section_range = max(0.1, end_time - start_time)
            
            # Adjust for the padding (10px on each side)
            usable_width = max(1, canvas_width - 20)
            position_ratio = max(0, min(1, (x - 10) / usable_width))
            return start_time + position_ratio * section_range
        else:
            # Full song view
            total_duration = max(0.1, self.slider_view.app.eng.get_total_duration())
            
            # Adjust for the padding (10px on each side)
            usable_width = max(1, canvas_width - 20)
            position_ratio = max(0, min(1, (x - 10) / usable_width))
            return position_ratio * total_duration
    
    def update_position_from_x(self, x):
        """Update position based on x coordinate."""
        if not self.slider_view.app.eng.current_song:
            return
            
        # Calculate time at this x position
        new_pos = self.x_to_time(x)
        
        # Update engine position
        was_playing = self.slider_view.app.eng.is_playing()
        if was_playing:
            self.slider_view.app.eng.stop()
        
        self.slider_view.app.eng.set_start_position(new_pos)
        
        # Update position variable - triggers UI update through trace
        self.slider_view.pos.set(new_pos)
        
        # Resume playback if needed
        if was_playing:
            self.slider_view.app.play_current()
            self.slider_view.app.sts.set(f"Position: {self.format_time(new_pos)}")
        else:
            self.slider_view.app.sts.set(f"Position: {self.format_time(new_pos)}")