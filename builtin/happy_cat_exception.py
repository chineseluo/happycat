class HappyCatException(Exception):
    ...


class HappyCatDecryptException(HappyCatException):
    """
    解密异常
    """
    ...


class HappyCatTimeoutException(HappyCatException):
    ...


class HappyCatNetworkException(HappyCatException):
    ...


class HappyCatDecryptFileNotFoundException(HappyCatException):
    ...


class HappyCatLoginException(HappyCatException):
    ...


class HappyCatAddGoodsToShoppingCarException(HappyCatException):
    ...


class HappyCatReserveException(HappyCatException):
    ...
