#!/usr/bin/python
# coding=utf-8
import os.path
import sqlite3
import sys
import unicodedata

ATOM_NS = '{http://www.w3.org/2005/Atom}'
G_NS = '{http://schemas.google.com/g/2005}'
GC_NS = '{http://schemas.google.com/contact/2008}'

configfile = os.path.expanduser('~/.config/gabconfig.py')
database = os.path.expanduser('~/.cache/simplegab.db')
xmlcache = ''
username = ''
password = ''

def _normalize(string):
    '''Dummy casefold with normalization. Could be better to support cases like ü->ue'''
    return ''.join(c for c in unicodedata.normalize('NFKD', unicode(string))
            if not unicodedata.combining(c)).lower()

def _email(e, f):
    title = e.findtext(ATOM_NS + 'title')
    nickname = e.findtext(GC_NS + 'nickname', default='')
    email = f.get('address')
    kind = f.get('label') or f.get('rel').split('#')[-1]
    fulltext = _normalize('%s "%s" <%s> (%s)' % (title, nickname, email, kind))
    return (title, nickname, email, kind, fulltext,)

def updatedb(xmlfile):

    if xmlfile:
        xml = open(xmlfile, 'r').read()
    else:
        import gdata.contacts.service
        gd_client = gdata.contacts.service.ContactsService(additional_headers={gdata.contacts.service.GDATA_VER_HEADER:3})
        gd_client.ClientLogin(username, password)
        query = gdata.contacts.service.ContactsQuery()
        query.max_results = 2000
        xml = gd_client.GetContactsFeed('https://www.google.com' + query.ToUri()).ToString()
    if xmlcache:
        open(xmlcache, 'w').write(xml)

    cu.execute('CREATE TABLE IF NOT EXISTS addresses (title TEXT, nickname TEXT, email TEXT, kind TEXT, fulltext TEXT)')
    cu.execute('DELETE FROM addresses')
    import xml.etree.ElementTree as ET
    for e in ET.fromstring(xml).findall(ATOM_NS + 'entry'):
        # TODO skip groupless
        if not e.find(ATOM_NS + 'category').get('term').endswith('contact'):
            continue
        cu.executemany('INSERT INTO addresses VALUES (?,?,?,?,?)',
                (_email(e, f) for f in e.findall(G_NS + 'email')))
    cx.commit()

def query(query):
    tokens = [_normalize(unicode(s, 'utf-8')) for s in query.split()]
    query = 'SELECT email, title, kind FROM addresses WHERE 1' + (' AND fulltext LIKE ?' * len(tokens))
    cu.execute(query, ['%%%s%%' % t for t in tokens])
    print('\n' + '\n'.join('\t'.join(r) for r in cu.fetchall())),

if len(sys.argv) > 2 and sys.argv[1] == '-c':
    configfile = sys.argv[2]
    del sys.argv[1:3]

if os.path.exists(configfile):
    execfile(configfile)

cx = sqlite3.connect(database)
cu = cx.cursor()

if len(sys.argv) >= 2 and sys.argv[1] == 'update':
    updatedb(sys.argv[2] if len(sys.argv) > 2 else None)
elif len(sys.argv) == 3 and sys.argv[1] == 'query':
    query(sys.argv[2])
else:
    print('Usage: simplegab.py [-c configfile.py] ...')
    print('       simplegab.py update [file.xml]')
    print('       simplegab.py query tokens')
