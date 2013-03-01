#!/usr/bin/python
# Needs at least python2.5 for correct subprocess module.
# With this one subprocess does not clean up behind your back.

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

import sys, os, signal, optparse, re, subprocess, locale
# for output/log file encoding (does not work as _we_ don't write in that file)
# maybe for filefilter re checks (but I think just plain "UNICODE" is better)
# to convert file names to unicode objects I don't need to set the locale, but anyway
locale.resetlocale() # same as locale.setlocale(locale.LC_ALL, '') or not?
encoding = locale.getpreferredencoding(False) # here we get _always_ a good guess

def debug(msg):
    print >> sys.stderr, msg

def unicod(str):
    return unicode(str, encoding, 'replace')

def filefilter(name, bad = re.compile(ur"\W", re.UNICODE)):
    return not bad.search(unicod(name))

class Snipers(object):
    def __init__(self):
        self.proc = {}

    def stop(self, auction):
        if auction not in self.proc:
            debug("no esniper started for " + auction)
        else:
            debug("stopping " + auction)
            p = self.proc.pop(auction)
            debug('pid ' + str(p.pid))
            os.kill(p.pid, signal.SIGTERM)
            #pid = self.proc.pop(auction)
            #debug("Killing " + auction)
            #os.kill(pid, signal.SIGTERM)
            #os.waitpid(pid, 0)
            #debug(auction + " finished.")

    def restart(self, auction):
        if auction in self.proc:
            self.stop(auction)
        debug("starting " + auction)
        log = open("log/" + auction, 'w')
        self.proc[auction] = subprocess.Popen(["esniper", auction],
            stdout=log, stderr=subprocess.STDOUT, cwd='auction/')
        #debug("Forking for " + auction)
        #pid = os.fork()
        #if pid == 0: # child
            ## logfd = os.open('log/' + auction, os.O_WRONLY|os.O_CREAT|os.O_TRUNC)
            #log = open("log/" + auction, 'a')
            #os.dup2(log.fileno(), sys.stdout.fileno())
            #os.execlp("esniper", "esniper", auction)
        ## parent
        # self.proc[auction] = pid


from pyinotify import WatchManager, Notifier, ProcessEvent, EventsCodes

class ProcessFiles(ProcessEvent):
    def process_IN_CLOSE_WRITE(self, event):
        if filefilter(event.name):
            snipers.restart(event.name)

    process_IN_MOVED_TO = process_IN_CLOSE_WRITE

    def process_IN_MOVED_FROM(self, event):
        if filefilter(event.name):
            snipers.stop(event.name)

    process_IN_DELETE = process_IN_MOVED_FROM


optparser = optparse.OptionParser(version="%prog 0.2",
    usage='%prog [options] directory',
    description='%prog watches directory for auction/* files to attach esnipers.')
optparser.add_option('-d', '--debug', action='store_true',
                help='print simple debug statements')

options, args = optparser.parse_args()

if len(args) != 1:
    optparser.error("I need a directory to watch for auctions.")

if not options.debug: debug = lambda msg: None

os.chdir(args[0])
snipers = Snipers()
wm = WatchManager()
mask = EventsCodes.ALL_FLAGS['IN_CLOSE_WRITE']|EventsCodes.ALL_FLAGS['IN_MOVED_TO']| \
    EventsCodes.ALL_FLAGS['IN_MOVED_FROM']|EventsCodes.ALL_FLAGS['IN_DELETE']
notifier = Notifier(wm, ProcessFiles())
wm.add_watch('auction/', mask)

auctions = filter(filefilter, os.listdir('auction/'))
for a in auctions:
    snipers.restart(a)

while True:
    debug('cycle')
    if notifier.check_events(None): # "None" necessary for endless select()
        notifier.read_events()
        notifier.process_events()
