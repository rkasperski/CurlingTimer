import functools, CurlingClockTimers
import sys
import asyncio

from Kapow import RotatingBlock, Rain, Life, Symbols

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
    fakeDefaults.lastEndMessageDisplayTime = "15:00"

    fakeTimers = CurlingClockTimers.Timers(fakeDefaults, fakeSheetData,lambda : False)
    fakeTimers.competition.teams[0].name = "Ratakowsky"
    fakeTimers.competition.teams[1].name = "O'Connor"

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

async def testClock10ths():
    async def clockUpdate10ths():
        display.clockUpdate(showTenths=True)

    await spin(clockUpdate10ths)

async def test2Line():
    await spin(functools.partial(display.twoLineText, "line p" , "line y", centre=True))

async def test2Scrolling():
    await spin(functools.partial(display.twoLineText, "line1 - is too lone" , "line2"))

async def testBreakTimes():
    await spin(functools.partial(display.breakTimeDisplay))

async def testBreakTimes1():
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
    await spin(functools.partial(nothing))

async def testBlank():
    display.bkank()
    await spin(functools.partial(nothing))

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
        display.updateTimer(str(fakeTimers.countDown), "white", "cdt:")

    fakeTimers.countDown.resume()
    await spin(countdownUpdate)

async def testElapsedUpdate():
    async def elapsedUpdate():
        display.updateTimer(str(fakeTimers.elapsedTime), "white", "cdt:")

    fakeTimers.elapsedTime.resume()
    await spin(elapsedUpdate)

async def testElapsed10thsUpdate():
    fakeTimers.elapsedTime.showTenths = True

    async def elapsed10thsUpdate():
        display.updateTimer(str(fakeTimers.elapsedTime), "white", "cdt:", showTenths=True)

    fakeTimers.elapsedTime.resume()
    
    await spin(elapsed10thsUpdate)

async def delayedTest(testFn):
    await asyncio.sleep(1)
    await testFn()

async def testDots():
    i = -1
    r, g, b = [128, 129, 128]

    drawable = display.getClearedDrawable()
    drawable.show()

    while True:
        i += 1

        r = (r + 9) % 255
        g = (g + 31) % 255
        b = (b + 67) % 255

        drawable.start()
        drawable.drawPoint(i % drawable.width, int(i / drawable.width) % drawable.height, (r, g, b))
        drawable.show()
        await asyncio.sleep(0.2)

async def testCircles():
    i = -1
    r, g, b = [128, 129, 128]

    drawable = display.getClearedDrawable()
    drawable.show()

    centerX = int(drawable.width / 2)
    centerY = int(drawable.height / 2)
    maxD = int(max(drawable.visible_pixels) / 2)
    pd = drawable.visible_pixel_dimension
    i = 1234567890 * maxD - 1
    while True:
        i = (i - 1) % maxD

        r = (r + 9) % 255
        g = (g + 31) % 255
        b = (b + 67) % 255

        drawable.start()
        drawable.drawCircle(centerX, centerY, pd * i, borderColour=(r, g, b))
        display.show(drawable)
        await asyncio.sleep(0.2)

async def testRects():
    i = -1
    r, g, b = [128, 129, 128]

    drawable = display.getClearedDrawable()
    drawable.show()

    centerX = int(drawable.width / 2)
    centerY = int(drawable.height / 2)

    maxD = int(max(drawable.visible_pixels) / 2)

    pd = drawable.visible_pixel_dimension
    i = 1234567890 * maxD - 1
    while True:
        i = (i - 1) % maxD

        r = (r + 9) % 255
        g = (g + 31) % 255
        b = (b + 67) % 255

        t = i * pd
        drawable.start()
        drawable.drawRect(centerX - t, centerY - t, t + t - 1, t + t - 1, borderColour=(r, g, b))
        drawable.show()
        await asyncio.sleep(0.2)

async def testKapow(whichKapow):
    kapow = whichKapow(display.getDrawable())

    await spin(kapow.next)

async def testPolygons():
    star_vertices = ((000, 300), (300, 300), (400, 000), (500, 300), (800, 300), (550, 500), (650, 800), (400, 600), (150, 800), (250, 500))

    i = -1
    r, g, b = [128, 129, 128]

    drawable = display.getClearedDrawable()
    drawable.show()

    centerX = int(drawable.width / 2)
    centerY = int(drawable.height / 2)

    maxD = max(drawable.visible_pixels)
    pd = drawable.visible_pixel_dimension

    i = 1234567890 + maxD - 1
    while True:
        i = (i - 1) % maxD

        r = (r + 9) % 255
        g = (g + 31) % 255
        b = (b + 67) % 255

        pi = i * pd
        offset = (centerX - int(((800 / maxD) * i  / 800) * pi) , centerY - int((800 / maxD) * (i / 800) * pi))

        pts = [(int((x / 800) * pi) + offset[0], int((y / 800) * pi) + offset[1]) for x, y in star_vertices]

        drawable.start()
        drawable.drawPolygon(pts, borderColour=(r, g, b))
        drawable.show()
        await asyncio.sleep(0.2)

def main():
    global display, app, testFn

    TV = False
    a = sys.argv.pop(1)
    if a == "TV":
        import TV_Display as displayServer

        a = sys.argv.pop(1)
        TV = True
    else:
        import LED_RGB_Display as displayServer

    createFakeTimers()

    testFunctions = {
        "scrolling": testScrolling,
        "clock": testClock,
        "clock10ths": testClock10ths,
        "2line": test2Line,
        "2scrolling": test2Scrolling,
        "break": testBreakTimes,
        "break1": testBreakTimes1,
        "break2": testBreakTimes2,
        "text": testText,
        "competition": testCompetitionUpdate,
        "teams": testTeams,
        "teamsScrolling": testTeamsScrolling,
        "vs": testTeamsScrolling,
        "splash": testSplash,
        "countdown": testCountdownUpdate,
        "elapsed": testElapsedUpdate,
        "elapsed10ths": testElapsed10thsUpdate,
        "flash": testFlash,
        "flash2": testFlash2,
        "blank": testBlank,
        "dots": testDots,
        "circles": testCircles,
        "rects": testRects,
        "polygons": testPolygons,
        "block": functools.partial(testKapow, RotatingBlock),
        "rain": functools.partial(testKapow, Rain),
        "life": functools.partial(testKapow, Life),
        "star": functools.partial(testKapow, lambda x: Symbols(x, "star")),
        "square": functools.partial(testKapow, lambda x: Symbols(x, "square")),
        "circle": functools.partial(testKapow, lambda x: Symbols(x, "circle"))
    }
    
    testFn = testFunctions.get(a, None)

    if testFn is None:
        print(f"{a} is not a valid test")
        print(f"try one of {', '.join(testFunctions.keys())}")
        sys.exit(4)

    if TV:
        display = displayServer.create(sys.argv, "welcome to my nightmare", "test.config")
    else:
        display = displayServer.create(sys.argv, "welcome to my nightmare", "defaults/display.toml")

    display.startDisplay()
    loop = display.run()

    loop.run_until_complete(delayedTest(testFn))
    

if __name__ == "__main__":
    main()
