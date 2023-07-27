import sys
import clifn

argvs = [
    ['clifn',],
    ['clifn', '-o',],
    ['clifn', 'sub-command-1', 'a'],
    ['clifn', 'sub-command-1', 'b', 'c'],
    ['clifn', 'sub-command-1', '-o', 'd'],
    ['clifn', 'sub-command-1', '-o', 'e', 'f'],
    # demo spec does not account for sub-command-2 by itself
    #['clifn', 'sub-command-2', 'g'],
    #['clifn', 'sub-command-2', 'h', 'i'],
    #['clifn', 'sub-command-2', '-o', 'j'],
    #['clifn', 'sub-command-2', '-o', 'k', 'l'],
    #['clifn', 'sub-command-2', 'sub-command-1', 'm'],
    ['clifn', 'sub-command-2', 'sub-command-1', 'n', 'o'],
    ['clifn', 'sub-command-2', 'sub-command-1', '-o', 'p'],
    ['clifn', 'sub-command-2', 'sub-command-1', '-o', 'q', 'p'],
]

def test_argvs():
    bads = []
    for argv in argvs:
        sys.argv = argv
        try:
            clifn.main()
        except BaseException as e:
            bads.append((argv, e))

    assert not bads, ';'.join([' '.join(b) for b, e in bads])
