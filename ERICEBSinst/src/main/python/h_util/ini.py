from ConfigParser import SafeConfigParser, NoOptionError, NoSectionError
import os
from re import match


class ini_reader:
    def __init__(self, ini_file):
        if not os.path.exists(ini_file):
            raise IOError(2, '{0} not found'.format(ini_file))
        self.ini_file = ini_file
        self.inireader = SafeConfigParser()
        self.inireader.optionxform = str
        self.inireader.read(self.ini_file)

    def get_option(self, section, option, seperator=None, default=None):
        if self.inireader.has_section(section):
            if self.inireader.has_option(section, option):
                value = self.inireader.get(section, option)
            elif default is not None:
                value = default
            else:
                raise NoOptionError(option, section)
        elif default is not None:
            value = default
        else:
            raise NoSectionError(section)
        if seperator is not None:
            value = value.split(seperator)
        return value

    def get_section(self, section):
        if self.inireader.has_section(section):
            items = self.inireader.items(section)
            data = {}
            for item in items:
                data[item[0]] = item[1]
            return data
        else:
            raise NoSectionError(section)

    def get_block_names(self):
        return self.inireader.sections()

    def get_site_value(self, section, option, default_value=None,
                       seperator=None):
        if self.inireader.has_option(section, option):
            _value = self.inireader.get(section, option)
        elif default_value is not None:
            _value = default_value
        else:
            raise NoOptionError(option, section)
        if seperator is not None:
            _value = _value.split(seperator)
        return _value

    def get_site_section_keys(self, section, key_filter=None):
        keys = self.inireader.options(section)
        if key_filter:
            keys[:] = [key for key in keys if match(key_filter, key)]
        return keys
