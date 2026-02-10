class RockTimingEvents {
    timing_patterns = [
        [[["back-slide-interval", 1, 3],
          ["t-slide-interval", 1, 2],          
          ["hog-hog-interval", 0, 1],
          ["near-hog-speed", 1, null],
          ["far-hog-speed", 0, null],
          ["X", null]],
          [["h2", 0], ["h1", 22], ["t1", 5], ["b1", 3]]],  // b1 t1 h1 h2
         
        [[["back-slide-interval", 1, 3],
          ["t-slide-interval", 1, 2],          
          ["hog-hog-interval", 0, 1],
          ["near-hog-speed", 1, null],
          ["far-hog-speed", 0, null],
          ["X", null, null]],
         [["h1", 0], ["h2", 22], ["t2", 5], ["b2", 3]]],  // b2 t2 h2 h1
         
        [[["back-slide-interval", 0, 2],
          ["t-slide-interval", 0, 1],          
          ["near-hog-speed", 0, null],
          ["X", null, null]],
         [["h1", 22], ["t1", 5], ["b1", 3]]],             // b1 t1 h1
         
        [[["back-slide-interval", 0, 2],
          ["t-slide-interval", 0, 1],
          ["near-hog-speed", 0, null],
          ["X", null, null]],
         [["h2", 22], ["t2", 5], ["b2", 3]]],             // b2 t2 h2
        
        [[["t-slide-interval", 1, 2],
          ["hog-hog-interval", 0, 1],
          ["near-hog-speed", 1, null],
          ["far-hog-speed", 0, null],
          ["X", null, null]],
         [["h2", 0], ["h1", 22], ["t1", 5]]],             // t1 h1 h2
        
        [[["t-slide-interval", 1, 2],
          ["hog-hog-interval", 0, 1],
          ["near-hog-speed", 1, null],
          ["far-hog-speed", 0, null],
          ["X", null, null]],
         [["h1", 0], ["h2", 22], ["t2", 5]]],             // t2 h2 h1
        
        [[["back-slide-interval", 1, 2],
          ["hog-hog-interval", 0, 1],
          ["near-hog-speed", 1, null],
          ["far-hog-speed", 0, null],
          ["X", null, null]],
         [["h2", 0], ["h1", 22], ["b1", 5]]],             // b1 h1 h2
        
        [[["back-slide-interval", 1, 2],
          ["hog-hog-interval", 0, 1],
          ["near-hog-speed", 1, null],
          ["far-hog-speed", 0, null],
          ["X", null, null]],
         [["h1", 0], ["h2", 22], ["b2", 5]]],             // b2 h2 h1
        
        [[["t-slide-interval", 0, 1],
          ["near-hog-speed", 0, null]],
         [["h1", 0], ["t1",  5]]],                        // t1 h1
        
        [[["t-slide-interval", 0, 1],
          ["near-hog-speed", 0, null]],
         [["h2", 0], ["t2",  5]]],                        // t2 h2
        
        [[["back-slide-interval", 0, 1],
          ["near-hog-speed", 0, null]],
         [["h1", 0], ["b1",  5]]],                        // b1 h1
        
        [[["back-slide-interval", 0, 1],
          ["near-hog-speed", 0, null]],
         [["h2", 0], ["b2",  5]]],                        // b2 h2
        ]
        
    timing_patterns_1 = [
        [[["sensor-speed", 0, null],
          ["X", null, null]],
         [["h2", 0], ]],                                  // h2
        
        [[["sensor-speed", 0, null],
          ["X", null, null]],
         [["h1", 0], ]],                                  // h1
        
        [[["sensor-speed", 0, null],
          ["X", null, null]],
         [["t2", 0], ]],                                  // t2
        
        [[["sensor-speed", 0, null],
          ["X", null, null]],
         [["t1", 0], ]],                                  // t1
        
        [[["sensor-speed", 0, null],
          ["X", null, null]],          
         [["b2", 0], ]],                                  // b2
        
        [[["sensor-speed", 0, null],
          ["X", null, null]],
         [["b1", 0], ]],                                  // b1
    ];

    sensor_names = {
        "b1": "Near Back-Line", 
        "t1": "Near T-Line",
        "h1": "Near Hog-Line", 
        "h2": "Far Hog-Line",
        "t2": "Far T-Line",
        "b2": "Far Back-Line" };
    
    constructor(sensorToPlacementMap, placementToColourMap, circumferenceInM) {
        this.times = [];
        this.sensorToPlacementMap = sensorToPlacementMap;
        this.placementToColourMap = placementToColourMap;
        if (sensorToPlacementMap.size == 1) {
            this.timePatterns = this.timing_patterns_1;
        } else {
            this.timePatterns = this.timing_patterns;
        }

        this.first_time = 0;
        this.throws = new Map();
        this.diameter = circumferenceInM / Math.PI;
    }

    clear() {
        this.first_time = 0;
        this.times = []
        this.throws = new Map()
    }

    checkTimePattern(timePattern, times) {
        let patternEntry = timePattern[0];
        let timesEntry = times[0];
        
        if (patternEntry[0] != timesEntry[0]) {
            return null;
        }
        
        let matches = [[patternEntry[0], 0, timesEntry[1], timesEntry[3]]];
        
        let maxPatternIndex = timePattern.length;
        if (maxPatternIndex == 1) {
            return matches;
        }
        
        let checkIndex = 1;
        let maxCheckIndex = times.length;
        let patternIndex = 1;
        // console.log('timePattern', timePattern);

        while (patternIndex < maxPatternIndex && checkIndex < maxCheckIndex) {
            let checkPattern = timePattern[patternIndex];
            while (checkIndex < maxCheckIndex) {
                // console.log(`patternIndex=${patternIndex} checkIndex=${checkIndex}`);
                // console.log(`diff=${matches[matches.length-1][2] - times[checkIndex][1]} checkPattern=${checkPattern} times[checkIndex]=${times[checkIndex]}`);
                
                let checkTime = times[checkIndex];
        
                if (checkPattern[0] != checkTime[0]) {
                    // console.log(`!checkPattern[0]=${checkPattern[0]} checkTime[0]=${checkTime[0]}`);
                    checkIndex += 1;
                    continue;
                }

                let t = checkTime[1]

                let diff = matches[matches.length - 1][2] - t
                
                if (diff > 0 && diff < checkPattern[1]) {
                    matches.push([checkPattern[0], checkIndex, t, checkTime[3]])
                    // console.log(matches);
                    if (matches.length == maxPatternIndex) {
                        return matches;
                    }

                    break;
                }

                checkIndex += 1;
            }
                
            patternIndex += 1;
        }
        
        return null;
    }

    checkForEvent(tm) {
        let tdiff = tm[0] - this.first_time;
        
        if (tdiff > 20) {
            this.times = [];
            this.first_time = tm[0];
        }
        
        this.times.unshift([this.sensorToPlacementMap.get(tm[3], tm[3]), tm[0], tm[1], tm[2]]);
        let timePatternMatch = null;

        let timeSelector = null;
        for (let ix = 0; ix < this.times.length; ix++) {
            let placement = this.times[ix][0]
            for(let ts of this.timePatterns) {
                let timeSelector = ts[0];
                let timePattern = ts[1];
                if (timePattern[0][0] != placement) {
                    continue;
                }
                
                timePatternMatch = this.checkTimePattern(timePattern, this.times, ix, 0);
                if (!timePatternMatch) {
                    continue;
                }

                let throwTimes = [];

                for (const selector of timeSelector) {
                    const [event_type, end_idx, start_idx] = selector;
                    
                    if (event_type == "near-hog-speed") {
                        throwTimes.push([timePatternMatch[end_idx][3],
                                         "orange",
                                         "Near Hog-Line",
                                         this.diameter / timePatternMatch[end_idx][3]]);
                    } else if (event_type == "far-hog-speed") {
                        throwTimes.push([timePatternMatch[end_idx][3],
                                         "green",
                                         "Far Hog-Line",
                                         this.diameter / timePatternMatch[end_idx][3]]);
                    } else if (event_type == "sensor-speed") {
                        throwTimes.push([timePatternMatch[end_idx][3],
                                         "blue",
                                         this.sensor_names[timePatternMatch[end_idx][0]],
                                         this.diameter / timePatternMatch[end_idx][3]]);
                    } else if(event_type == "t-slide-interval") {
                        let td = timePatternMatch[end_idx][2] - timePatternMatch[start_idx][2];
                        throwTimes.push([td,
                                         "yellow",
                                         "Slide - T",
                                         6.4008 / td]);
                    } else if(event_type == "back-slide-interval") {
                        let td = timePatternMatch[end_idx][2] - timePatternMatch[start_idx][2];
                        throwTimes.push([td,
                                         "white",
                                         "Slide - Back",
                                         8.2996 / td]);
                    } if (event_type == "hog-hog-interval") {
                        let td = timePatternMatch[end_idx][2] - timePatternMatch[start_idx][2];
                        throwTimes.push([td,
                                         "red",
                                         "Hog-To-Hog",
                                         21.945 / td]);
                    } else if (selector == "X") {
                        this.clear();
                    }
                }

                let throwKey = timePatternMatch[timePatternMatch.length - 1][2];
                this.throws.set(throwKey, throwTimes);
                return [throwKey, throwTimes];
            }
            
            return null;
        }
    }
}

