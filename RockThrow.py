import sys
import csv
import math
from collections import deque, OrderedDict


class RockTimingEvents:
    def __init__(self, sensorToPlacementMap, placementToColourMap, mode="full", circumference=0.910, slidePathLength=6.401):
        self.times = deque(maxlen=10)
        self.sensorToPlacementMap = sensorToPlacementMap
        self.placementToColourMap = placementToColourMap
        self.mode = mode
        # time patterns are in reverse order.
        # pattern tuple is (placement, maximum time difference from previous placment)
        # "b" is break time of second match.
        # "B" is break time of third match
        # "d" is time difference between 1 & 2
        # "D" is time difference between 2 & 3
        # "X" is reset queue of incoming times
        if mode == "half":
            self.timePatterns = [("dbX", (("s1", 0), ("s1", 4)))]
        elif mode == "h2h":
            self.timePatterns = [("dbBX", (("h1", 0), ("h2", 30))),
                                 ("dbBX", (("h2", 0), ("h1", 30)))]
        elif mode == "full":
            self.timePatterns = [("dDbBX", (("h2", 0), ("h1", 30), ("s1", 4))),
                                 ("dDbBX", (("h1", 0), ("h2", 30), ("s2", 4))),
                                 ("db", (("h1", 0), ("s1", 4))),
                                 ("db", (("h2", 0), ("s2", 4)))]
        else:
            self.timePatterns = None

        self.throws = OrderedDict()
        #diameter from circumference
        self.diameter = circumference / math.pi
        #self.slidePathLength = 6.401
        #self.slidePathLength = 8.2296
        self.slidePathLength = slidePathLength

    def clear(self):
        self.times.clear()
        self.throws.clear()

    def checkTimePattern(self, timePattern, times):
        patternEntry = timePattern[0]
        timesEntry = times[0]

        if patternEntry[0] != timesEntry[0]:
            return None
        
        matches = [(patternEntry[0], 0, timesEntry[1], timesEntry[3])]
        
        maxPatternIndex = len(timePattern)
        if maxPatternIndex == 1:
            return matches

        checkIndex = 1
        maxCheckIndex = len(times)
        patternIndex = 1
        # print(f"{timePattern=}")
        while patternIndex < maxPatternIndex and checkIndex < maxCheckIndex:
            checkPattern = timePattern[patternIndex]
            while checkIndex < maxCheckIndex:
                # print(f"{patternIndex=} {checkIndex=} diff={matches[-1][2] - times[checkIndex][1]} {timePattern[patternIndex]=} {times[checkIndex]=}")
                checkTime = times[checkIndex]
        
                if checkPattern[0] != checkTime[0]:
                    # print(f"!{checkPattern[0]=} {checkTime[0]=}")
                    checkIndex += 1
                    continue

                t = checkTime[1]

                diff = matches[-1][2] - t
                # print(f"{diff=} {checkPattern[1]=}")
                if diff > 0 and diff < checkPattern[1]:
                    matches.append((checkPattern[0], checkIndex, t, checkTime[3]))
                    # print(matches)
                    if len(matches) == maxPatternIndex:
                        return matches

                    break;

                checkIndex += 1
                
            patternIndex += 1
        
        return None

    def checkForEvent(self, tm):
        self.times.appendleft((self.sensorToPlacementMap.get(tm[3], tm[3]), tm[0], tm[1], tm[2]))
        if self.timePatterns is None:
            return [tm[0], [[tm[2], "white", "raw", self.diameter / tm[2]]]]
        
        timePatternMatch = None

        timeSelector = None
        placement = self.times[0][0]
        for ts in self.timePatterns:
            timeSelector, timePattern = ts
            if timePattern[0][0] != placement:
                continue
                
            timePatternMatch = self.checkTimePattern(timePattern, self.times)
            if not timePatternMatch:
                continue

            throwTimes = []

            for selector in timeSelector:
                if selector == "b":
                    # report breaktime at first hog-line
                    throwTimes.append((timePatternMatch[-1][3],
                                       self.placementToColourMap[timePatternMatch[-1][0]],
                                       "Near Hog-Line Speed",
                                       self.diameter / timePatternMatch[-1][3]))
                elif selector == "B":
                    # report breaktime at second hog-line
                    throwTimes.append((timePatternMatch[0][3],
                                       self.placementToColourMap[timePatternMatch[0][0]],
                                       "Far Hog-Line Speed",
                                       self.diameter / timePatternMatch[0][3]))
                elif selector == "d":
                    # report difference between first two timers - they are in reverse order
                    td = timePatternMatch[-2][2] - timePatternMatch[-1][2]
                    throwTimes.append((td,
                                       self.placementToColourMap[timePatternMatch[0][0]],
                                       "Slide Interval",
                                       self.slidePathLength / td))
                elif selector == "D":
                    # report difference between last two timers - they are in reverse order
                    td = timePatternMatch[0][2] - timePatternMatch[1][2]
                    throwTimes.append((td,
                                       self.placementToColourMap[timePatternMatch[1][0]],
                                       "Hog-To-Hog Interval",
                                       21.945 / td))
                elif selector == "X":
                    self.times.clear()

            throwKey = timePatternMatch[-1][2]
            self.throws[throwKey] = throwTimes
            return (throwKey, throwTimes)

        return None

def test():
    colours = ["white", "yellow", "red", "green", "blue", "orange"]

    times = []

    sensorToPlacementMap = {}
    placementToColourMap = {}
    rows = []

    with open(sys.argv[1], newline='') as csvfile:
        timesRdr = csv.reader(csvfile)
        firstLine = True
        for row in timesRdr:
            if firstLine:
                firstLine = False
                continue

            sensor = row[0]
            if sensor[0] == 'T':
                placement = "s" + sensor[-1]
            else:
                placement = "h" + sensor[-1]

            if sensor not in sensorToPlacementMap:
                placementToColourMap[placement] = colours.pop(0)
                sensorToPlacementMap[sensor] = placement

            t = [float(row[4]), float(row[5]), float(row[5]) - float(row[4]), sensor]
            rows.append(t)

    print(f"{sensorToPlacementMap=}")
    print(f"{placementToColourMap=}")

    rte = RockTimingEvents(sensorToPlacementMap, placementToColourMap, mode="full")
    for tm in reversed(rows):
        print()
        print("-")
        print(f"{tm=}")

        ev = rte.checkForEvent(tm)
        if ev:
            for t, c, event, speed in ev[1]:
                print(t, c, event, speed)

    print()
    print("==================================")
    for throwKey, throw in rte.throws.items():
        print(throwKey)
        for t, c, event, speed in throw:
            print(f"\t{t} {c} {event} {speed}")

if __name__ == "__main__":
    test()
