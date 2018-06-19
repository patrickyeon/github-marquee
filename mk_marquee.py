#!/usr/bin/python

import os, sys

from argparse import ArgumentParser
from datetime import date, datetime, timedelta
from font import font
from subprocess import call

timefmt = '%Y-%m-%dT%H:%M:%S'

# canvas we are drawing on is 52 x 7
#   0   7       ...       350 357
#   1   8       ...       351 358
# ... ...       ...       ... ...
#   5  12       ...       355 362
#   6  13       ...       356 363

# test patterns
def primefill():
    def isprime(n):
        for i in xrange(2, n):
            if i * i > n:
                return True
            if n % i == 0:
                return False
        return True
    return [i for i in range(364) if isprime(i)]
def vstripes(stride):
    retval = []
    for i in range(52):
        if i % stride == 0:
            retval.extend(range(i * 7, (i + 1) * 7))
    return retval
def hstripes(stride):
    retval = []
    baseline = [i * 7 for i in range(52)]
    for i in range(7):
        if i % stride == 0:
            retval.extend([b + i for b in baseline])
    return sorted(retval)
def box():
    return sorted(range(7) + range(0, 364, 7)
                  + range(6, 364, 7) + range(357, 364))

def dotmatrix(s):
    s = reversed(s[-8:])
    retval = []
    for i, c in enumerate(s):
        c = ord(c)
        if 0x20 > c or 0x7d < c:
            c = 0x20
        rune = font[c - 0x20]
        for j, col in enumerate(rune):
            for k in range(7):
                if col & (1 << k):
                    retval.append((46 * 7) - (i*6*7) + j*7 + k)
    return retval


if __name__ == '__main__':
    ap = ArgumentParser()
    ap.add_argument('--box', action='store_true',
                    help='draw the outline of the canvas')
    ap.add_argument('--primes', action='store_true',
                    help='colour in prime-numbered pixels')
    ap.add_argument('--rows', type=int,
                    help='colour in every Nth row (weekday)')
    ap.add_argument('--columns', type=int,
                    help='colour in every Nth column (week)')
    ap.add_argument('--dry-run', action='store_true',
                    help='output to console, no git actions')
    ap.add_argument('--text',
                    help='string to display (recommend <= 8 chars)')
    ap.add_argument('--repo', help='github user/repo to push to')
    ap.add_argument('--depth', type=int,
                    help='number of commits per pixel')
    args = ap.parse_args()

    pixels = []
    if args.box:
        pixels.extend(box())
    if args.primes:
        pixels.extend(primefill())
    if args.rows:
        pixels.extend(hstripes(args.rows))
    if args.columns:
        pixels.extend(vstripes(args.columns))
    if args.text:
        pixels.extend(dotmatrix(args.text))
    pixels = sorted(set(pixels))

    # find the most recent saturday (not including today)
    today = date.today()
    if today.weekday() == 6:
        br = today - timedelta(1)
    else:
        br = today - timedelta(today.weekday() + 2)

    # all tomfoolery happens at 3AM
    bot_right = datetime(br.year, br.month, br.day, 3, 0, 0)
    top_left = bot_right - timedelta(52 * 7 - 1)

    if args.dry_run:
        for r in range(7):
            dots = ['x' if c in pixels else ' ' for c in range(r, 52*7, 7)]
            print ''.join(dots)
        print 'TL, BR corners would be {}, {}'.format(top_left, bot_right)
        print ' '.join(sys.argv)
        exit()

    if os.path.exists('.git'):
        print 'Run this from a directory that is not the root of a repo.'
        print 'This is for your own good.'
        exit(1)

    call(['git', 'init'])
    with open('README.md', 'w') as f:
        f.write('''
# Spice up your GitHub profile
## with github_marquee.py

Created with

''')
        f.write(' '.join(sys.argv) + '\n\n')
        f.write('https://github.com/patrickyeon/github-marquee\n')

    call(['git', 'add', 'README.md'])
    call(['git', 'commit', '-m', '"initialize with README"',
          '--date={}'.format((top_left + timedelta(-365)).strftime(timefmt))])

    times = [0]
    if args.depth and args.depth >= 2:
        # arbitrarily going to limit to 3600 commits per pixel
        depth = int(min(args.depth - 1, 60 * 60))
        timestep = float(60 * 60) / depth
        times.extend([n * timestep for n in range(depth)])
    for px in pixels:
        for time in times:
            date = (top_left + timedelta(px, time)).strftime(timefmt)
            call(['git', 'commit', '-m', '"add a dot"',
                  '--allow-empty', '--date={}'.format(date)])

    if args.repo:
        repo = args.repo
        if not repo.endswith('.git'):
            repo += '.git'
        call('git remote add origin git@github.com:{}'.format(repo).split())
        call('git push -u origin master'.split())
