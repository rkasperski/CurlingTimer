import sys
import csv
import math
from collections import deque, OrderedDict


class RockTimingEvents:
    # time patterns are in reverse order.

    timing_patterns = [
        ((("back-slide-interval", 1, 3),
          ("t-slide-interval", 1, 2),          
          ("hog-hog-interval", 0, 1),
          ("near-hog-speed", 1, None),
          ("far-hog-speed", 0, None),
          ("X", None)),
          (("h2", 0), ("h1", 22), ("t1", 5), ("b1", 3))),  # b1 t1 h1 h2
         
        ((("back-slide-interval", 1, 3),
          ("t-slide-interval", 1, 2),          
          ("hog-hog-interval", 0, 1),
          ("near-hog-speed", 1, None),
          ("far-hog-speed", 0, None),
          ("X", None, None)),
         (("h1", 0), ("h2", 22), ("t2", 5), ("b2", 3))),  # b2 t2 h2 h1
         
        ((("back-slide-interval", 0, 2),
          ("t-slide-interval", 0, 1),          
          ("near-hog-speed", 0, None),
          ("X", None, None)),
         (("h1", 22), ("t1", 5), ("b1", 3))),             # b1 t1 h1
         
        ((("back-slide-interval", 0, 2),
          ("t-slide-interval", 0, 1),
          ("near-hog-speed", 0, None),
          ("X", None, None)),
         (("h2", 22), ("t2", 5), ("b2", 3))),             # b2 t2 h2
        
        ((("t-slide-interval", 1, 2),
          ("hog-hog-interval", 0, 1),
          ("near-hog-speed", 1, None),
          ("far-hog-speed", 0, None),
          ("X", None, None)),
         (("h2", 0), ("h1", 22), ("t1", 5))),             # t1 h1 h2
        
        ((("t-slide-interval", 1, 2),
          ("hog-hog-interval", 0, 1),
          ("near-hog-speed", 1, None),
          ("far-hog-speed", 0, None),
          ("X", None, None)),
         (("h1", 0), ("h2", 22), ("t2", 5))),             # t2 h2 h1
        
        ((("back-slide-interval", 1, 2),
          ("hog-hog-interval", 0, 1),
          ("near-hog-speed", 1, None),
          ("far-hog-speed", 0, None),
          ("X", None, None)),
         (("h2", 0), ("h1", 22), ("b1", 5))),             # b1 h1 h2
        
        ((("back-slide-interval", 1, 2),
          ("hog-hog-interval", 0, 1),
          ("near-hog-speed", 1, None),
          ("far-hog-speed", 0, None),
          ("X", None, None)),
         (("h1", 0), ("h2", 22), ("b2", 5))),             # b2 h2 h1
        
        ((("t-slide-interval", 0, 1),
          ("near-hog-speed", 0, None)),
         (("h1", 0), ("t1",  5))),                        # t1 h1
        
        ((("t-slide-interval", 0, 1),
          ("near-hog-speed", 0, None)),
         (("h2", 0), ("t2",  5))),                        # t2 h2
        
        ((("back-slide-interval", 0, 1),
          ("near-hog-speed", 0, None)),
         (("h1", 0), ("b1",  5))),                        # b1 h1
        
        ((("back-slide-interval", 0, 1),
          ("near-hog-speed", 0, None)),
         (("h2", 0), ("b2",  5))),                        # b2 h2
        ]
        
    timing_patterns_1 = [
        ((("sensor-speed", 0, None), 
          ("X", None, None)),
         (("h2", 0), )),                                  # h2
        
        ((("sensor-speed", 0, None), 
          ("X", None, None)),
         (("h1", 0), )),                                  # h1
        
        ((("sensor-speed", 0, None), 
          ("X", None, None)),
         (("t2", 0), )),                                  # t2
        
        ((("sensor-speed", 0, None), 
          ("X", None, None)),
         (("t1", 0), )),                                  # t1
        
        ((("sensor-speed", 0, None),
          ("X", None, None)),
         (("b2", 0), )),                                  # b2
        
        ((("sensor-speed", 0, None),
          ("X", None, None)),
         (("b1", 0), )),                                  # b1
    ]
    
    def __init__(self, sensor_to_placement_map, placement_to_colour_map, circumferenceInM=0.910):
        self.times = deque(maxlen=10)
        self.sensor_to_placement_map = sensor_to_placement_map
        self.placement_to_colour_map = placement_to_colour_map

        self.throws = OrderedDict()
        #diameter from circumference
        self.diameter = circumferenceInM / math.pi
        self.first_time = 0
        if len(sensor_to_placement_map) == 1:
            self.patterns_to_match = self.timing_patterns_1
        else:
            self.patterns_to_match = self.timing_patterns
            
    def clear(self):
        self.first_time = 0
        self.times.clear()
        self.throws.clear()

    def check_time_pattern(self, time_pattern, times):
        pattern_entry = time_pattern[0]
        times_entry = times[0]

        if pattern_entry[0] != times_entry[0]:
            return None
        
        matches = [(pattern_entry[0], 0, times_entry[1], times_entry[3])]
        
        max_pattern_index = len(time_pattern)
        if max_pattern_index == 1:
            return matches

        check_index = 1
        max_check_index = len(times)
        pattern_index = 1
        while pattern_index < max_pattern_index and check_index < max_check_index:
            checkPattern = time_pattern[pattern_index]
            while check_index < max_check_index:
                check_time = times[check_index]
        
                if checkPattern[0] != check_time[0]:
                    check_index += 1
                    continue

                t = check_time[1]

                diff = matches[-1][2] - t
                if diff > 0 and diff < checkPattern[1]:
                    matches.append((checkPattern[0], check_index, t, check_time[3]))
                    if len(matches) == max_pattern_index:
                        return matches

                    break;

                check_index += 1
                
            pattern_index += 1
        
        return None

    def check_for_event(self, tm, verbose=False):
        tdiff = tm[0] - self.first_time
        if tdiff > 20:
            if verbose:
                print("--- clear ---")
                
            self.times.clear()
            self.first_time = tm[0]

        if verbose:
            print(f"{tm=}")
            
        self.times.appendleft((self.sensor_to_placement_map.get(tm[3], tm[3]), tm[0], tm[1], tm[2]))

        placement = self.times[0][0]
        for ts in self.patterns_to_match:
            actions, time_pattern = ts
            if time_pattern[0][0] != placement:
                continue
                
            time_pattern_match = self.check_time_pattern(time_pattern, self.times)
            if not time_pattern_match:
                continue

            throw_times = []

            for event_type, end_idx, start_idx in actions:
                if event_type == "near-hog-speed":
                    # report breaktime at first hog-line
                    throw_times.append((time_pattern_match[end_idx][3],
                                        "orange",
                                        "Near Hog-Line",
                                        self.diameter / time_pattern_match[end_idx][3]))
                elif event_type == "sensor-speed":
                    throw_times.append((time_pattern_match[end_idx][3],
                                        "blue",
                                        time_pattern_match[end_idx][0],
                                        self.diameter / time_pattern_match[end_idx][3]))
                elif event_type == "far-hog-speed":
                    # report breaktime at second hog-line
                    throw_times.append((time_pattern_match[0][3],
                                        "green",
                                        "Far Hog-Line",
                                        self.diameter / time_pattern_match[end_idx][3]))
                elif event_type == "t-slide-interval":
                    # report difference between two timers as a slide interval
                    td = time_pattern_match[end_idx][2] - time_pattern_match[start_idx][2]
                    throw_times.append((td,
                                        "yellow",
                                        "Slide - T",
                                        6.4008 / td))
                elif event_type == "back-slide-interval":
                    # report difference between two timers as a slide interval
                    td = time_pattern_match[end_idx][2] - time_pattern_match[start_idx][2]
                    throw_times.append((td,
                                        "white",
                                        "Slide - Back",
                                        8.2296 / td))
                elif event_type == "hog-hog-interval":
                    # report difference between last two timers - they are in reverse order
                    td = time_pattern_match[end_idx][2] - time_pattern_match[start_idx][2]
                    throw_times.append((td,
                                        "red", 
                                        "Hog-To-Hog",
                                        21.945 / td))
                elif event_type == "X":
                    self.times.clear()
                    
            throw_key = time_pattern_match[-1][2]
            self.throws[throw_key] = throw_times
            return (throw_key, throw_times)

        return None

def test():
    colours = ["white", "yellow", "red", "green", "blue", "orange"]
    rock_positions = {
        "T-Line 1": "t1",
        "T-Line 2": "t2",
        "Hog-Line 1": "h1",
        "Hog-Line 2": "h2",
        "Back-Line 1": "b1",
        "Back-Line 2": "b2",
        }

    times = []

    sensor_to_placement_map = {}
    placement_to_colour_map = {}
    rows = []

    with open(sys.argv[1], newline='') as csvfile:
        times_rdr = csv.reader(csvfile)
        first_line = True
        for row in times_rdr:
            if first_line:
                first_line = False
                if row[0] == "Sensor":
                    continue

            sensor = row[0]

            if sensor not in sensor_to_placement_map:
                placement = rock_positions[sensor]
                placement_to_colour_map[placement] = colours.pop(0)
                sensor_to_placement_map[sensor] = placement

            t = [float(row[4]), float(row[5]), float(row[5]) - float(row[4]), sensor]
            rows.append(t)

    print(f"{sensor_to_placement_map=}")
    print(f"{placement_to_colour_map=}")

    rte = RockTimingEvents(sensor_to_placement_map, placement_to_colour_map)
    for tm in reversed(rows):
        ev = rte.check_for_event(tm, verbose=True)
        if ev:
            print()
            print(f"key={ev[0]}")
            for t, c, event, speed in ev[1]:
                print(f"\t{t} - {c} - {event} - {speed}")
            print()
        
    print()
    print("==================================")
    for throw_key, throw in rte.throws.items():
        print()
        print(f"key={throw_key}")
        for t, c, event, speed in throw:
            print(f"\t{t} - {c} - {event} - {speed}")

if __name__ == "__main__":
    test()
