import json
import unittest
from outcrop.core.projection_notation import checked_projection, projection_notation, single_letter
from outcrop.core.agda_semantics import inline_notation_expression_index, decorate_type_nodes
from outcrop.adapters.agda.reweave import CodeRelocation, rebase_trace


def node(head='S', argument='𝒮'):
    source = head + ' ' + argument
    return dict(id=4, kind='application', source=source, start=1,
                end=len(source)+1, type='Type',
                projection=dict(name='Example.R.'+head,record='Example.R',head=head,argument=argument))


class ProjectionNotationTests(unittest.TestCase):
    def test_single_letter_boundary(self):
        for value in ('S','𝒮','p','x̂','Ω'):
            self.assertTrue(single_letter(value), value)
        for value in ('','S₁','SS','isSetS','S′','_','1','𝒮 ↾ M'):
            self.assertFalse(single_letter(value), value)

    def test_conservative_policy(self):
        self.assertEqual(projection_notation(node()), ('S','𝒮'))
        self.assertEqual(projection_notation(node(argument='𝒮 ↾ M')), ('S','𝒮 ↾ M'))
        for head in ('isSetS','SWO.S','fst','snd','lower'):
            self.assertIsNone(projection_notation(node(head=head)))
        for arg in ('a\nb','f (g x)','longInstanceName','p₁','(x : A)','_',''):
            self.assertIsNone(projection_notation(node(argument=arg)), arg)
        self.assertIsNone(projection_notation({**node(),'projection':None}))
        self.assertIsNone(projection_notation({**node(),'context':'pattern'}))

    def test_checked_independent_ranges(self):
        source='S (𝒮 ↾ M)'
        record=dict(start=1,headEnd=2,argumentStart=4,argumentEnd=9,
                    projection='Example.R.S',record='Example.R')
        self.assertEqual(checked_projection(record,source,10)['argument'],'𝒮 ↾ M')
        for patch in ({'headEnd':5},{'argumentStart':0},{'argumentEnd':99},{'headEnd':None}):
            self.assertIsNone(checked_projection({**record,**patch},source,10))
        self.assertIsNone(checked_projection(record,'S x𝒮 ↾ M)',10))

    def test_unanimous_inline_evidence_and_popup(self):
        n=node()
        self.assertIn('S 𝒮',inline_notation_expression_index([n]))
        ordinary={**n,'id':5,'start':11,'end':14,'projection':None}
        self.assertNotIn('S 𝒮',inline_notation_expression_index([n,ordinary]))
        self.assertIn('data-projection-head="S"',decorate_type_nodes('S 𝒮',[n],'Example'))
        self.assertNotIn('data-projection-head',decorate_type_nodes('S 𝒮',[n,ordinary],'Example'))

    def test_relocation_moves_every_projection_coordinate(self):
        record=dict(path='/a',sourceHash='old',kind='projection',start=11,end=14,
                    headEnd=12,argumentStart=13,argumentEnd=14)
        moved=json.loads(rebase_trace(json.dumps(record)+'\n',
            {'/a':(CodeRelocation(((11,15),),((21,25),)),'old','new')}))
        self.assertEqual([moved[k] for k in ('start','end','headEnd','argumentStart','argumentEnd')],
                         [21,24,22,23,24])

if __name__=='__main__':unittest.main()
