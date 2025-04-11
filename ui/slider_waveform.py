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
        self._waveform_cache = {}
    
    def invalidate_cache(self):
        """Clear the waveform cache. Should be called when stems or the song changes."""
        self._waveform_cache.clear()

    def stemHitTest(self, x, y):
        label_start = 0
        if x > label_start and x < label_start + self.LABEL_WIDTH:
            # Check if y is within the range of any stem
            for i, stem_name in enumerate(self.stem_names):
                stem_top = self.TOP_MARGIN + i * (self.stem_height + self.STEM_SPACING)
                stem_bottom = stem_top + self.stem_height
                if y > stem_top and y < stem_bottom:
                    return stem_name

        return None

    def _compute_waveform_points(self, audio_data, num_chunks):
        points = []
        visible_samples = len(audio_data)
        chunk_size = max(1, visible_samples // num_chunks)
        for j in range(num_chunks):
            chunk_start = j * chunk_size
            chunk_end = min(visible_samples, (j + 1) * chunk_size)
            if chunk_start >= len(audio_data):
                break
            chunk_data = audio_data[chunk_start:chunk_end]
            if len(chunk_data) == 0:
                continue
            peak = np.max(np.abs(chunk_data))
            points.append((j, peak))
        return points

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
        
        if not self._waveform_cache:
            for stem_name in stems:
                audio_data = stems[stem_name]
                if audio_data.ndim > 1:
                    audio_data = audio_data[:, 0]
                
                max_amp = np.max(np.abs(audio_data)) if len(audio_data) > 0 else 1.0
                if max_amp < 0.001:
                    max_amp = 1.0
                
                display_name = short_name(stem_name)
                if len(display_name) > 20:
                    display_name = display_name[:18] + "..."
                
                num_chunks = min(canvas_width - self.LABEL_WIDTH - 20, 1000)
                points = self._compute_waveform_points(audio_data, num_chunks)
                
                self._waveform_cache[stem_name] = {
                    "audio_data": audio_data,
                    "max_amp": max_amp,
                    "display_name": display_name,
                    "points": None,
                    "range": None
                }
        
        # Calculate height for each stem
        stem_names = list(stems.keys())
        num_stems = len(stem_names)
        
        # Calculate available height for waveforms
        available_height = canvas_height - self.TOP_MARGIN - self.BOTTOM_MARGIN
        stem_height = max(30, int((available_height - (self.STEM_SPACING * (num_stems - 1))) / num_stems))

        self.stem_names = stem_names
        self.stem_height = stem_height

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
            
            # Draw stem label background
            self.slider_view.canvas.create_rectangle(
                0, stem_top - self.STEM_SPACING//2,
                self.LABEL_WIDTH, stem_bottom + self.STEM_SPACING//2,
                fill="#e8e8e8", outline="", tags="stem_bg"
            )
            
            # Draw stem label
            cached = self._waveform_cache[stem_name]
            display_name = cached["display_name"]
            max_amp = cached["max_amp"]
            audio_data = cached["audio_data"]
            canvas_width = self.slider_view.canvas.winfo_width()
            
            if self.app.svm.get():
                start_time = SliderTimeUtils.parse_time(self.app.stt.get())
                end_time = SliderTimeUtils.parse_time(self.app.ent.get())
                sample_rate = self.app.eng.stem_srs
                total_samples = len(audio_data)

                start_sample = int(start_time * sample_rate)
                end_sample = int(end_time * sample_rate)
            else:
                start_sample = 0
                end_sample = len(audio_data)

            current_range = (start_sample, end_sample)
            cached_range = cached["range"]

            if cached["points"] is None or cached_range != current_range:
                view_audio = audio_data[start_sample:end_sample]
                num_chunks = max(1, canvas_width - self.LABEL_WIDTH - 20)
                cached["points"] = self._compute_waveform_points(view_audio, num_chunks)
                cached["range"] = current_range

            points_raw = cached["points"]
            
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
            
            # Skip empty waveforms
            if len(points_raw) == 0:
                continue
                
            # Draw waveform lines
            amp_scale = stem_height * 0.6
            fill_color = "#aaaaaa" if is_muted else "#5080ff"
            points_raw = list(enumerate([peak for _, peak in points_raw]))

            for j, peak in points_raw:
                peak_scaled = (peak / max_amp) * amp_scale
                x_pos = self.LABEL_WIDTH + 10 + int((j / len(points_raw)) * (canvas_width - self.LABEL_WIDTH - 20))
                self.slider_view.canvas.create_line(
                    x_pos, stem_center - peak_scaled,
                    x_pos, stem_center + peak_scaled,
                    fill=fill_color,
                    width=1,
                    tags="waveform"
                )