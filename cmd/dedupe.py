from lib import options, gitdb, entry

optspec = """
crampi dedupe <dest-refname> --using <refname|commitid>
--
d,gitdb=   name of gitdb sqlite3 database file [crampi.sqlite3]
using=     refname or commitid to use as GUID source
"""

def main(argv):
    o = options.Options('crampi dedupe', optspec)
    (opt, flags, extra) = o.parse(argv[1:])

    if len(extra) != 1:
        o.fatal('exactly one argument expected; use "crampi log" for a list')
        
    g = gitdb.GitDb(opt.gitdb)

    dstbranch = extra[0]
    dst = g.commitid_latest(dstbranch)
    if not dst:
        o.fatal('invalid argument; specify a valid refname')

    if not opt.using:
        o.fatal('you must provide --using')
    if opt.using == extra[0]:
        o.fatal('--using option %r must differ from destination branch %r'
                % (opt.using, extra[0]))

    if g.commit(opt.using):
        src = opt.using
    else:
        src = g.commitid_latest(opt.using)
        if not src:
            o.fatal('invalid --using; specify a valid refname or commitid')

    esrc = entry.load_tree_from_commit(g, src)
    edst = entry.load_tree_from_commit(g, dst)

    def _keygen(e):
        k = ((e.d.get('lastname') or '').strip().lower(),
             (e.d.get('firstname') or '').strip().lower())
        if not filter(None, k):  # all sub-elements are blank
            k = ((e.d.get('company') or '').strip(),)
        if not filter(None, k):
            return None
        else:
            return k

    srcdict = {}
    for e in esrc.entries:
        key = _keygen(e)
        srcdict[key] = e

    edst.reindex()
    for e in edst.entries:
        if not e.lid:
            print 'barf: ', e
        key = _keygen(e)
        se = srcdict.get(key)
        if key and se and not edst.uuids.get(se.uuid):
            print e.uuid, se.uuid
            del srcdict[key]  # max one mapping each
            e.uuid = se.uuid
    edst.save_commit(g, dstbranch, 'deduplicated from %r@%r into %r@%r' 
                     % (opt.using, src, dstbranch, dst))
    g.flush()
