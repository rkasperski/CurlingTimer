from time import time as time_time
from token_authentication import TokenAuthentication


def pin_expire_time(sheet):
    s = sheet.pin_expire_time

    try:
        expire_time = int(s)
    except ValueError:
        return None

    remaining = expire_time - time_time()

    if remaining > 0:
        return expire_time

    return None


class ClockTokenAuthentication(TokenAuthentication):
    def __init__(self, users):
        super().__init__()
        self.users = users

    def verify(self, s, my_sheet=None):
        tkn = super().verify(s)

        if tkn is None:
            return None

        aud = tkn["aud"]
        user = tkn["user"]

        if aud == "user":
            if tkn["user"] in self.users:
                return tkn

        elif aud == "pin" and my_sheet:
            # pin enabled sheet
            if user == my_sheet.name:
                if tkn["pin"] == my_sheet.pin and pin_expire_time(my_sheet):
                    return tkn

        return tkn
