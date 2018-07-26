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
    class_ = '' if cls is None else f'class="{cls}"'
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

def htmldoc(*body, title='Spooky Nameless Page', styles=tuple(), scripts=tuple()):
    header = ('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"\n'
              '"http://www.w3.org/TR/html4/loose.dtd">\n')
    styles = '\n'.join((styletag(s) for s in styles))
    scripts = '\n'.join((scripts(s) for s in scripts))
    head = headtag('\n'.join((titletag(title), '<meta charset="UTF-8">', styles, scripts)))
    return header + htmltag('\n'.join((head, bodytag(*body))))

def render_table(rows, *headers):
    output = []
    output.append('<tr><th>' + '</th><th>'.join(headers) + '</th><tr>')
    for row in rows:
        output.append('<tr><th>' + '</th><th>'.join(row) + '</th><tr>')

    out = '<table>' + '\n'.join(output) + '</table>'
    return out

# css

monospace_body_style = 'body { font-family: Dejavu Sans Mono; font-size: 11pt }'

table_style = ('th { text-align: left; padding-right: 20px; }'
               'tr { vertical-align: top;  }'
               'tr:hover { background-color: #fcfcfc;  }'
               'table { font-family: Dejavu Sans Mono; }'
               'a:link { color: black; }'
               'a:visited { color: grey; }'
               'del { color: white; }')

details_style = ('details summary::-webkit-details-marker { display: none; }\n'
                 'details > summary:first-of-type { list-style-type: none; }')

navbar_style = '''
.navbar {
    overflow: hidden;
    background-color: gray;
    position: fixed;
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
    margin-top: 60px;
}
'''

