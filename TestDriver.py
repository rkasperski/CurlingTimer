import functools, CurlingClockTimers
import sys
import asyncio

fakeTimers = None
fakeDefaults = None
fakeSheet = None

class PlaceHolder():
    pass

def createFakeTimers():
    global fakeTimers, fakeDefaults, fakeSheetData

    fakeSheetData = PlaceHolder()
    fakeSheetData.topColour = "yellow"
    fakeSheetData.bottomColour = "blue"

    fakeDefaults = PlaceHolder()

    fakeDefaults.gameTime = "1:40:00"

    fakeDefaults.finishedMessage = "Done"
    fakeDefaults.finishedMessageColour = "red"
    fakeDefaults.finishedMessageDisplayTime = "15:00"

    fakeDefaults.lastEndMessage = "Last End"
    fakeDefaults.lastEndMessageColour = "green"

    fakeTimers = CurlingClockTimers.Timers(fakeDefaults, fakeSheetData,lambda : False)
    fakeTimers.competition.teams[0].name = "O'Connor"
    fakeTimers.competition.teams[1].name = "Ratakowski"

async def spin(fn):
    while True:
        r = await fn()
        await asyncio.sleep(r if r else 0.1)

async def testScrolling():
    await display.displayScrollingText( "hello again. does this scroll", colour="white")

async def testClock():
    async def clockUpdate():
        display.clockUpdate()

    await spin(clockUpdate)

async def test2Line():
    await spin(functools.partial(display.twoLineText, "line p" , "line y", centre=True))

async def test2Scrolling():
    await spin(functools.partial(display.twoLineText, "line1 - is too lone" , "line2"))

async def testBreakTimes():
    await spin(functools.partial(display.breakTimeDisplay))

async def testBreakTimes1():
    print("textBreaktimes")
    display.breakTimeSet(0.123, "red")

    await spin(functools.partial(display.breakTimeDisplay))

async def testBreakTimes2():
    display.breakTimeSet(0.123, "red")
    display.breakTimeSet(0.456, "green")
    await spin(functools.partial(display.breakTimeDisplay))

async def testCompetitionUpdate():
    global fakeTimers

    async def competitionUpdate():
        teams = fakeTimers.competition.teams
        displayTime1 = str(teams[0])
        displayTime2 = str(teams[1])
        display.competitionUpdate(displayTime1, teams[0].scoreboardColour, displayTime2, teams[1].scoreboardColour)

    createFakeTimers()

    fakeTimers.competition.resumeTeam1()

    await spin(competitionUpdate)

async def testTeams():
    createFakeTimers()

    teams = fakeTimers.competition.teams
    await spin(functools.partial(display.displayTeamNames, teams[0].name, teams[0].colour, teams[1].name, teams[1].colour, None))

async def testTeamsScrolling():
    createFakeTimers()

    teams = fakeTimers.competition.teams
    await spin(functools.partial(display.displayTeamNames, teams[0].name, teams[0].colour, teams[1].name, teams[1].colour, "vs"))

async def nothing():
    return 0.1

async def testText():
    display.displayText("test text")
    spin(functools.partial(nothing))

async def testSplash():
    async def splashColour(colour):
        display.splashColour(colour)

    await spin(functools.partial(splashColour, (121, 200, 80)))

async def testFlash():
    await spin(functools.partial(display.displayFlashText, "192.168.1.80", "red"))

async def testFlash2():
    await spin(functools.partial(display.displayFlashText, "top\nbottom", "red"))

async def testCountdownUpdate():
    async def countdownUpdate():
        display.countDownUpdate(fakeTimers.countDown)

    fakeTimers.countDown.resume()
    await spin(countdownUpdate)

async def delayedTest(testFn):
    await asyncio.sleep(1)
    await testFn()

def main():
    global display, app, testFn

    TV = False
    if len(sys.argv) > 1 and sys.argv[1] == "TV":
        import TV_Display as displayServer

        sys.argv.pop(1)
        TV = True
    else:
        import LED_RGB_Display as displayServer


    print(sys.argv)
    createFakeTimers()

    if sys.argv[1] == "scrolling":
        del sys.argv[1]
        testFn = testScrolling
    elif sys.argv[1] == "clock":
        del sys.argv[1]
        testFn = testClock
    elif sys.argv[1] == "2line":
        del sys.argv[1]
        testFn = test2Line
    elif sys.argv[1] == "2scrolling":
        del sys.argv[1]
        testFn = test2Scrolling
    elif sys.argv[1] == "break":
        del sys.argv[1]
        testFn = testBreakTimes
    elif sys.argv[1] == "break1":
        del sys.argv[1]
        testFn = testBreakTimes1
    elif sys.argv[1] == "break2":
        del sys.argv[1]
        testFn = testBreakTimes2
    elif sys.argv[1] == "text":
        del sys.argv[1]
        testFn = testText

    elif sys.argv[1] == "competition":
        del sys.argv[1]
        testFn = testCompetitionUpdate

    elif sys.argv[1] == "teams":
        del sys.argv[1]
        testFn = testTeams

    elif sys.argv[1] == "teamsScrolling":
        del sys.argv[1]
        testFn = testTeamsScrolling

    elif sys.argv[1] == "splash":
        del sys.argv[1]
        testFn = testSplash

    elif sys.argv[1] == "update":
        del sys.argv[1]
        testFn = testUpdateTimer

    elif sys.argv[1] == "countdown":
        del sys.argv[1]
        testFn = testCountdownUpdate

    elif sys.argv[1] == "elapsed":
        del sys.argv[1]
        testFn = testElapsedUpdate

    elif sys.argv[1] == "timerUpdate":
        del sys.argv[1]
        testFn = testTimerUpdate

    elif sys.argv[1] == "flash":
        del sys.argv[1]
        testFn = testFlash

    elif sys.argv[1] == "flash2":
        del sys.argv[1]
        testFn = testFlash2

    elif sys.argv[1] == "blank":
        del sys.argv[1]
        testFn = testBlank


    if TV:
        display = displayServer.create(sys.argv, "welcome to my nightmare", "test.config")
    else:
        display = displayServer.create(sys.argv, "welcome to my nightmare", "defaults/display.toml")

    display.startDisplay()
    loop = display.run()

    loop.run_until_complete(delayedTest(testFn))
    

if __name__ == "__main__":
    main()
