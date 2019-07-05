import configparser
import os

_config_dir = os.path.join(os.path.expanduser('~'), '.coinapi')
_config_file = os.path.join(_config_dir, 'apikey.config')

def get_configd():
    configd = {'config_dir': _config_dir, 'config_file': _config_file}

    if not os.path.isdir(_config_dir):
        os.mkdir(_config_dir)

    if not os.path.isfile(_config_file):
        with open(_config_file, 'w') as f:
            f.write('')
        configd['config'] = None
        return configd

    config = configparser.ConfigParser()
    config.read(_config_file)

    configd['config'] = config
    return configd

