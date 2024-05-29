class RockTimingEvents {
    constructor(sensorToPlacementMap, placementToColourMap, mode, circumference, slidePathLength) {
        this.times = [];
        this.sensorToPlacementMap = sensorToPlacementMap;
        this.placementToColourMap = placementToColourMap;
        this.mode = mode;
        // time patterns are in reverse order.
        // pattern tuple is (placement, maximum time difference from previous placment)
        // "b" is break time of second match.
        // "B" is break time of third match
        // "d" is time difference between 1 & 2
        // "D" is time difference between 2 & 3
        // "X" is reset queue of incoming times
        if (mode == "half") {
            this.timePatterns = [["dbX", [["s1", 0], ["s1", 4]]]];
        } else if (mode == "h2h") {
            this.timePatterns = [["dbBX", [["h1", 0], ["h2", 30]]],
                                 ["dbBX", [["h2", 0], ["h1", 30]]]];
        } else if (mode == "full") {
            this.timePatterns = [["dDbBX", [["h2", 0], ["h1", 30], ["s1", 4]]],
                                 ["dDbBX", [["h1", 0], ["h2", 30], ["s2", 4]]],
                                 ["db", [["h1", 0], ["s1", 4]]],
                                 ["db", [["h2", 0], ["s2", 4]]]];
        } else {
            this.timePatterns = null;
        }

        this.throws = new Map();
        // diameter from circumference
        this.diameter = circumference / Math.PI;
        // this.slidePathLength = 6.401;
        // this.slidePathLength = 8.2296;
        this.slidePathLength = slidePathLength;
        // console.log(this.timePatterns);
    }

    clear() {
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
        if (this.timePatterns == null) {
            let throwKey = tm[0]
            let throwTimes = [[tm[2], "white", "raw", this.diameter / tm[2]]]
            this.throws.set(throwKey, throwTimes);
            return [throwKey, throwTimes];
        }
        
        this.times.unshift([this.sensorToPlacementMap.get(tm[3], tm[3]), tm[0], tm[1], tm[2]]);
        let timePatternMatch = null;

        let timeSelector = null;
        for (let ix = 0; ix < this.times.length; ix++) {
            placement = this.times[ix][0]
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

                for (let selector of timeSelector) {
                    if (selector == "b") {
                        throwTimes.push([timePatternMatch[1][3],
                                         this.placementToColourMap.get(timePatternMatch[1][0]), "Near Hog-Line", this.diameter / timePatternMatch[1][3]]);
                    } else if (selector == "B") {
                        throwTimes.push([timePatternMatch[2][3],
                                         this.placementToColourMap.get(timePatternMatch[2][0]), "Far Hog-Line", this.diameter / timePatternMatch[2][3]]);
                    } else if (selector == "d") {
                        let td = timePatternMatch[timePatternMatch.length - 2][2] - timePatternMatch[timePatternMatch.length - 1][2];
                        throwTimes.push([td,
                                         this.placementToColourMap.get(timePatternMatch[0][0]), "Slide", this.slidePathLength / td]);
                    } else if (selector == "D") {
                        let td = timePatternMatch[0][2] - timePatternMatch[1][2];
                        throwTimes.push([td,
                                         this.placementToColourMap.get(timePatternMatch[1][0]), "Hog-To-Hog", 21.945 / td]);
                    } else if (selector == "X") {
                        this.times = [];
                    }
                }

                let throwKey = timePatternMatch[0][2];
                this.throws.set(throwKey, throwTimes);
                return [throwKey, throwTimes];
            }
            
            return null;
        }
    }
}

