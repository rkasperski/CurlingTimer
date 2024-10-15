"""
Creates the timers used to track curling games
"""

from Timers import CountDownTimer, ElapsedTimeTimer, CompetitionTimer

class Timers():
    def __init__(self, defaults, mySheetData, isIdle):
        self.competition = CompetitionTimer()
        self.competition.teams[0].colour = mySheetData.topColour
        self.competition.teams[0].scoreboardColour = mySheetData.topColour
        self.competition.teams[1].colour = mySheetData.bottomColour
        self.competition.teams[1].scoreboardColour = mySheetData.bottomColour

        self.countDown = CountDownTimer(defaults.gameTime)
        self.countDown.setFinishedMessage(defaults.finishedMessage,
                                          defaults.finishedMessageColour,
                                          defaults.finishedMessageDisplayTime)
        self.countDown.setLastEndMessage(defaults.lastEndMessage,
                                         defaults.lastEndMessageColour)
        self.elapsedTime = ElapsedTimeTimer(0)
        self.intermission = CountDownTimer(8 * 60)
        self.intermission.colour = "white"
        self.timeout = CountDownTimer(2 * 60)
        self.timeout.colour = "white"
        self.timeout.teamId = "unknown"
        self.timeout.team = None
        self.isIdle = isIdle

    def isActive(self):
        return self.competition.active() or self.countDown.active() or self.elapsedTime.active() or self.intermission.active() or self.timeout.active()
       
    def ajaxResponse(self, response):
        response.update({"active": self.isActive(),
                         "competition": self.competition.ajaxResponse(),
                         "countdown": self.countDown.ajaxResponse(),
                         "elapsedtime": self.elapsedTime.ajaxResponse(),
                         "intermission": self.intermission.ajaxResponse(),
                         "timeout": self.timeout.ajaxResponse(),
                         "idle": self.isIdle()})

        return response
