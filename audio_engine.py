import os
import time
import threading
import json
import numpy as np
import sounddevice as sd
import soundfile as sf
import librosa
from dataclasses import dataclass
from typing import List, Optional
import pyrubberband as pyrb

@dataclass
class Section:
    name: str
    muted: bool
    level: float
    start_time: float
    end_time: float

@dataclass
class SongConfig:
    title: str
    path: str
    bpm: float
    sections: List[Section]
    current_section: str

class AudioEngine:
    def __init__(self):
        self.current_song: Optional[SongConfig] = None
        
        self.playing = False
        self.loop = False
        self.playback_speed = 1.0
        self.loop_delay = 0.0
        
        # Stems
        self.stems = {}
        self.stem_srs = 0
        self.muted_stems = set()
        self.processed_stems = {}
        
        self.playback_thread = None
        self.stop_event = threading.Event()
        
        self.count_in = False
        
        # We'll store a "start_position" (seconds) for the next playback.
        self._start_position = 0.0
        self._end_position = 0.0

        # We track the actual playback position in real time:
        self._current_position = 0.0
        
        # Callback for when mute status changes
        self.mute_status_change_callback = { }
        self.next_mute_cb_id = 0


    # -------------------------------------------------------
    #   GETTERS / SETTERS
    # -------------------------------------------------------
    def set_position(self, pos: float):
        """Next playback will begin from 'pos' seconds."""
        self._current_position = pos

    def set_loop( self, loop : bool):
        self.loop = loop

    def set_playback_speed( self, speed : float):
        self.playback_speed = speed

    def set_loop_delay( self, delay : float):
        self.loop_delay = delay

    def get_start_position(self) -> float:
        return self._start_position

    def set_start_position(self, pos: float):
        """Next playback will end at 'pos' seconds."""
        print("Engine: start position: " + str(pos))
        self._start_position = pos

    def set_end_position(self, pos: float):
        """Next playback will end at 'pos' seconds."""
        print("Engine: end position: " + str(pos))
        self._end_position = pos

    def get_end_position(self) -> float:
        return self._end_position
    
    def get_current_position(self) -> float:
        """Approximate last-known position in the original track."""
        return self._current_position

    def is_playing(self) -> bool:
        return self.playing
        
    def add_mute_callback(self, callback):
        """Set a callback function to be called when mute status changes."""
        client_id = self.next_mute_cb_id
        self.next_mute_cb_id += 1
        self.mute_status_change_callback[client_id] = callback
        return client_id

    def remove_mute_callback(self, client_id):
        """Remove a previously registered callback."""
        if client_id in self.mute_status_change_callback:
            del self.mute_status_change_callback[client_id]
        else:
            print(f"Warning: Callback ID {client_id} not found.")
    # -------------------------------------------------------
    #   SONG LOADING
    # -------------------------------------------------------
    def get_available_songs(self, base_folder: str) -> List[str]:
        """Return subfolders that contain a config.json file."""
        return [
            folder for folder in os.listdir(base_folder)
            if os.path.isdir(os.path.join(base_folder, folder)) and
               os.path.exists(os.path.join(base_folder, folder, 'config.json'))
        ]
    
    def find_section(self, section_name):
        target = None
        for s in self.current_song.sections:
            if s.name == section_name:
                target = s
                break
        return target

    def clear_stem_cache(self):
        self.processed_stems.clear()

    def load_song(self, song_folder: str) -> SongConfig:
        config_path = os.path.join(song_folder, "config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"No config.json in {song_folder}")
        
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        sections = []
        for sec in config_data.get('sections', []):
            sections.append(Section(sec['name'], sec.get("muted", False), sec.get("level", 1.0), sec['start_time'], sec['end_time']))
        
        song_cfg = SongConfig(
            title=config_data.get('title', os.path.basename(song_folder)),
            path=song_folder,
            bpm=config_data.get('bpm', 120.0),
            sections=sections,
            current_section=config_data.get("current_section", "Full Song")
        )
        
        # Clear old stems
        self.stems.clear()
        self.clear_stem_cache()
        
        # Load each audio file
        for file in os.listdir(song_folder):
            if file.lower().endswith(('.wav', '.mp3', '.flac', '.ogg')):
                stem_name = os.path.splitext(file)[0]
                file_path = os.path.join(song_folder, file)
                audio_data, samplerate = sf.read(file_path)
                self.stems[stem_name] = audio_data
                self.stem_srs = samplerate
        
        if not self.stems:
            raise FileNotFoundError(f"No audio files in {song_folder}")
        
        self.current_song = song_cfg
        self.muted_stems = set()
        
        # Reset positions
        self._start_position = 0.0
        self._current_position = 0.0
        self._end_position = self.get_total_duration()

        current_section = self.find_section( song_cfg.current_section )

        if current_section:
            print("loaded: " + str(current_section))
            self._start_position = current_section.start_time
            self._current_position = current_section.start_time
            self._end_position = current_section.end_time

        return song_cfg
    
    def get_stem_names(self) -> List[str]:
        return list(self.stems.keys())

    def play_section(self):
        """Play from _start_position to the end of the chosen section (or full track)."""
        if not self.current_song:
            raise ValueError("No song loaded.")
        
        # Stop any existing playback
        self.stop()
        
        # Clear so we can start fresh
        self.stop_event.clear()

        # If the user start_position is before the section's start, clamp
        print("Playing init: cur=" + str(self._current_position) + " start=" + str(self._start_position))

        if self._current_position < self._start_position or self._current_position > self._end_position:
            self._current_position = self._start_position
        
        self.playing = True

        # Start worker thread
        self.playback_thread = threading.Thread(target=self._playback_worker)
        self.playback_thread.daemon = True
        self.playback_thread.start()

    def stop(self):
        self.pause()
        
    def pause(self):
        """Pause = Stop plus store the last-known position in _start_position."""
        if self.playing:
            self.stop_event.set()
            if self.playback_thread and self.playback_thread.is_alive():
                self.playback_thread.join(timeout=30.0)
            self.playing = False
        
            # Now we preserve the current_position
            # self._start_position = self._current_position

    def set_count_in(self, enabled: bool):
        self.count_in = enabled

    # -------------------------------------------------------
    #   TIME-STRETCH
    # -------------------------------------------------------
    def custom_time_stretch(self, audio: np.ndarray, speed: float) -> np.ndarray:
        """Use RubberBand to time-stretch without pitch change."""
        # Add basic check for valid speed, though controller should ensure this
        if speed <= 0:
            print(f"Warning: custom_time_stretch called with invalid speed {speed}. Returning original.")
            return audio
        # Ensure input is float32 for pyrubberband
        audio_float32 = audio.astype(np.float32)
        return pyrb.time_stretch(audio_float32, self.stem_srs, speed)

    # Note: _time_stretch_section is now superseded by _get_or_stretch_stem_snippet
    # We keep it here for now if other parts of the code might use it, but the core
    # playback logic will use the new method. Consider removing if unused later.
    def _time_stretch_section(self, stem_name: str, audio_slice: np.ndarray, speed: float) -> np.ndarray:
        """Cache time-stretch results so we don't recalc multiple times."""
        # This cache key is less robust than the new one.
        slice_key = (stem_name, len(audio_slice), speed)
        if slice_key in self.processed_stems:
            return self.processed_stems[slice_key]

        if audio_slice.ndim == 1:
            stretched = self.custom_time_stretch(audio_slice, speed)
            out = stretched.astype(np.float32)
        else:
            channels = audio_slice.shape[1]
            ch_list = []
            for ch in range(channels):
                single_ch = audio_slice[:, ch]
                st = self.custom_time_stretch(single_ch, speed)
                ch_list.append(st.astype(np.float32))
            out = np.column_stack(ch_list)

        self.processed_stems[slice_key] = out
        return out

    # -------------------------------------------------------
    #   MUTE / UNMUTE
    # -------------------------------------------------------
    def toggle_mute_stem(self, stem_name: str) -> bool:
        """Toggle a stem's muted state. Returns True if now muted, else False."""
        if stem_name not in self.stems:
            return False
        
        if stem_name in self.muted_stems:
            self.muted_stems.remove(stem_name)
            is_muted = False
        else:
            self.muted_stems.add(stem_name)
            is_muted = True
            
        # Notify callback about the change if one is registered
        for client_id, callback in self.mute_status_change_callback.items():
            if callable(callback):
                callback(stem_name, is_muted)
        # if self.mute_status_change_callback:
        #     self.mute_status_change_callback(stem_name, is_muted)
            
        return is_muted

    # -------------------------------------------------------
    #   DURATION
    # -------------------------------------------------------
    def get_total_duration(self) -> float:
        """Return the total length (in sec) of the full track (largest stem)."""
        if not self.stems:
            return 0.0
        return max(len(x) for x in self.stems.values()) / self.stem_srs

    # -------------------------------------------------------
    #   AUDIO PREPARATION
    # -------------------------------------------------------
    def _prepare_audio_section(self, start_sec: float, end_sec: float, speed: float, current_muted_stems: set) -> Optional[tuple[np.ndarray, int]]:
        """
        Prepares the mixed and time-stretched audio data for a given section.

        Args:
            start_sec: The start time of the section in seconds.
            end_sec: The end time of the section in seconds.
            speed: The playback speed factor.
            current_muted_stems: A set of stem names to mute for this preparation.

        Returns:
            A tuple containing:
                - A NumPy array with the prepared audio data (mixed_section).
                - An integer representing the number of channels.
            Returns None if the section duration is invalid or no audio data is produced.
        """
        if not self.stems or self.stem_srs == 0:
            print("Warning: Stems not loaded or sample rate is zero.")
            return None

        section_duration = end_sec - start_sec
        if section_duration <= 0:
            # print(f"Warning: Invalid section duration {section_duration} ({start_sec} -> {end_sec}).")
            return None # Invalid duration

        start_sample = int(start_sec * self.stem_srs)
        end_sample = int(end_sec * self.stem_srs)
        orig_len_samples = end_sample - start_sample
        if orig_len_samples <= 0:
            return None # Invalid sample range

        # Use the provided speed argument
        if speed <= 0:
            print(f"Warning: Invalid playback speed {speed}.")
            return None

        new_length = int(section_duration * self.stem_srs / speed)
        if new_length <= 0:
             print(f"Warning: Calculated new length is zero or negative ({new_length}).")
             return None

        channels = 1
        max_stem_len = 0
        for sdata in self.stems.values():
            if len(sdata.shape) > 1:
                channels = max(channels, sdata.shape[1])
            max_stem_len = max(max_stem_len, len(sdata))

        # Ensure sample indices are within the bounds of the actual audio data
        safe_start_sample = max(0, start_sample)
        safe_end_sample = min(max_stem_len, end_sample) # Use max_stem_len for safety across all stems

        if safe_start_sample >= safe_end_sample:
             print(f"Warning: Safe sample range is invalid ({safe_start_sample} >= {safe_end_sample}).")
             return None

        mixed_section = np.zeros((new_length, channels), dtype=np.float32)

        for stem_name, audio_data in self.stems.items():
            if stem_name in current_muted_stems: # Use the provided set
                continue

            # Adjust end sample specifically for this stem's length
            stem_safe_end_sample = min(len(audio_data), safe_end_sample)
            if safe_start_sample >= stem_safe_end_sample:
                continue # Skip if the section is outside this stem's range

            snippet = audio_data[safe_start_sample:stem_safe_end_sample]
            if snippet.size == 0:
                continue

            # Call _time_stretch_section (uses its own cache based on len(snippet))
            stretched = self._time_stretch_section(stem_name, snippet, speed)

            length_to_mix = min(len(mixed_section), len(stretched))
            if length_to_mix <= 0:
                continue

            if stretched.ndim == 1:
                # Ensure stretched is broadcastable if mixed_section has more channels
                stretched_reshaped = stretched[:length_to_mix, np.newaxis] if channels > 1 else stretched[:length_to_mix]
                try:
                    mixed_section[:length_to_mix] += stretched_reshaped
                except ValueError as e:
                     print(f"Error mixing stem {stem_name} (1D): {e}. Shapes: mix={mixed_section[:length_to_mix].shape}, stretch={stretched_reshaped.shape}")

            else:
                out_ch = min(channels, stretched.shape[1])
                try:
                    mixed_section[:length_to_mix, :out_ch] += stretched[:length_to_mix, :out_ch]
                except ValueError as e:
                    print(f"Error mixing stem {stem_name} (ND): {e}. Shapes: mix={mixed_section[:length_to_mix, :out_ch].shape}, stretch={stretched[:length_to_mix, :out_ch].shape}")


        return mixed_section, channels

    # -------------------------------------------------------
    #   AUDIO PREPARATION (New Methods)
    # -------------------------------------------------------
    def _get_or_stretch_stem_snippet(self, stem_name: str, start_sec: float, end_sec: float, speed: float) -> Optional[np.ndarray]:
        """
        Gets a time-stretched snippet of a single stem, using a cache.
        Assumes valid inputs (start_sec < end_sec, speed > 0).
        Uses a cache key: (stem_name, rounded_start, rounded_end, rounded_speed).
        """
        start_sec_r = round(start_sec, 6)
        end_sec_r = round(end_sec, 6)
        speed_r = round(speed, 6)
        cache_key = (stem_name, start_sec_r, end_sec_r, speed_r)

        print("get stem: " + str(cache_key))

        cached_result = self.processed_stems.get(cache_key)
        if cached_result is not None:
            return cached_result

        # --- Not cached, calculate ---
        audio_data = self.stems.get(stem_name)
        if audio_data is None: # Should not happen if controller is correct
             print(f"Warning: Stem '{stem_name}' not found during snippet preparation.")
             return None

        start_sample = int(start_sec * self.stem_srs)
        end_sample = int(end_sec * self.stem_srs)

        # Basic bounds check for safety, even if controller should prevent invalid ranges
        safe_start_sample = max(0, start_sample)
        safe_end_sample = min(len(audio_data), end_sample)

        if safe_start_sample >= safe_end_sample:
            # Valid scenario if section is outside this stem's range
            return None # Return None for empty snippet

        snippet = audio_data[safe_start_sample:safe_end_sample]

        if snippet.size == 0:
            return None # Return None for empty snippet

        # Perform time stretching
        stretched_snippet = self.custom_time_stretch(snippet, speed)

        # Store in cache
        self.processed_stems[cache_key] = stretched_snippet
        return stretched_snippet

    def _prepare_mixed_audio(self, start_sec: float, end_sec: float, speed: float, current_muted_stems: set) -> tuple[np.ndarray, int]:
        """
        Prepares a fully mixed section using cached/stretched stem snippets.
        Assumes valid inputs (start_sec < end_sec, speed > 0).
        """
        # 1. Determine max channels
        channels = 1
        if self.stems:
            for sdata in self.stems.values():
                if sdata.ndim > 1:
                    channels = max(channels, sdata.shape[1])
        else:
            # No stems loaded, return empty array immediately
            return np.zeros((0, channels), dtype=np.float32), channels

        # 2. Calculate duration and output length (Assume valid inputs)
        section_duration = end_sec - start_sec
        # Add a small epsilon to prevent zero length due to float precision near loop points?
        # Or rely on controller to ensure start_sec is strictly less than end_sec.
        new_length = int(section_duration * self.stem_srs / speed)

        # If calculated length is zero (e.g., very short section, high speed), return empty
        if new_length <= 0:
             return np.zeros((0, channels), dtype=np.float32), channels

        # 3. Initialize mixed_section
        mixed_section = np.zeros((new_length, channels), dtype=np.float32)

        # 4. Loop through stems, get/stretch snippets, and mix
        for stem_name in self.stems.keys():
            if stem_name in current_muted_stems:
                continue

            # Get stretched snippet (using cache)
            stretched_snippet = self._get_or_stretch_stem_snippet(stem_name, start_sec, end_sec, speed)

            if stretched_snippet is not None and stretched_snippet.size > 0:
                # Mix into the main buffer
                length_to_mix = min(len(mixed_section), len(stretched_snippet))
                if length_to_mix <= 0: continue # Skip if nothing to mix

                if stretched_snippet.ndim == 1:
                    # Add mono snippet to all channels
                    mixed_section[:length_to_mix] += stretched_snippet[:length_to_mix, np.newaxis]
                else:
                    # Mix channel by channel up to the number of channels in mixed_section
                    snippet_channels = stretched_snippet.shape[1]
                    ch_to_mix = min(channels, snippet_channels)
                    mixed_section[:length_to_mix, :ch_to_mix] += stretched_snippet[:length_to_mix, :ch_to_mix]

        return mixed_section, channels

    # -------------------------------------------------------
    #   INTERNAL PLAYBACK WORKER
    # -------------------------------------------------------
    def _playback_worker(self):
        """
        Streams audio for the selected section, handling loops and mute changes.
        Uses cached time-stretched snippets and re-mixes on the fly if mutes change.
        Assumes valid start/end times and speed are set by the controller.
        """
        # Initial setup based on current state when play was pressed
        current_start = self._start_position
        current_end = self._end_position
        current_speed = self.playback_speed
        frames_consumed = 0
        playback_finished = False
        
        # Determine initial channel count (can be refined if needed)
        initial_channels = 1
        if self.stems:
            for sdata in self.stems.values():
                if sdata.ndim > 1:
                    initial_channels = max(initial_channels, sdata.shape[1])

        channels = initial_channels
        mixed_section = np.zeros((0, initial_channels), dtype=np.float32)        
        current_mix_buffer = [ mixed_section ]
        should_recompute = [True]
 
        def recalculate():
            nonlocal frames_consumed, channels, playback_finished, current_start, current_end, current_speed

            time_changed = \
                self._start_position != current_start or \
                self._end_position != current_end

            if  self.playback_speed != current_speed or time_changed:
                should_recompute[0] = True
                if time_changed:
                    self.clear_stem_cache()

            if should_recompute[0]:
                should_recompute[0] = False

                current_speed = self.playback_speed
                current_start = self._start_position
                current_end   = self._end_position

                new_audio_data, channels = self._prepare_mixed_audio(
                    current_start, current_end, current_speed, self.muted_stems
                )

                current_mix_buffer[0] = new_audio_data

                frames_consumed = int( (float(self.stem_srs) * (self._current_position - current_start)) / current_speed )

                # Ensure consumption point is valid for the new buffer
                frames_consumed = min(frames_consumed, len(new_audio_data))

        while not self.stop_event.is_set():
            # --- Handle Count-in ---
            # Check if count-in is needed *at the start of the intended section*
            if self.count_in and self._current_position == self._start_position:
                 self._play_count_in()
                 if self.stop_event.is_set(): break # Stop if count-in was interrupted

            frames_consumed = 0
            playback_finished = False

            def callback(outdata, frames, time_info, status):
                nonlocal frames_consumed, playback_finished
                recalculate()

                # --- Feed audio data ---
                active_buffer = current_mix_buffer[0]
                buffer_len = len(active_buffer)
                playback_finished = frames_consumed >= buffer_len

                if playback_finished:
                    # Buffer exhausted or became empty after recompute
                    outdata[:] = 0 # Fill with silence
                    self._current_position = min(current_end, self._current_position)
                    return

                start_idx = frames_consumed
                frames_to_copy = min(frames, buffer_len - start_idx)
                end_idx = start_idx + frames_to_copy

                try:
                    # Check/adjust for channel mismatch before copying
                    out_channels = outdata.shape[1]
                    buf_channels = active_buffer.shape[1] if active_buffer.ndim > 1 else 1

                    if out_channels == buf_channels:
                        outdata[:frames_to_copy] = active_buffer[start_idx : end_idx]
                    elif out_channels > buf_channels: # Output expects more channels (e.g., mono -> stereo)
                        # Repeat mono buffer across output channels
                        outdata[:frames_to_copy, :] = active_buffer[start_idx : end_idx, np.newaxis]
                    else: # Output expects fewer channels (e.g., stereo -> mono)
                        # Mix down buffer channels or just take the first one? Take first for now.
                        outdata[:frames_to_copy, 0] = active_buffer[start_idx : end_idx, 0]
                        # Zero out remaining output channels if any
                        if out_channels > 1:
                             outdata[:frames_to_copy, 1:] = 0

                    # Zero pad if request exceeds available data
                    if frames_to_copy < frames:
                        outdata[frames_to_copy:] = 0

                    playback_finished = frames_consumed >= buffer_len

                except IndexError as e:
                    outdata[:] = 0 # Output silence on error
                    playback_finished = True

                frames_consumed += frames_to_copy

                # Update global position (clamped to section end)
                # Calculate based on frames consumed from the *original* duration perspective

                # t = (f / srs) * s
                # (srs * t) / s = f 
                played_sec_original_timescale = (frames_consumed / float(self.stem_srs)) * current_speed
                self._current_position = min(current_end, current_start + played_sec_original_timescale)

            def handle_mute_change(stem_name, is_muted):
                # Simply signal the callback to handle the recompute
                should_recompute[0] = True

            # --- Stream Audio ---
            callback_id = self.add_mute_callback(handle_mute_change)
            stream = None # Define stream variable outside try block
            try:
                # Use the channel count determined by the initial preparation
                stream = sd.OutputStream(samplerate=self.stem_srs,
                                         channels=channels,
                                         blocksize=1024, # Or make configurable
                                         dtype=np.float32,
                                         callback=callback)
                stream.start()

                # Wait loop: Check if buffer consumed or stop event
                while not self.stop_event.is_set() and not playback_finished:
                    sd.sleep(10) # Sleep in ms, sounddevice handles efficient waiting

            except Exception as e:
                 print(f"Error during audio stream: {e}")
                 self.stop_event.set() # Ensure loop terminates on stream error
            finally:
                if stream:
                    try:
                        stream.stop()
                        stream.close()
                    except Exception as e:
                        print(f"Error stopping/closing stream: {e}")
                self.remove_mute_callback(callback_id)


            # --- Post-Stream Logic ---
            if self.stop_event.is_set():
                print("Playback stopped.")
                break # Exit outer loop

            if playback_finished and self.loop:
                print("Looping section.")
                # Apply delay
                if self.loop_delay > 0:
                    # Use stop_event.wait for interruptible sleep
                    interrupted = self.stop_event.wait(timeout=self.loop_delay)
                    if interrupted:
                        print("Stopped during loop delay.")
                        break
                if self.stop_event.is_set(): break # Check again just in case

                # Reset for next loop iteration
                current_start = self._start_position
                self._current_position = self._start_position # Reset playback marker
                current_end = self._end_position
                continue 

            elif playback_finished and not self.loop:
                print("Playback finished, no loop.")
                break # Finished and not looping

            else: # Playback interrupted for other reasons (e.g., stream error handled above)
                print("Playback pass ended.")
                break


        # --- End of outer while loop ---
        self.playing = False
        print("Playback worker finished.")


    # -------------------------------------------------------
    #   COUNT-IN
    # -------------------------------------------------------
    def _play_count_in(self):
        """Play 4 quick clicks at BPM, or until user stops."""
        if not self.current_song or not self.current_song.bpm:
            return
        
        bpm = self.current_song.bpm
        beat_interval = 60.0 / bpm
        sr = 44100
        click_dur = 0.05
        t = np.linspace(0, click_dur, int(sr*click_dur), endpoint=False)
        click = 0.5*np.sin(2*np.pi*880*t)
        
        for _ in range(4):
            sd.play(click, sr)
            sd.wait()
            if self.stop_event.is_set():
                return
            remain = beat_interval - click_dur
            if remain > 0:
                time.sleep(remain)