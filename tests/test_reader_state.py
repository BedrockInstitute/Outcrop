"""Public state-machine contracts replacing closure-variable spelling checks."""
import json
from pathlib import Path
from outcrop import site as site_package
RESOURCES = Path(site_package.__file__).resolve().parent / "resources"
import shutil
import subprocess
import unittest

READER = RESOURCES / 'static/reader'


@unittest.skipUnless(shutil.which('node'), 'Node.js is required')
class ReaderStateTests(unittest.TestCase):
    def run_js(self, exports, scenario):
        imports = '\n'.join('import {' + names + '} from ' + json.dumps(
            (READER / filename).as_uri()) + ';' for filename, names in exports.items())
        result = subprocess.run(['node', '--input-type=module', '-e', imports + scenario],
                                check=True, capture_output=True, text=True)
        return json.loads(result.stdout)

    def test_unbounded_history_identity_forward_truncation_and_cancel(self):
        result = self.run_js({'definition-session.js': 'DefinitionSession'}, '''
const s = new DefinitionSession();
for (let i=0;i<120;i++) s.push({url:'page#'+i}, 'definition '+i);
const total=s.entries.length;
s.move(-1); const old=s.current.target.url;
s.push({url:'replacement#1'},'replacement');
const forward=s.canForward, back=s.canBack;
let releases=0;
const first=s.begin(); s.own(()=>releases++);
const second=s.begin(); const stale=s.isCurrent(first), current=s.isCurrent(second);
s.own(()=>releases++); s.close(); s.close();
console.log(JSON.stringify({total,old,forward,back,stale,current,releases,
  closed:s.current,revived:s.isCurrent(second),length:s.entries.length}));
''')
        self.assertEqual(result, dict(total=120, old='page#118', forward=False, back=True,
            stale=False, current=True, releases=2, closed=None, revived=False, length=0))

    def test_common_downward_geometry_and_horizontal_clamping(self):
        result = self.run_js({'hover-view.js': 'belowSource'}, '''
const rect={left:280,right:310,bottom:77};
console.log(JSON.stringify(belowSource(rect,180,{width:320,scrollX:0,scrollY:20})));
''')
        self.assertEqual(result, {'left': 132, 'top': 97})

    def test_hover_has_no_depth_limit_and_disposes_every_entry(self):
        result = self.run_js({'hover-branch.js': 'HoverBranch'}, '''
let count=0;const branch=new HoverBranch({persistent:()=>true,dispose:()=>count++});
for(let i=0;i<120;i++) branch.append({parent:branch.entries[i-1]});
const depth=branch.entries.length;branch.removeFrom(0);
console.log(JSON.stringify({depth,count,left:branch.entries.length}));
''')
        self.assertEqual(result, {'depth':120,'count':120,'left':0})

    def test_rotated_surface_uses_one_inverse_for_gestures_and_popups(self):
        result = self.run_js({'code-surface.js': 'setCodeSurface, codePoint, codeSurface'}, '''
const anchor={getBoundingClientRect:()=>({left:280,right:300,top:120,bottom:200})};
const plane={contains:x=>x===anchor,clientWidth:844,clientHeight:390,scrollLeft:12,scrollTop:30,
  getBoundingClientRect:()=>({left:10,right:400,top:20,bottom:864})};
setCodeSurface({plane,rotated:true});
const start=codePoint({clientX:290,clientY:130},anchor);
const move=codePoint({clientX:290,clientY:170},anchor);
const {rect,width,height,scrollX,scrollY}=codeSurface(anchor);
const outside=codeSurface({});
setCodeSurface(null);
const normal=codePoint({clientX:290,clientY:170},anchor);
console.log(JSON.stringify({start,delta:move.x-start.x,rect,width,height,scrollX,scrollY,outside,normal}));
''')
        self.assertEqual(result, dict(start={'x':110,'y':110},delta=40,
            rect={'left':100,'right':180,'top':100,'bottom':120},width=844,height=390,
            scrollX=12,scrollY=30,outside=None,normal={'x':290,'y':170}))
