
from AutoConfigParser import ConfigSectionHandler


class DefaultsConfigSection(ConfigSectionHandler):
    section = "Defaults"
    
    attributes = {"finishedMessage": 		"Finish this end and play one more",
                  "finishedMessageColour": 	"green",
                  "finishedMessageDisplayTime": "0",
                  "gameTime": 			"1:40:00",
                  "lastEndMessage": 		"Last End",
                  "lastEndMessageColour": 	"red",
                  "welcomeMessage": 		"Hello",
                  "scrollTeamsSeparator": 	"",
                  "largeActiveTeamTimer":       (int, str, 0),
                  "largeStoppedTeamTimer":      (int, str, 0),
                  "betweenEndTime":             (int, str, 30),
                  "extraEndTime":               "4:30",
                  "teamTime": 			"40:00",
                  "intermissionLength": 	"8:00",
                  "defaultPINExpireTime": 	"3:00:00",
                  "blankTime": 			"30:00",
                  "timeoutLength": 		"0:30",
                  "rockCircumference":          (int, str, 910),
                  "ipOnStart": 		        (int, str, 1),
                  "numberOfTimeouts": 		(int, str, 2),
                  "drawServer": 		"",
                  "breakFilterTime": 		(int, str, 5)}
