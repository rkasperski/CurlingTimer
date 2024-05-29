from TokenAuthentication import TokenAuthentication
import time


def pinExpireTime(sheet):
    s = sheet.pinExpireTime

    try:
        expireTime = int(s)
    except ValueError:
        return None

    remaining = expireTime - time.time()

    if remaining > 0:
        return expireTime

    return None


class ClockTokenAuthentication(TokenAuthentication):
    def __init__(self, users):
        super().__init__()
        self.users = users

    def verify(self, s, mySheet=None):
        tkn = super().verify(s)

        if tkn is None:
            return None

        aud = tkn["aud"]
        user = tkn["user"]

        if aud == "user":
            if tkn["user"] in self.users:
                return tkn
            
        elif aud == "pin" and mySheet:
            # pin enabled sheet
            if user == mySheet.name:
                if tkn["pin"] == mySheet.pin and pinExpireTime(mySheet):
                    return tkn

        return tkn
