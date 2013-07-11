# -*- coding: utf-8 -*-
#
# Copyright © 2006 - 2013 Michal Čihař <michal@cihar.com>
#
# This file is part of Weblate <http://weblate.org/>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import hashlib
import os
import datetime
import re
import json


README_TEXT = '''%(title)s
%(line)s

This is autogenerated dictionary for StarDict.

Data were downloaded from following website:
<%(url)s>

The original source is available under %(license)s.

Dictionary was generated using:
Stardicter version %(version)s

You can get conversion script from:
<http://cihar.com/software/slovnik/>

Install dictionary by copying dictionary files to dic/ folder in
StarDict. On Linux it is usually /usr/share/stardict/dic/, on Windows
C:\Program files\stardict\dic\.
'''

STRIPTAGS = re.compile(r"<.*?>", re.DOTALL)

CONFIGFILE = os.path.expanduser('~/.stardicter')

AUTHOR = u'Stardicter'
URL = 'https://cihar.com/software/slovnik/'


class StardictWriter(object):
    '''
    Generic writer for stardict dictionary.
    '''
    url = None
    name = 'Generic'
    prefix = ''
    source = 'aa'
    target = 'bb'
    license = ''

    fmt_type = u'<span size="larger" color="darkred" weight="bold">%s</span>\n'
    fmt_details = u'<i>%s</i> '
    fmt_translate = u'<b>%s</b>'
    fmt_note = u' (%s)'
    fmt_author = u' <small>[%s]</small>'

    def __init__(self, ascii=False, notags=False):
        self.words = {}
        self.reverse = {}
        self.description = ''
        self.ascii = ascii
        self.notags = notags
        self._data = None
        self._checksum = None

    @property
    def data(self):
        '''
        Returns downloaded data file.
        '''
        if self._data is None:
            self._data = self.download()
        return self._data

    @property
    def lines(self):
        '''
        Returns lines.
        '''
        return self.data.splitlines()

    @property
    def checksum(self):
        '''
        Returns data checksum.
        '''
        if self._checksum is None:
            self._checksum = self.get_checksum()
        return self._checksum

    def get_filename(self, forward=True):
        '''
        Returns filename for dictionary.
        '''
        if forward:
            return '%s%s-%s' % (self.prefix, self.source, self.target)
        else:
            return '%s%s-%s' % (self.prefix, self.target, self.source)

    def get_name(self, forward=True):
        '''
        Returns dictionary name.
        '''
        return self.name

    def is_data_line(self, line):
        '''
        Checks whether line is used for checksum. Can be used to exclude
        timestamps from data.
        '''
        return True

    def get_checksum(self):
        '''
        Calculated dictionary checksum.
        '''
        md5 = hashlib.md5()
        for line in self.lines:
            if self.is_data_line(line):
                md5.update(line)
        return md5.hexdigest()

    def download(self):
        '''
        Downloads dictionary.
        '''
        return 'foo:bar'

    def parse(self):
        '''
        Parses dictionary.
        '''
        for line in self.lines:
            word, translation = line.split(':')
            self.words[word] = translation
            self.reverse[translation] = word

    def xmlescape(self, text):
        '''
        Escapes special xml entities.
        '''
        return text.replace(
            '&', '&amp;'
        ).replace(
            '<', '&lt;'
        ).replace(
            '>', '&gt;'
        )

    def convert(self, text):
        '''
        Converts text to match wanted format.
        '''
        if self.ascii:
            text = text.encode('ascii', 'deaccent')

        if self.notags:
            text = STRIPTAGS.sub('', text)

        return text

    def getsortedwords(self, words):
        '''
        Returns keys of hash sorted case insensitive.
        '''
        tuples = [(item.encode('utf-8').lower(), item) for item in words]
        tuples.sort()
        return [item[1] for item in tuples]

    def write_words(self, directory, filename, name, words):
        '''
        Writes word list to dictionary files.
        '''
        # initialize variables
        offset = 0
        count = 0
        idxsize = 0

        # File names
        basefilename = os.path.join(directory, filename)
        dictn = '%s.dict' % basefilename
        idxn = '%s.idx' % basefilename
        ifon = '%s.ifo' % basefilename

        # Write dictionary and index
        with open(dictn, 'w') as dictf, open(idxn, 'w') as idxf:

            for key in self.getsortedwords(words):
                # format single entry
                deftext = self.convert(self.formatentry(wlist[key]))

                # write dictionary text
                entry = deftext.encode('utf-8')
                dictf.write(entry)

                # write index entry
                idxf.write(self.convert(key).encode('utf-8') + '\0')
                idxf.write(struct.pack('!I', offset))
                idxf.write(struct.pack('!I', len(entry)))

                # calculate offset for next index entry
                offset += len(entry)
                count += 1

            # index size is needed in ifo
            idxsize = idxf.tell()

        # Write info file
        with open(ifon, 'w') as ifof:
            ifof.write('StarDict\'s dict ifo file\n')
            ifof.write('version=2.4.2\n')
            ifof.write(self.convert(u'bookname=%s\n' % name).encode('utf-8'))
            ifof.write('wordcount=%d\n' % count)
            ifof.write('idxfilesize=%d\n' % idxsize)
            ifof.write(self.convert('author=%s\n' % AUTHOR).encode('utf-8'))
            ifof.write(self.convert('website=%s\n' % URL).encode('utf-8'))
            # we're using pango markup for all entries
            ifof.write('sametypesequence=g\n')
            ifof.write(datetime.date.today().strftime('date=%Y.%m.%d\n'))

    def write_dict(self, directory):
        '''
        Writes dictionary into directory.
        '''
        # Write readme
        with open(os.path.join(directory, 'README'), 'w') as readme:
            readme.write(self.get_readme())
        # Write forward dictioanry
        self.write_words(
            directory,
            self.get_filename(True),
            self.get_name(True),
            self.words
        )
        # Write reverse dictionary
        self.write_words(
            directory,
            self.get_filename(False),
            self.get_name(False),
            self.reverse
        )

    def get_readme(self):
        '''
        Generates README text for dictionary.
        '''
        title = '%s for StarDict' % self.name
        return README_TEXT % {
            'title': title,
            'line': '-' * len(title),
            'url': self.url,
            'license': self.license,
            'version': '0.1',
        }

    def load_config(self):
        '''
        Loads checksum cache.
        '''
        with open(CONFIGFILE) as handle:
            try:
                return json.load(handle)
            except ValueError:
                return {}

    def save_config(self, changes):
        '''
        Loads checksum cache.
        '''
        config = self.load_config()
        config.update(changes)
        with open(CONFIGFILE, 'w') as handle:
            json.dump(config, handle, indent=2)

    def was_changed(self):
        '''
        Detects whether dictionary has same content as on last run.
        '''
        key = self.get_filename()
        config = self.load_config()
        if key not in config:
            return True
        return self.checksum != config[key]

    def save_checksum(self):
        '''
        Saves checksum to configuration.
        '''
        key = self.get_filename()
        self.save_config({key: self.checksum})
