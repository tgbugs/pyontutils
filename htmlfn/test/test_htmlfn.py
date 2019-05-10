import unittest
import htmlfn as hfn

doc_expect ='''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
"http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<title>test page</title>
<meta charset="UTF-8">
<meta test="meta">
<style>
body { font-family: Dejavu Sans Mono; font-size: 11pt }
</style>
<script>
console.log("lol")
</script>
</head>
<body>
<a href="https://example.com/">https://example.com/</a>
</body>
</html>'''


class TestHtmlFn(unittest.TestCase):
    def test_metatag_charset(self):
        assert hfn.metatag(charset='UTF-8') == '<meta charset="UTF-8">'

    def test_metatag_multi(self):
        assert hfn.metatag(name='field', content='value') == '<meta name="field" content="value">'

    def test_htmldoc(self):
        doc = hfn.htmldoc(hfn.atag('https://example.com/'),
                          title='test page',
                          metas=({'test': 'meta'},),
                          styles=(hfn.monospace_body_style,),
                          scripts=('console.log("lol")',))

        assert doc == doc_expect

    def test_spancmb(self):
        out = hfn.spancmb('class', id='hah')('some text')
        assert out == '<span class="class" id="hah">some text</span>'

    def test_apostag(self):
        out = hfn.atagpost('lol', 'something to search', form_value='hahaha')
