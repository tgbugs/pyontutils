""" Light weight functions for generating html
and working with the rest of the unholy trinity. """

# html

def tag(_tag, n=False):
    nl = '\n' if n else ''
    s = f'<{_tag}>{nl}'
    e = f'{nl}</{_tag}>'
    def tagwrap(*value):
        return s + nl.join(value) + e
    return tagwrap

def atag(href, value=None, new_tab=False, uriconv=None, cls=None):
    target = ' target="_blank"' if new_tab else ''
    class_ = '' if cls is None else f' class="{cls}"'
    if value is None:
        value = href
        if uriconv is not None:
            href = uriconv(href)
    return f'<a href="{href}"{target}{class_}>{value}</a>'

def divtag(*values, cls=None):
    class_ = f'class="{cls}"' if cls else ''
    vals = '\n'.join(values)
    return f'<div {class_}>\n{vals}\n</div>'

def deltag(text):
    return f'<del>{text}</del>'

htmltag = tag('html', n=True)
headtag = tag('head', n=True)
titletag = tag('title')
styletag = tag('style', n=True)
scripttag = tag('script', n=True)
bodytag = tag('body', n=True)
h1tag = tag('h1')
h2tag = tag('h2')
btag = tag('b')

def htmldoc(*body, title='Spooky Nameless Page', styles=tuple(), scripts=tuple()):
    header = ('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"\n'
              '"http://www.w3.org/TR/html4/loose.dtd">\n')
    styles = '\n'.join((styletag(s) for s in styles))
    scripts = '\n'.join((scripts(s) for s in scripts))
    head = headtag('\n'.join((titletag(title), '<meta charset="UTF-8">', styles, scripts)))
    return header + htmltag('\n'.join((head, bodytag(*body))))

def render_table(rows, *headers):
    output = []
    output.append('<tr><th>' + '</th><th>'.join(headers) + '</th></tr>')
    clean_headers = [h.split('>', 1)[1].split('<', 1)[0]  # FIXME hack
                     if h.startswith('<a')
                     else h
                     for h in headers]  # deal with atag headers
    for row in rows:
        if headers:
            ous = ('<tr>'
                + ''.join(f'<td class="col-{h.replace(" ", "_")}">{r}</td>'
                            for h, r in zip(clean_headers, row))
                + '</tr>')
            output.append(ous)
        else:
            output.append('<tr><td>' + '</td><td>'.join(row) + '</td></tr>')

    try:
        if headers and rows and len(headers) != len(row):
            raise TypeError(f'# of headers does not match # rows! {headers} {row}')
    except UnboundLocalError: # FIXME generators make things dumb
        print(f'WARNING: no rows for {headers}')

    out = '<table>' + '\n'.join(output) + '</table>'
    return out

# css

monospace_body_style = 'body { font-family: Dejavu Sans Mono; font-size: 11pt }'

table_style = '''
th { text-align: left; padding-right: 20px; }
td { text-align: left; padding-right: 20px; }
tr { vertical-align: top; }
tr:hover { background-color: #fcfcfc; }
table {
    font-family: Dejavu Sans Mono;
    font-weight: bold;
}
a:link { color: black; }
a:visited { color: grey; }
del { color: white; }
'''

cur_style = '''
tr { vertical-align: baseline; }

.col-Identifier a,
.col-PMID a,
.col-DOI a,
.col-RRIDs a,
.col-Paper a,
.col-Link a,
.col-HTML_Link a,
.col-Done a,
.col-TODO a
{
    background: pink;
    padding: 10px 4px;
    display: inline-block;
    text-decoration: none;
}

.col-Identifier a:visited,
.col-PMID a:visited,
.col-DOI a:visited,
.col-RRIDs a:visited,
.col-Paper a:visited,
.col-Link a:visited,
.col-HTML_Link a:visited,
.col-Done a:visited,
.col-TODO a:visited
{
    color: black;
    background: #b5a6ff;
}
'''

details_style = '''
details summary::-webkit-details-marker { display: none; }
details > summary:first-of-type { list-style-type: none; }
'''

navbar_style = '''
.navbar {
    overflow: hidden;
    background-color: gray;
    position: static;
    top: 0;
    left: 0;
    width: 100%;
}

.navbar a {
    float: left;
    display: block;
    color: black;
    font-family: Dejavu Sans Mono;
    font-weight: bold;
    text-align: center;
    padding: 14px 16px;
    text-decoration: none;
}

.navbar a:hover, .navbar-select {
    background: #ddd;
    color: black;
}

.navbar a:focus {
    outline: darkgray solid 2px;
    outline-offset: -3px;
}

.main {
    margin: 10px;
}

body {
    margin: 0px; /* so that the navbar is actually 100% */
    background: #e8e8e7;
}
'''

redlink_style = '''
.redlink {
    color: darkred;
    font-weight: bold;
}
'''
