"""Compiler syntax participates in the shared introductory vocabulary."""
import re
import unittest

from outcrop.core import MarkdownDocument
from outcrop.core.agda_semantics import AgdaSemantics
from outcrop.site.compiler_index import build_code_context


def token(text, aspect, position=None, target=None):
    identity = f' id="{position}"' if position is not None else ''
    href = f' href="{target}"' if target else ''
    return f'<a{identity}{href} class="{aspect}">{text}</a>'


def notation(name, target, parts):
    return (token('syntax', 'Keyword') + ' ' + token(name, 'Function', target=target)
            + ' ' + token('=', 'Symbol') + ' '
            + ' '.join(token(part, 'Function') + ' ' + token('x', 'Bound') for part in parts))


class VocabularySyntaxTests(unittest.TestCase):
    def setUp(self):
        self.semantics = AgdaSemantics(prelude_module='Guide')
        self.definitions = [('Σ[]-syntax', '40', ['Σ[', ']']),
                            ('Σ[∶]-syntax', '50', ['Σ[', '∶', ']'])]
        self.imports = [('∀[]-syntax', '60', ['∀[', ']']),
                        ('∀[∶]-syntax', '70', ['∀[', '∶', ']']),
                        ('∃[]-syntax', '80', ['∃[', ']']),
                        ('∃[∶]-syntax', '90', ['∃[', '∶', ']'])]
        guide = '# Guide\n\n## Pairs\n\n<pre class="Agda">'
        for name, position, parts in self.definitions:
            guide += (f'<a id="{name}"></a>' + token(name, 'Function', position, f'Guide.html#{position}')
                      + ' ' + token(':', 'Symbol', '101') + ' Type\n'
                      + notation(name, f'Guide.html#{position}', parts) + '\n')
        guide += '</pre>\n\n## Logic\n\n### Quantification\n\n<pre class="Agda">'
        guide += token('open', 'Keyword', '110') + ' ' + token('import', 'Keyword', '115') + ' Library '
        guide += token('public', 'Keyword', '120') + ' ' + token('using', 'Keyword', '125') + ' ( '
        guide += '; '.join(token(name, 'Function', str(int(position) + 1000), f'Library.html#{position}')
                           for name, position, _ in self.imports) + ' )</pre>'
        library = '\n'.join(f'<a id="{name}"></a>' + token(name, 'Function', position, f'Library.html#{position}')
                            + '\n' + notation(name, f'Library.html#{position}', parts)
                            for name, position, parts in self.imports)
        documents = {'Guide': (guide, True), 'Library': (library, False), 'Consumer': ('', True)}
        corpus = type('Corpus', (), {'read': lambda _, module: documents[module]})()
        types = {'Guide': {name: 'Type' for name, _, _ in self.definitions + self.imports},
                 'Library': {name: 'Type' for name, _, _ in self.imports}}
        self.code = build_code_context(corpus, {'Guide', 'Consumer'}, list(documents),
                                       self.semantics, types, {})
        self.guide = guide

    def test_imported_and_local_notations_share_one_registry(self):
        self.assertEqual({name for name, _ in self.code.vocabulary['syntax']},
                         {name for name, _, _ in self.definitions + self.imports})

    def test_all_surfaces_keep_declaration_identity_and_type(self):
        for name, position, parts in self.definitions + self.imports:
            imported = (name, position, parts) in self.imports
            expected = str(int(position) + 1000) if imported else position
            expression = ' '.join(part + ' x' for part in parts)
            formal = '<pre class="Agda">' + ' '.join(
                token(part, 'Function', target=f'{"Library" if imported else "Guide"}.html#{position}')
                + ' x' for part in parts) + '</pre>'
            for surface in (f'`{expression}`{{.Agda}}',
                            f'<div class="single-line-code"><code>`{expression}`{{.Agda}}</code></div>',
                            formal):
                with self.subTest(name=name, surface=surface):
                    body = MarkdownDocument(surface, module='Consumer', code=self.code).render('en').body
                    self.assertEqual(body.count(f'href="Guide.html#{expected}"'), len(parts))
                    self.assertEqual(body.count(f'data-type="Guide#{expected}"'), len(parts))

    def test_nested_notations_keep_distinct_targets(self):
        body = MarkdownDocument('`Σ[ x ∶ A ] ∃[ y ] ∀[ z ∶ B ] P x y z`{.Agda}',
                                module='Consumer', code=self.code).render('en').body
        self.assertEqual(re.findall(r'href="Guide.html#(\d+)"', body),
                         ['50', '50', '50', '1080', '1080', '1070', '1070', '1070'])

    def test_sections_are_edition_local_and_do_not_replace_definition_ids(self):
        for lang in ('en', 'zh', 'ja'):
            body = MarkdownDocument(self.guide, module='Guide', code=self.code).render(lang).body
            for name, position, _ in self.definitions + self.imports:
                imported = any(item[0] == name for item in self.imports)
                position = str(int(position) + 1000) if imported else position
                section = 'sec-3' if imported else 'sec-1'
                anchor = re.search(r'<a id="' + position + r'"[^>]+>', body)[0]
                self.assertIn(f'data-introduction-section="{section}"', anchor)
            # The visible imports still let readers continue into the library.
            self.assertIn('href="Library.html#60"', body)
        unrelated = MarkdownDocument(self.guide, module='Consumer', code=self.code).render('en').body
        self.assertNotIn('data-introduction-section', unrelated)

    def test_renamed_import_aliases_keep_their_introduction(self):
        source = ('# Guide\n\n## Records\n\n<pre class="Agda">'
                  + token('open', 'Keyword', '1') + ' ' + token('import', 'Keyword', '2')
                  + ' Library renaming ( old to ' + token('new', 'Function', '999') + ' )</pre>')
        body = MarkdownDocument(source, module='Guide', code=self.code).render('en').body
        self.assertIn('id="999" class="Function" data-introduction-section="sec-1"', body)


if __name__ == '__main__':
    unittest.main()
