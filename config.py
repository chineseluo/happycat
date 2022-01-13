import os
import configparser
from loguru import logger
from builtin.happy_cat_exception import HappyCatDecryptFileNotFoundException


class Config(object):
    def __init__(self, config_file='../config.ini'):
        self._path = os.path.join(os.getcwd(), config_file)
        logger.info(self._path)
        if not os.path.exists(self._path):
            raise HappyCatDecryptFileNotFoundException("快乐喵检查配置文件失败，未找到config.ini")
        self._config = configparser.ConfigParser()
        self._config.read(self._path, encoding='utf-8-sig')
        self._configRaw = configparser.RawConfigParser()
        self._configRaw.read(self._path, encoding='utf-8-sig')

    def get(self, section, name):
        return self._config.get(section, name)

    def getRaw(self, section, name):
        return self._configRaw.get(section, name)


global_config = Config()
