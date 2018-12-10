#!/usr/bin/python3

# Copyright 2008 Robert Siemer
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


# esniper-manager [dir]

# if a file disappears: kill sniper
# if a new file arrives: start sniper
# if a file changes: kill old sniper, start a new one

# relation: file --> sniper (relative file name --> Popen instance)

# "start sniper": esniper auctionfile with redirection to log/auctionfile.log
# "kill sniper": kill process number

# go to dir
# watch dir
# get a dir list
# run for each file a sniper
# react on dir changes

# IN_CLOSE_WRITE: restart
# IN_MOVED_FROM: stop
# IN_MOVED_TO: restart
# IN_DELETE: stop

import os, re, subprocess, argparse, logging

def filefilter(name, bad = re.compile(r"\.bug\.html", re.UNICODE)):
    return not bad.search(name)

class Snipers(object):
    def __init__(self):
        self.proc = {}

    def stop(self, auction):
        if auction not in self.proc:
            logging.debug("no esniper started for " + auction)
        else:
            logging.debug("stopping " + auction)
            p = self.proc.pop(auction)
            logging.debug('pid ' + str(p.pid))
            p.kill()
            p.wait()

    def restart(self, auction):
        if auction in self.proc:
            self.stop(auction)
        logging.debug("starting " + auction)
        log = open("log/" + auction, 'a')  # use logrotate on the file
        self.proc[auction] = subprocess.Popen(["esniper", auction],
            stdout=log, stderr=subprocess.STDOUT, cwd='auction/')


from pyinotify import WatchManager, Notifier, ProcessEvent, EventsCodes

class ProcessFiles(ProcessEvent):

    def __init__(self, snipers):
        self._snipers = snipers

    def process_IN_CLOSE_WRITE(self, event):
        if filefilter(event.name):
            self._snipers.restart(event.name)

    process_IN_MOVED_TO = process_IN_CLOSE_WRITE

    def process_IN_MOVED_FROM(self, event):
        if filefilter(event.name):
            self._snipers.stop(event.name)

    process_IN_DELETE = process_IN_MOVED_FROM


def main():
    argparser = argparse.ArgumentParser(description='%(prog)s watches directory for auction/* files to attach esnipers.')
    argparser.add_argument('--version', action='version', version='%(prog)s 0.3')
    argparser.add_argument('-d', '--debug', action='store_true', help='print simple debug statements')
    argparser.add_argument('directory', help='Directory to watch for auctions.')
    args = argparser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    os.chdir(args.directory)
    snipers = Snipers()
    wm = WatchManager()
    mask = EventsCodes.ALL_FLAGS['IN_CLOSE_WRITE']|EventsCodes.ALL_FLAGS['IN_MOVED_TO']| \
        EventsCodes.ALL_FLAGS['IN_MOVED_FROM']|EventsCodes.ALL_FLAGS['IN_DELETE']
    notifier = Notifier(wm, ProcessFiles(snipers))
    wm.add_watch('auction/', mask)

    auctions = filter(filefilter, os.listdir('auction/'))
    for a in auctions:
        snipers.restart(a)

    while True:
        logging.debug('cycle')
        if notifier.check_events(None): # "None" necessary for endless select()
            notifier.read_events()
            notifier.process_events()

if __name__ == '__main__':
    main()
