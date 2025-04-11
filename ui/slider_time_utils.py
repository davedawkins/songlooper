"""Utility functions for time handling and conversions in the slider view."""

import tkinter as tk

class SliderTimeUtils:
    """Handles time formatting, parsing, and coordinate conversions for the slider."""
    
    def __init__(self, slider_view):
        """Initialize with reference to the parent SliderView."""
        self.slider_view = slider_view
        self.app = slider_view.app
        
    def format_time(seconds):
        """Format time in mm:ss.c format."""
        minutes, sec_frac = divmod(seconds, 60)
        sec = int(sec_frac)
        msec = int((sec_frac - sec) * 1000)  # 3 decimal places
        return f"{int(minutes):02d}:{sec:02d}.{msec}"

    def parse_time(time_str):
        """Parse time from either mm:ss.c format or float seconds."""
        if ":" in time_str:
            try:
                # Parse from mm:ss.c format
                parts = time_str.split(":")
                minutes = int(parts[0])
                seconds = float(parts[1])
                # if "." in parts[1]:
                #     sec_parts = parts[1].split(".")
                #     seconds = int(sec_parts[0])
                #     if len(sec_parts[1]) > 0:
                #         msec = int(sec_parts[1][0])
                #         return minutes * 60 + seconds + msec / 1000
                #     else:
                #         return minutes * 60 + seconds
                # else:
                #     seconds = float(parts[1])
                return minutes * 60.0 + seconds
            except (ValueError, IndexError):
                return None
        else:
            try:
                # Parse as raw seconds
                return float(time_str)
            except ValueError:
                return None

    # def update_time_label(self, current, total):
    #     """Update the time display label with format mm:ss.c."""
    #     time_text = f"{SliderTimeUtils.format_time(current)} / {SliderTimeUtils.format_time(total)}"
    #     self.slider_view.time_label.config(text=time_text)
    
    def time_to_x(self, time):
        """Convert time value to x coordinate."""
        canvas_width = self.slider_view.canvas.winfo_width()
        label_width = self.slider_view.waveform.LABEL_WIDTH
        
        if self.app.svm.get():
            # Section view
            start_time = SliderTimeUtils.parse_time(self.app.stt.get())
            end_time = SliderTimeUtils.parse_time(self.app.ent.get())
            section_range = max(0.1, end_time - start_time)
            
            position_ratio = (time - start_time) / section_range
            position_ratio = max(0, min(1, position_ratio))
            # Scale to usable area (after label width)
            usable_width = max(1, canvas_width - label_width - 20)
            return label_width + 10 + position_ratio * usable_width
        else:
            # Full song view
            total_duration = max(0.1, self.slider_view.app.eng.get_total_duration())
            
            position_ratio = time / total_duration
            position_ratio = max(0, min(1, position_ratio))
            # Scale to usable area (after label width)
            usable_width = max(1, canvas_width - label_width - 20)
            return label_width + 10 + position_ratio * usable_width
    
    def x_to_time(self, x):
        """Convert x coordinate to time value."""
        canvas_width = self.slider_view.canvas.winfo_width()
        label_width = self.slider_view.waveform.LABEL_WIDTH
        
        # Only consider clicks after the label area
        if x <= label_width:
            x = label_width + 1
        
        if self.app.svm.get():
            # Section view
            start_time = SliderTimeUtils.parse_time(self.app.stt.get())
            end_time = SliderTimeUtils.parse_time(self.app.ent.get())
            section_range = max(0.1, end_time - start_time)
            
            # Adjust for the padding and label width
            usable_width = max(1, canvas_width - label_width - 20)
            position_ratio = max(0, min(1, (x - label_width - 10) / usable_width))
            return start_time + position_ratio * section_range
        else:
            # Full song view
            total_duration = max(0.1, self.slider_view.app.eng.get_total_duration())
            
            # Adjust for the padding and label width
            usable_width = max(1, canvas_width - label_width - 20)
            position_ratio = max(0, min(1, (x - label_width - 10) / usable_width))
            return position_ratio * total_duration
    
    def update_position_from_x(self, x):
        """Update position based on x coordinate."""
        if not self.slider_view.app.eng.current_song:
            return
            
        # Only consider clicks after the label area
        label_width = self.slider_view.waveform.LABEL_WIDTH
        if x <= label_width:
            return
            
        # Calculate time at this x position
        new_pos = self.x_to_time(x)
        
        # Update engine position
        was_playing = self.slider_view.app.eng.is_playing()
        if was_playing:
            self.slider_view.app.eng.pause()
        
        print("update_position_from_x: Setting engine start position: " + str(new_pos))
        self.slider_view.app.eng.set_position(new_pos)
        
        # Update position variable - triggers UI update through trace
        self.app.pos.set(new_pos)
        
        # Resume playback if needed
        if was_playing:
            self.slider_view.app.play_current()
            self.slider_view.app.sts.set(f"Position: {SliderTimeUtils.format_time(new_pos)}")
        else:
            self.slider_view.app.sts.set(f"Position: {SliderTimeUtils.format_time(new_pos)}")