class HappyCatException(Exception):
    ...


class HappyCatDecryptException(HappyCatException):
    ...


class HappyCatTimeoutException(HappyCatException):
    ...


class HappyCatNetworkException(HappyCatException):
    ...


class HappyCatDecryptFileNotFoundException(HappyCatException):
    ...


class HappyCatLoginException(HappyCatException):
    ...


class HappyCatReserveException(HappyCatException):
    ...
