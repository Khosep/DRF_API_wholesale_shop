from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AnonShortRateThrottle(AnonRateThrottle):
    scope = "anon_short"


class AnonLongRateThrottle(AnonRateThrottle):
    scope = "anon_long"


class UserShortRateThrottle(UserRateThrottle):
    scope = "user_short"


class UserLongRateThrottle(UserRateThrottle):
    scope = "user_long"