"""Waveform drawing functionality for the slider view with individual stem displays."""

import numpy as np
from ui.slider_time_utils import SliderTimeUtils
import re


def short_name(text):
    parts = re.split(r"[ _-]+", text)
    return parts[len(parts)-1] if len(parts) > 1 else text

class SliderWaveform:
    """Handles drawing and rendering of individual audio waveforms for each stem in the slider."""
    
    def __init__(self, slider_view):
        """Initialize with reference to the parent SliderView."""
        self.slider_view = slider_view
        self.app = slider_view.app
        
        # Constants for layout
        self.LABEL_WIDTH = 180
        self.TOP_MARGIN = 50
        self.BOTTOM_MARGIN = 50
        self.STEM_SPACING = 15
    
    def draw_waveform(self):
        """Draw individual waveform representations for each stem."""
        if not hasattr(self.slider_view.app, 'eng') or not self.slider_view.app.eng.current_song or not self.slider_view.app.eng.stems:
            return
        
        # Get canvas dimensions
        canvas_width = self.slider_view.canvas.winfo_width()
        canvas_height = self.slider_view.canvas.winfo_height()
        
        if canvas_width <= 1:  # Canvas not yet drawn
            return
        
        # Clear previous waveform
        self.slider_view.canvas.delete("waveform")
        self.slider_view.canvas.delete("stem_label")
        self.slider_view.canvas.delete("stem_bg")
        
        # Get stems
        stems = self.slider_view.app.eng.stems
        if not stems:
            return
            
        # Calculate height for each stem
        stem_names = list(stems.keys())
        num_stems = len(stem_names)
        
        # Calculate available height for waveforms
        available_height = canvas_height - self.TOP_MARGIN - self.BOTTOM_MARGIN
        stem_height = max(30, int((available_height - (self.STEM_SPACING * (num_stems - 1))) / num_stems))
        
        # Draw vertical separator line between labels and waveforms
        self.slider_view.canvas.create_line(
            self.LABEL_WIDTH, 0, 
            self.LABEL_WIDTH, canvas_height,
            fill="#cccccc", width=1, tags="stem_bg"
        )
        
        # Draw each stem's waveform
        for i, stem_name in enumerate(stem_names):
            # Calculate y-position for this stem
            stem_top = self.TOP_MARGIN + i * (stem_height + self.STEM_SPACING)
            stem_bottom = stem_top + stem_height
            stem_center = (stem_top + stem_bottom) / 2
            
            # Check if stem is muted
            is_muted = stem_name in self.slider_view.app.eng.muted_stems
            
            # Draw stem background
            bg_color = "#f8f8f8" if i % 2 == 0 else "#f0f0f0"  # Alternate colors
            # self.slider_view.canvas.create_rectangle(
            #     0, stem_top - self.STEM_SPACING//2,
            #     canvas_width, stem_bottom + self.STEM_SPACING//2,
            #     fill=bg_color, outline="", tags="stem_bg"
            # )
            
            # Draw stem label background
            self.slider_view.canvas.create_rectangle(
                0, stem_top - self.STEM_SPACING//2,
                self.LABEL_WIDTH, stem_bottom + self.STEM_SPACING//2,
                fill="#e8e8e8", outline="", tags="stem_bg"
            )
            
            # Draw stem label
            # Truncate stem name if too long
            display_name = short_name(stem_name)
            if len(display_name) > 20:
                display_name = display_name[:18] + "..."

            self.slider_view.canvas.create_text(
                10, stem_center,
                text=display_name, anchor="w",
                tags="stem_label",
                fill="#666666" if is_muted else "#000000"
            )
            
            # Draw horizontal separator line for this stem
            if i > 0:
                y_sep = stem_top - self.STEM_SPACING//2
                self.slider_view.canvas.create_line(
                    0, y_sep, canvas_width, y_sep,
                    fill="#dddddd", width=1, tags="stem_bg"
                )
            
            # Get audio data for this stem
            audio_data = stems[stem_name]
            
            # Only use first channel for visualization
            if audio_data.ndim > 1:
                audio_data = audio_data[:, 0]
                
            # Determine visible range based on section view mode
            if self.app.svm.get():
                # In section view, only show the section part of the waveform
                start_time = SliderTimeUtils.parse_time(self.app.stt.get())
                end_time = SliderTimeUtils.parse_time(self.app.ent.get())
                
                if start_time is None or end_time is None:
                    continue
                    
                total_samples = len(audio_data)
                start_sample = int(start_time * self.slider_view.app.eng.stem_srs)
                end_sample = int(end_time * self.slider_view.app.eng.stem_srs)
                
                # Ensure valid range
                start_sample = max(0, min(start_sample, total_samples - 1))
                end_sample = max(start_sample + 1, min(end_sample, total_samples))
                
                waveform_data = audio_data[start_sample:end_sample]
                visible_samples = end_sample - start_sample
            else:
                # In full view, show the entire waveform
                waveform_data = audio_data
                visible_samples = len(waveform_data)
            
            # Skip empty waveforms
            if len(waveform_data) == 0:
                continue
                
            # Calculate amplitude scale (60% of stem height)
            max_amp = np.max(np.abs(waveform_data)) if len(waveform_data) > 0 else 1.0
            if max_amp < 0.001:  # Avoid division by near-zero
                max_amp = 1.0
                
            amp_scale = stem_height * 0.6
            
            # Efficient algorithm to convert waveform to display points
            # Process in chunks for better performance
            num_chunks = min(canvas_width - self.LABEL_WIDTH - 20, 1000)  # Cap at 1000 points for performance
            chunk_size = max(1, visible_samples // num_chunks)
            
            # Choose fill color based on mute status
            fill_color = "#aaaaaa" if is_muted else "#5080ff"
            
            points = []
            for j in range(num_chunks):
                chunk_start = j * chunk_size
                chunk_end = min(visible_samples, (j + 1) * chunk_size)
                
                if chunk_start >= len(waveform_data):
                    break
                    
                # Get maximum amplitude in this chunk for peak visualization
                chunk_data = waveform_data[chunk_start:chunk_end]
                if len(chunk_data) == 0:
                    continue
                    
                peak = np.max(np.abs(chunk_data))
                
                # Normalize and scale
                peak_scaled = (peak / max_amp) * amp_scale
                
                # Calculate x position - ensure it starts after label width
                x_pos = self.LABEL_WIDTH + 10 + int((j / num_chunks) * (canvas_width - self.LABEL_WIDTH - 20))
                
                # Add line from center to peak and center to -peak
                points.append((x_pos, stem_center - peak_scaled, x_pos, stem_center + peak_scaled))
            
            # Draw waveform lines
            for x1, y1, x2, y2 in points:
                self.slider_view.canvas.create_line(
                    x1, y1, x2, y2, 
                    fill=fill_color, 
                    width=1, 
                    tags="waveform"
                )