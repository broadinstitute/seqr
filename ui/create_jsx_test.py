import argparse as ap
import re
import os

p = ap.ArgumentParser("Create a .test.js file with a shallow-render test template for a .jsx component. "
                      "This script expects the .jsx file to export the class it defines using a statement like:"
                      "'export { SomeWidget as SomeWidgetComponent }'" )

p.add_argument('jsx_path', help='Path of .jsx component')
args = p.parse_args()

jsx_dir = os.path.dirname(args.jsx_path)
jsx_filename = os.path.basename(args.jsx_path)

outf = open(os.path.join(jsx_dir, jsx_filename.replace('.jsx', '.test.js')), 'w')

class_name, component_name = None, None
propTypes = ""
mapStateToProps = ""
imports = ""
f = open(args.jsx_path)

for line in f:
    # match lines like 'export { FilterSelector as FilterSelectorComponent }'
    match = re.match('export[ ]* \{[ ]*([^ ]+)[ ]* as [ ]*([^ ]+)[ ]*\}', line)
    if match:
        class_name = match.group(1)
        component_name = match.group(2)

    match = re.match('class[ ]+([^ ]+)[ ]+extends[ ]+React.Component', line)
    if match:
        class_name = component_name = match.group(1)

    match = re.match('const[ ]+([^ ]+)[ ]+=[ (]+props[ )]+=>', line)
    if match:
        class_name = component_name = match.group(1)

    elif line.startswith('import') and 'rootReducer' in line:
        imports += line

    elif "propTypes =" in line:
        while '}' not in line:
            line = next(f)
            if ':' in line:
                propTypes += '    ' + line.strip()+'\n'
        propTypes = propTypes.rstrip('\n')

    elif "mapStateToProps =" in line:
        while '}' not in line:
            line = next(f)
            if ':' in line:
                mapStateToProps += '    ' + line.strip()+'\n'
        mapStateToProps = mapStateToProps.replace('state', 'STATE1').rstrip('\n')

if not class_name:
    #p.error("export line (eg. 'export { FilterSelector as FilterSelectorComponent }') not found")
    class_name = component_name = os.path.basename(args.jsx_path).replace('.jsx', '')

if not mapStateToProps:
    mapStateToProps = propTypes


template = """import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import %(component_name)s from './%(class_name)s'
%(imports)s

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
%(propTypes)s
   */

  const props = {
%(mapStateToProps)s
  }

  shallow(<%(component_name)s {...props} />)
})
""" % locals()

outf.write(template)
outf.close()
