def filter_and_isolate_data(data, threshold:int=500)->list:
    # Step 1: Filter out values above the threshold
    filtered_data = [value if value <= threshold else None for value in data]
    
    # Step 2: Identify contiguous segments
    def identify_segments(filtered_data):
        segments = []
        current_segment = []
        for value in filtered_data:
            if value is not None:
                current_segment.append(value)
            else:
                if current_segment:
                    segments.append(current_segment)
                    current_segment = []
        if current_segment:
            segments.append(current_segment)
        return segments
    
    # Get all contiguous segments of filtered data
    segments = identify_segments(filtered_data)
    
    # Step 3: Determine start and stop of rotations
    def determine_rotation_bounds(segments):
        bounds = []
        for segment in segments:
            if segment:
                bounds.append((data.index(segment[0]), data.index(segment[-1])))
        return bounds
    
    bounds = determine_rotation_bounds(segments)

    # Step 4: Isolate clockwise and counterclockwise data
    def isolate_rotations(data, bounds):
        isolated_data = {"clockwise": [], "counterclockwise": []}
        for start, end in bounds:
            rotation_data = data[start:end+1]
            if len(rotation_data) > 1:
                # Assuming first and last segments are clockwise and counterclockwise respectively
                if start == 0 or (len(isolated_data["clockwise"]) == 0 and len(rotation_data) > 1):
                    isolated_data["clockwise"].append(rotation_data)
                else:
                    isolated_data["counterclockwise"].append(rotation_data)
        return isolated_data

    isolated_data = isolate_rotations(data, bounds)
    
    return isolated_data

# # Example data and usage
# data = [1000, 1000, 1000, 1010, 9997, 1000, 140, 121, 123, 33, 122, 1002, 1008, 1120, 110, 100, 133, 110, 1000, 1000, 1000, 1002]
# threshold = 500

# isolated_data = filter_and_isolate_data(data, threshold)

# print("Clockwise Data:", isolated_data["clockwise"])
# print("Counterclockwise Data:", isolated_data["counterclockwise"])
