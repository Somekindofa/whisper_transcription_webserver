def merge_diarization_with_transcript(diarization, transcription):
    """
    Align diarization speaker segments with word-level transcript output.
    
    Args:
        diarization: Pyannote diarization output with speaker segments [{speaker, start, end}]
        transcription: Whisper output with word-level timestamps
    
    Returns:
        Formatted transcript with speaker labels
    """
    if not diarization or not transcription:
        return transcription.get("text", "")
    
    # Extract segments from pyannote output
    diar_segments = diarization.get("diarization", [])
    if not diar_segments:
        return transcription.get("text", "")
    
    # Extract words from whisper output
    words = []
    for segment in transcription.get("segments", []):
        words.extend(segment.get("words", []))
    
    if not words:
        return transcription.get("text", "")
    
    def find_speaker_for_word(word_start, word_end):
        """Find the best speaker match for a word with multiple fallback strategies."""
        # Strategy 1: Match using word start time (most reliable)
        for seg in diar_segments:
            if seg["start"] <= word_start <= seg["end"]:
                return seg["speaker"]
        
        # Strategy 2: Match using word midpoint
        word_mid = (word_start + word_end) / 2
        for seg in diar_segments:
            if seg["start"] <= word_mid <= seg["end"]:
                return seg["speaker"]
        
        # Strategy 3: Find nearest speaker within tolerance (0.1s gap)
        tolerance = 0.1
        closest_speaker = None
        closest_distance = float('inf')
        
        for seg in diar_segments:
            # Calculate minimum distance from word to segment
            if word_start < seg["start"]:
                distance = seg["start"] - word_start
            elif word_start > seg["end"]:
                distance = word_start - seg["end"]
            else:
                distance = 0
            
            if distance < closest_distance and distance <= tolerance:
                closest_distance = distance
                closest_speaker = seg["speaker"]
        
        if closest_speaker:
            return closest_speaker
        
        # Strategy 4: Find absolute nearest speaker (last resort)
        for seg in diar_segments:
            distance = min(abs(word_start - seg["start"]), abs(word_start - seg["end"]))
            if closest_speaker is None or distance < closest_distance:
                closest_distance = distance
                closest_speaker = seg["speaker"]
        
        return closest_speaker
    
    # Match each word to a speaker based on timestamp overlap
    result_lines = []
    current_speaker = None
    current_line = []
    
    for word in words:
        word_start = word["start"]
        word_end = word["end"]
        
        speaker = find_speaker_for_word(word_start, word_end)
        
        # If speaker changed or no speaker found, start new line
        if speaker != current_speaker:
            if current_line:
                speaker_label = f"[{current_speaker}]" if current_speaker else "[Unknown]"
                result_lines.append(f"{speaker_label}: {' '.join(current_line)}")
                current_line = []
            current_speaker = speaker
        
        current_line.append(word["word"].strip())
    
    # Add final line
    if current_line:
        speaker_label = f"[{current_speaker}]" if current_speaker else "[Unknown]"
        result_lines.append(f"{speaker_label}: {' '.join(current_line)}")
    
    return "\n".join(result_lines)
