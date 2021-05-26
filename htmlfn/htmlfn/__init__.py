""" Light weight functions for generating html
and working with the rest of the unholy trinity. """

__version__ = '0.0.4'

# chars

nbsp = '\xA0'

# html

def tag(_tag, n=False):
    nl = '\n' if n else ''
    s = f'<{_tag}{{extra}}>{nl}'
    e = f'{nl}</{_tag}>'
    def tagwrap(*value, **kwargs):
        if 'class_' in kwargs:
            kwargs['class'] = kwargs.pop('class_')
        extra = (' ' + ' '.join(f'{k}="{v}"'
                                for k, v in kwargs.items())
                 if kwargs else '')
        return s.format(extra=extra) + nl.join(value) + e
    return tagwrap


def cmb(_tag, n=False):
    nl = '\n' if n else ''
    _s = f'<{_tag}{{extra}}>{nl}'
    e = f'{nl}</{_tag}>'
    def asdf(**kwargs):
        if 'class_' in kwargs:
            kwargs['class'] = kwargs.pop('class_')
        extra = (' ' + ' '.join(f'{k}="{v}"'
                                for k, v in kwargs.items())
                 if kwargs else '')
        s = _s.format(extra=extra)
        def inner(*args):
            return s + nl.join(args) + e
        return inner
    return asdf


def stag(tag_):
    """ single tags """
    def inner(**kwargs):
        if 'class_' in kwargs:
            kwargs['class'] = kwargs.pop('class_')
        content = ' '.join(f'{key}="{value}"' for key, value in kwargs.items())
        return f'<{tag_} {content}>'
    return inner


def atag(href, value=None, new_tab=False, uriconv=None,
         cls=None, title=None, id=None):
    target = ' target="_blank"' if new_tab else ''
    class_ = '' if cls is None else f' class="{cls}"'
    id_ = '' if id is None else f' id="{id}"'
    title_tip = '' if title is None else f'<div class="cont"> <div class="tooltip">{title}</div></div></div>'
    tstart = '' if title is None else '<div class="tip">'
    title = '' if title is None else f' title="{title}"'
    if value is None:
        value = href
        if uriconv is not None:
            href = uriconv(href)

    return f'{tstart}<a href="{href}"{target}{class_}{id_}{title}>{value}</a>{title_tip}'


def atagpost(target, value=None, **data):
    # TODO
    if value is None:
        value = target

    formcmb = cmb('form', n=True)
    return formcmb(method='post', action='??', **{'class':'inline'})(
        inputtag(type='hidden', name='hrm', **data),
        buttontag(value, type='submit', name='submit-thing',
                  value='submit-value', **{'class':'link-button'}))


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
h3tag = tag('h3')
btag = tag('b')
ptag = tag('p')

buttontag = tag('button')


def metatag(**kwargs):
    content = ' '.join(f'{key}="{value}"' for key, value in kwargs.items())
    return f'<meta {content}>'


def spancmb(class_=None, **kwargs):
    """ span combinator
        because class is a reserved keyword in python, class_ is the first arg
        kwargs keys may be any html global attribute """
    cdict = {'class': class_}  # put class first (sign the siren song or python preserving key order)
    cdict.update(kwargs)
    content = ' '.join(f'{key}="{value}"' for key, value in cdict.items() if value is not None)
    def spantag(text):
        return f'<span {content}>{text}</span>'

    return spantag


def zerotag(text):
    return f'<span class="zero">{text}</span>'


def zeronotetag(text):
    return f'<span class="zeronote">{text}</span>'


inputtag = stag('input')

_default_title = 'Spooky Nameless Page'
def htmldoc(*body, title=_default_title, metas=tuple(), other=tuple(), styles=tuple(), scripts=tuple()):
    """ metas is a tuple of dicts """
    header = ('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"\n'
              '"http://www.w3.org/TR/html4/loose.dtd">\n')
    titlet = ('' if
              [o for o in other if o.startswith('<title')]
              and title == _default_title
              else titletag(title))
    other = '\n'.join(other)
    styles = '\n'.join((styletag(s) for s in styles))
    scripts = '\n'.join((scripttag(s) for s in scripts))
    metas = (dict(charset='UTF-8'),) + metas
    head = headtag('\n'.join((_ for _ in (titlet, other, *(metatag(**md) for md in metas), styles, scripts) if _)))
    return header + htmltag('\n'.join((head, bodytag(*body))))


def render_table(rows, *headers, halign=None):
    output = []
    ha = '' if halign is None else f' align="{halign}"'
    output.append(f'<tr><th{ha}>' + f'</th><th{ha}>'.join(headers) + '</th></tr>')
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


# forms
# FIXME this is quite bad

labeltag = tag('label')
inputtag = stag('input')
formtag = tag('form')
optiontag = tag('option')


def selecttag(*options, **kwargs):
    return tag('select')(*(optiontag(o) for o in options), **kwargs)


def render_form(*elements, method='POST', **kwargs):
    tags = labeltag, inputtag, selecttag
    return formtag(*[divtag(*(tag(*args, **kwargs)
                              for tag, (args, kwargs) in zip(tags, parts)
                              if args or kwargs))
                     for parts in elements],
                   method=method,
                   **kwargs)


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
.zero { color: red; }
.zeronote { color: #c08800; }
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
details > summary:hover { color: #40b040; background-color : #ccccff; }
details:not([open]) > summary:hover > a { color : #ff0000; font-weight: bold; }
details[open] > summary > span.hide-when-open { display: none; }
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

ttl_html_style = '''
body { font-family: monospace }
.tip { display: inline; }
.cont {
    position: absolute;
    opacity: 0;
    visibility: hidden;
    display: inline;
    z-index: 2;
    transition: 0s;
    transition-delay: 0s;
}

.tooltip {
    position: inherit;
    display: inherit;
    background: white;
    color: black;
    border-style: solid;
    border-color: black
    text-style: bold;
    border-width: 2px 2px 2px 2px;
    padding: 1px 1px 1px 1px;
}

.tip:hover .cont {
    position: relative;
    opacity: 1;
    visibility: visible;
    transition: 0s;
    transition-delay: 0s;
}

a:link { text-decoration: none;
         color: #252069; }
'''

emacs_style = '''
body {
    color: #a67ff4 ;
    background-color: black ;
}
.symbol { color : #770055; background-color : transparent; border: 0px; margin: 0px;}
a.symbol:link { color : #229955; background-color : transparent; text-decoration: none; border: 0px; margin: 0px; }
a.symbol:active { color : #229955; background-color : transparent; text-decoration: none; border: 0px; margin: 0px; }
a.symbol:visited { color : #229955; background-color : transparent; text-decoration: none; border: 0px; margin: 0px; }
a.symbol:hover { color : #229955; background-color : transparent; text-decoration: none; border: 0px; margin: 0px; }
.special { color : #FF5000; background-color : inherit; }

.keyword { color : #cd5c5c;
    background-color : inherit; }

.comment { color : #ff1493 ;
    background-color : inherit;
    font-weight: normal;
    /* text-decoration: underline; */
}

.string { color : cyan;
    background-color : inherit;
    font-weight: normal;
    white-space: wrap;
}

.quote { color : #2e8b57 ;
    background-color : inherit;
    font-weight: normal;
}

.number { color : #2e8b57 ;
    background-color : inherit;
    font-weight: normal;
}

.atom { color : #314F4F; background-color : inherit; }

.macro { color : #FF5000; background-color : inherit; }
.variable { color : #36648B; background-color : inherit; }
.function { color : #8B4789; background-color : inherit; }
.attribute { color : #FF5000; background-color : inherit; }
.character { color : #0055AA; background-color : inherit; }
.syntaxerror { color : #FF0000; background-color : inherit; }
.diff-deleted { color : #5F2121; background-color : inherit; }
.diff-added { color : #215F21; background-color : inherit; }

span.paren1 { color: #006400 ;
    font-weight: bold;
}

span.paren2 { color: #0000ff ;
    font-weight: bold;
}

span.paren3 { color: #a020f0 ;
    font-weight: bold;
}

span.paren4 { color: #4682b4 ;
    font-weight: bold;
}

span.paren5 { color: #ffa500 ;
    font-weight: bold;
}

span.paren6 { color: #8b008b ;
    font-weight: bold;
}

span.paren7 { color: #556b2f ;
    font-weight: bold;
}

span.paren8 { color: #008b8b ;
    font-weight: bold;
}

span.paren9 { color: #4d4d4d ;
    font-weight: bold;
}

.default { color: #a67ff4 ;
    font-weight: normal;
    background-color: none;
    }
.default:hover { background-color: none; color: #00ff00; }
'''

atagpost_style = '''
.inline {
  display: inline;
}

.link-button {
  background: none;
  border: none;
  color: blue;
  text-decoration: underline;
  cursor: pointer;
  font-size: 1em;
  font-family: serif;
}
.link-button:focus {
  outline: none;
}
.link-button:active {
  color:red;
}
'''

# combined styles
tree_styles = (details_style,
               'body { font-family: Dejavu Sans Mono; font-size: 10pt; }',  # FIXME duplicate with monospace_body
               'a:link { color: black; }',
               'a:visited { color: grey; }',)
